"""Acceptance contracts: criterion-bound evidence for one work order.

A contract is a small JSON file that sits next to its work order:

    work-orders/WO-c1a2b3c4.md
    work-orders/WO-c1a2b3c4.contract.json

    {
      "contract_version": 1,
      "work_id": "WO-c1a2b3c4",
      "artifact": "deliverables/summary_draft_first.md",
      "criteria": [
        {"id": "has-summary", "type": "has_line", "text": "## Summary"},
        {"id": "names-client", "type": "contains", "text": "Example Client"},
        {"id": "no-placeholder", "type": "not_contains", "text": "TODO", "ignore_case": true}
      ]
    }

"artifact" is one file inside the work order's own project folder, written
relative to that folder with forward slashes. Every criterion is a literal text
check on that file. There are no patterns, no commands and nothing is executed.
ALL criteria are evaluated every time; one failure fails the contract.

What a pass means: these exact artifact bytes met these exact criteria. Both
hashes are stored on the work order, so a later change to either file makes the
evidence stale. What a pass does not mean: that the criteria were the right
ones, that a person reviewed the output, or that anything was delivered. Anyone
who can edit the files directly can also edit the stored hashes; nothing here is
signed or authenticated.

Python 3 standard library only. Read-only: this module never writes a file.
"""
import json
import os
import re

import common as c

VERSION = 1
MODE = "contract-v1"            # evidence_mode written by a contract pass
LEGACY = "legacy-technical"     # evidence_mode written by --check-file / --check-cmd
EVIDENCE_FIELDS = ("evidence", "evidence_mode", "contract_sha256", "artifact",
                   "artifact_sha256", "verified")
MAX_CONTRACT_BYTES = 65536
MAX_ARTIFACT_BYTES = 2000000
MAX_CRITERIA = 50
MAX_TEXT = 500
MAX_PATH = 300
TYPES = ("contains", "has_line", "not_contains")
TOP_KEYS = {"contract_version", "work_id", "artifact", "criteria"}
CRITERION_KEYS = {"id", "type", "text"}
CRITERION_OPTIONAL = {"ignore_case"}
ID_PATTERN = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")


class ContractError(Exception):
    """A contract or its artifact cannot be used. Messages are fixed text and
    never quote the contract or the artifact."""


def path_of(order):
    return order.with_name(order.stem + ".contract.json")


def exists(order):
    """True when anything sits at the contract path, including a link."""
    return os.path.lexists(path_of(order))


def _no_duplicate_keys(pairs):
    keys = [key for key, _ in pairs]
    if len(set(keys)) != len(keys):
        raise ContractError("the contract repeats a key")
    return dict(pairs)


def _no_constants(_name):
    raise ContractError("the contract holds a value that is not standard JSON")


def _check_artifact_path(value):
    if not isinstance(value, str) or not value or len(value) > MAX_PATH:
        raise ContractError("artifact must be a short, non-empty text path")
    if value.startswith("/") or "\\" in value or ":" in value or any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise ContractError("artifact must be a relative path with forward slashes only")
    parts = value.split("/")
    if any(part in ("", ".", "..") or part.startswith(".") or part != part.strip()
           for part in parts):
        raise ContractError("artifact path may not contain empty, dot or parent segments")
    if parts[0].lower() == "work-orders":
        raise ContractError("artifact may not be a work order or a contract")


def _check_criterion(entry, number, seen):
    where = "criterion %d" % number
    if not isinstance(entry, dict):
        raise ContractError(where + " is not an object")
    keys = set(entry)
    if not CRITERION_KEYS <= keys or keys - CRITERION_KEYS - CRITERION_OPTIONAL:
        raise ContractError(where + " must have id, type and text, optionally "
                            "ignore_case, and nothing else")
    ident, kind, text = entry["id"], entry["type"], entry["text"]
    if not isinstance(ident, str) or len(ident) > 40 or not ID_PATTERN.fullmatch(ident):
        raise ContractError(where + " has a bad id (lowercase letters, numbers, hyphens)")
    if ident in seen:
        raise ContractError(where + " repeats an id used earlier")
    seen.add(ident)
    if not isinstance(kind, str) or kind not in TYPES:
        raise ContractError(where + " has an unsupported type (allowed: %s)" % ", ".join(TYPES))
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT:
        raise ContractError(where + " needs non-empty text of at most %d characters" % MAX_TEXT)
    if any(ord(ch) < 32 for ch in text):
        raise ContractError(where + " text must be a single line without control characters")
    if not isinstance(entry.get("ignore_case", False), bool):
        raise ContractError(where + " ignore_case must be true or false")


def load(order):
    """Return (contract, sha256 of the contract file's exact bytes).
    Raises ContractError unless the file is a strictly valid version 1 contract."""
    # Reject linked work orders and linked ancestors before resolving a project.
    # Otherwise order.resolve() could silently move the evidence boundary.
    if order.is_symlink() or any(parent.is_symlink() for parent in order.parents):
        raise ContractError("the work order path goes through a link")
    path = path_of(order)
    if path.is_symlink():
        raise ContractError("the contract file is a link; links are not followed")
    if not path.is_file():
        raise ContractError("no acceptance contract file next to the work order")
    if path.stat().st_size > MAX_CONTRACT_BYTES:
        raise ContractError("the contract file is too large")
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
        data = json.loads(text, object_pairs_hook=_no_duplicate_keys,
                          parse_constant=_no_constants)
    except (ValueError, RecursionError):
        raise ContractError("the contract file is not valid UTF-8 JSON") from None
    if c.find_secret(text):
        raise ContractError("the contract looks like it contains a secret")
    if not isinstance(data, dict) or set(data) != TOP_KEYS:
        raise ContractError("the contract must have exactly these keys: %s"
                            % ", ".join(sorted(TOP_KEYS)))
    if type(data["contract_version"]) is not int or data["contract_version"] != VERSION:
        raise ContractError("unsupported contract_version (this tool reads version %d)" % VERSION)
    if data["work_id"] != order.stem:
        raise ContractError("work_id in the contract does not match this work order")
    _check_artifact_path(data["artifact"])
    criteria = data["criteria"]
    if not isinstance(criteria, list) or not criteria or len(criteria) > MAX_CRITERIA:
        raise ContractError("criteria must be a list of 1 to %d checks" % MAX_CRITERIA)
    seen = set()
    for number, entry in enumerate(criteria, 1):
        _check_criterion(entry, number, seen)
    return data, c.sha256_bytes(raw)


def read_artifact(order, artifact):
    """Return the artifact's bytes. It must be a real, non-empty, bounded file
    inside the work order's own project folder, reached without any link."""
    project = order.resolve().parent.parent
    here = project
    for part in artifact.split("/"):
        here = here / part
        if here.is_symlink():
            raise ContractError("the artifact path goes through a link; links are not followed")
    if not here.is_file() or not c.inside(project, here):
        raise ContractError("the artifact file is missing from this work order's project folder")
    size = here.stat().st_size
    if size == 0:
        raise ContractError("the artifact file is empty")
    if size > MAX_ARTIFACT_BYTES:
        raise ContractError("the artifact file is larger than %d bytes" % MAX_ARTIFACT_BYTES)
    data = here.read_bytes()
    if not data or len(data) > MAX_ARTIFACT_BYTES:
        raise ContractError("the artifact file changed size while it was read")
    return data


def evaluate(contract, text):
    """Evaluate every criterion. Returns [(id, type, passed)], never stops early."""
    if text.startswith("﻿"):
        text = text[1:]
    results = []
    for entry in contract["criteria"]:
        needle, hay = entry["text"], text
        if entry.get("ignore_case", False):
            needle, hay = needle.casefold(), hay.casefold()
        if entry["type"] == "has_line":
            met = needle.strip() in [line.strip() for line in hay.splitlines()]
        elif entry["type"] == "contains":
            met = needle in hay
        else:
            met = needle not in hay
        results.append((entry["id"], entry["type"], met))
    return results


def check(order):
    """Validate the contract, read the artifact once, evaluate all criteria on
    those same bytes. Raises ContractError when the check cannot be made."""
    contract, contract_hash = load(order)
    data = read_artifact(order, contract["artifact"])
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise ContractError("the artifact file is not valid UTF-8 text") from None
    results = evaluate(contract, text)
    return {"ok": all(met for _, _, met in results), "results": results,
            "contract_sha256": contract_hash, "artifact": contract["artifact"],
            "artifact_sha256": c.sha256_bytes(data)}


def stale(order, meta):
    """Why this work order's evidence cannot be relied on right now, or None.
    Used before accepted and delivered, and by lint."""
    if meta.get("evidence_mode") != MODE:
        if exists(order):
            return ("it has an acceptance contract, but its evidence is legacy and never "
                    "evaluated that contract")
        return None
    try:
        contract, contract_hash = load(order)
        data = read_artifact(order, contract["artifact"])
    except ContractError as error:
        return "evidence is stale: %s" % error
    if contract_hash != meta.get("contract_sha256"):
        return "evidence is stale: the contract changed after verification"
    if contract["artifact"] != meta.get("artifact"):
        return "evidence is stale: the contract names a different artifact"
    if c.sha256_bytes(data) != meta.get("artifact_sha256"):
        return "evidence is stale: the artifact changed after verification"
    return None
