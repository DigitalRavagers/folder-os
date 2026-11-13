#!/usr/bin/env python3
"""Check structure and frontmatter against routing/registry.json and routing/taxonomy.json.

Exit codes are real and are never masked:
  0  no errors (warnings may be printed)
  1  at least one error (or a warning when --strict is given)
  2  the check itself could not run (rules unreadable, not an installed system)
Read-only. Python 3 standard library only.
"""
import sys
sys.dont_write_bytecode = True
import argparse
import datetime
import json
import re

import common as c


def age_days(date_text):
    try:
        then = datetime.date.fromisoformat(date_text[:10])
    except ValueError:
        return None
    return (c.now().date() - then).days


def check_markdown(path, name, reg, tax, errors, warnings):
    try:
        meta, body = c.read_frontmatter(c.read_text(path))
    except (OSError, UnicodeDecodeError):
        return errors.append("%s: cannot be read as text" % name)
    if meta is None:
        text = c.read_text(path).strip()
        if "\n" not in text and " " not in text and ("/" in text or "\\" in text):
            return errors.append("%s: looks like a pointer stub (a bare path), not real "
                                 "content. Replace it with the real file." % name)
        return errors.append("%s: no frontmatter. Start the file with ---, then title, "
                             "type, status and created lines, then ---." % name)
    kind = tax["types"].get(meta.get("type", ""))
    if kind is None:
        return errors.append("%s: type '%s' is not in routing/taxonomy.json"
                             % (name, meta.get("type", "")))
    if name.startswith(reg["templates"] + "/"):
        return None  # templates keep their {{placeholders}}
    status = meta.get("status", "")
    needed = tax["base_required"] + kind["required"] + kind.get("required_when", {}).get(status, [])
    for field in needed:
        if not meta.get(field):
            errors.append("%s: required field '%s' is missing or empty" % (name, field))
        elif "{{" in meta[field]:
            errors.append("%s: field '%s' still holds a template placeholder" % (name, field))
    if status and status not in kind["statuses"]:
        errors.append("%s: status '%s' is not allowed for type '%s' (allowed: %s)"
                      % (name, status, meta["type"], ", ".join(kind["statuses"])))
    if meta["type"] == "current" and status == "active":
        days = age_days(meta.get("updated", ""))
        if days is not None and days > 7:
            warnings.append("%s: next step not refreshed for %d days" % (name, days))
    return meta, body


def check_inbox_item(root, path, name, parsed, reg, errors, warnings):
    """Only the declared writer may put files in the inbox. Detect anything else."""
    box = reg["inbox"]["path"]
    if not re.match(reg["naming"]["inbox_item"]["pattern"], path.name):
        return errors.append("%s: not written by %s (bad name). The inbox has one "
                             "writer." % (name, reg["inbox"]["writer"]))
    if not parsed:
        return None
    meta, body = parsed
    if meta.get("writer") != reg["inbox"]["writer"] or meta.get("type") != "inbox-item":
        errors.append("%s: not written by the declared inbox writer" % name)
    if meta.get("id") != c.item_id(body) or meta.get("id", "") not in path.name:
        errors.append("%s: id does not match its text (edited by hand or foreign writer)"
                      % name)
    where = path.parent.relative_to(root).as_posix()
    expected = {box: "new", box + "/_routed": "routed", box + "/_discarded": "discarded"}
    if meta.get("status") != expected.get(where):
        errors.append("%s: status '%s' does not match its folder" % (name, meta.get("status")))
    if meta.get("status") == "routed" and not (root / meta.get("routed_to", "?")).is_file():
        errors.append("%s: routed_to points at a missing work order" % name)
    if meta.get("status") == "new" and (age_days(meta.get("captured", "")) or 0) > 2:
        warnings.append("%s: waiting in the inbox for more than 2 days" % name)
    return None


def lint(root):
    errors, warnings = [], []
    reg, tax = c.load_rules(root)
    box = reg["inbox"]["path"]
    for name in reg["required_files"]:
        if not (root / name).is_file():
            errors.append("%s: required file is missing" % name)
    maps = [root / "CLAUDE.md", root / "AGENTS.md"]
    if all(m.is_file() for m in maps) and maps[0].read_bytes() != maps[1].read_bytes():
        errors.append("CLAUDE.md and AGENTS.md differ. They must be byte-identical so "
                      "there is one root map, not two.")
    for folder, dirs, files in c.walk(root):
        here = folder.relative_to(root).as_posix()
        for d in list(dirs):
            if (folder / d).is_symlink():
                errors.append("%s/%s: is a link. Links are not allowed; use real folders."
                              % (here, d))
                dirs.remove(d)
        if folder != root and "context.md" not in files:
            errors.append("%s: folder has no context.md contract (copy %s/context.template.md)"
                          % (here, reg["templates"]))
        for filename in files:
            path = folder / filename
            name = path.relative_to(root).as_posix()
            if path.is_symlink():
                errors.append("%s: is a link. Links are not allowed; use real files." % name)
                continue
            parsed = None
            if filename.endswith(".md") and name not in reg["frontmatter_exempt"]:
                parsed = check_markdown(path, name, reg, tax, errors, warnings)
            if (here == box or here.startswith(box + "/")) and filename != "context.md":
                check_inbox_item(root, path, name, parsed, reg, errors, warnings)
            if here == "logs/receipts" and filename != "context.md":
                if not re.match(reg["naming"]["receipt"]["pattern"], filename):
                    errors.append("%s: receipt name does not follow the naming rule" % name)
                try:
                    json.loads(c.read_text(path))
                except (OSError, ValueError):
                    errors.append("%s: receipt is not readable JSON" % name)
    return errors, warnings


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = parser.parse_args()
    errors, warnings = lint(c.tool_root())
    for line in warnings:
        print("WARNING " + line)
    for line in errors:
        print("ERROR   " + line)
    print("lint: %d error(s), %d warning(s)" % (len(errors), len(warnings)))
    sys.exit(1 if errors or (args.strict and warnings) else 0)


if __name__ == "__main__":
    main()
