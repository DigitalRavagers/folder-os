"""Shared helpers for the folder system tools.

Python 3 standard library only. No network access. No credentials.
Every other tool imports this file, so rules about time stamps, receipts,
secret detection and frontmatter live in exactly one place.
"""
import datetime
import hashlib
import json
import os
import re
import sys
import uuid
from pathlib import Path

KIT_VERSION = "0.1.0-pilot"
MANIFEST = ".install/install.json"
IGNORED_NAMES = {".DS_Store"}  # Finder metadata. Never written and never removed by this kit.
SKIP_DIRS = {".install", "__pycache__", ".git"}

# Best effort only. A pattern list cannot catch every secret.
SECRET_PATTERNS = [
    ("private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("api key, sk style", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}")),
    ("cloud access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("code host key", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}")),
    ("chat app key", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("credential assignment",
     re.compile(r"(?i)\b(password|passwd|api[_-]?key|secret|token)\b\s*[:=]\s*\S{6,}")),
    ("card-like number", re.compile(r"\b(?:\d[ -]?){13,19}\b")),
]

SESSION = (re.sub(r"[^A-Za-z0-9]", "", os.environ.get("POFS_SESSION_ID", ""))[:32]
           or uuid.uuid4().hex[:8])


def now():
    return datetime.datetime.now().astimezone()


def stamp():
    """Date, time with seconds, and timezone offset. Used in log filenames."""
    return now().strftime("%Y%m%dT%H%M%S%z")


def iso():
    return now().strftime("%Y-%m-%dT%H:%M:%S%z")


def today():
    return now().strftime("%Y-%m-%d")


def die(message, code=2):
    print("ERROR: " + message, file=sys.stderr)
    sys.exit(code)


def one_line(text):
    return " ".join(str(text).split())


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    return sha256_bytes(Path(path).read_bytes())


def item_id(text):
    """Identity of a captured item: a hash of its text with whitespace collapsed.
    The same text always gets the same id, which is what makes capture idempotent."""
    return "c" + sha256_bytes(one_line(text).encode("utf-8"))[:15]


def read_text(path):
    return Path(path).read_text(encoding="utf-8")


def write_new(path, text):
    """Create a file. Fails with FileExistsError instead of overwriting."""
    with open(path, "x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def replace_text(path, text):
    """Update a file this system owns: write a temp file next to it, then swap."""
    path = Path(path)
    temp = path.with_name(path.name + ".tmp-" + SESSION)
    write_new(temp, text)
    os.replace(temp, path)


def inside(root, path):
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
        return True
    except ValueError:
        return False


def find_secret(text):
    """Return the name of the first secret-like pattern found, or None.
    Callers print the pattern name only, never the matching text."""
    for name, pattern in SECRET_PATTERNS:
        if pattern.search(text):
            return name
    return None


def walk(root):
    """Yield (folder, dirnames, filenames) below root. Never follows links."""
    for folder, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        yield Path(folder), dirs, sorted(f for f in files if f not in IGNORED_NAMES)


def tool_root():
    """The installed system folder, found from this file's own location."""
    root = Path(__file__).resolve().parent.parent
    if not (root / MANIFEST).is_file():
        die("These tools only run from the tools folder of an installed system "
            "(no %s found next to it)." % MANIFEST)
    return root


def load_rules(root):
    """Load the single sources of truth. Exit code 2 when they cannot be read."""
    rules = []
    for name in ("routing/registry.json", "routing/taxonomy.json"):
        try:
            rules.append(json.loads(read_text(Path(root) / name)))
        except (OSError, ValueError) as error:
            die("Cannot read %s (%s). Fix or restore that file first."
                % (name, type(error).__name__))
    return rules


def read_frontmatter(text):
    """Return (meta, body). meta is None when there is no frontmatter block.
    Deliberately tiny: flat 'key: value' lines between two '---' lines."""
    lines = text.split("\n")
    if lines[0].strip() != "---":
        return None, text
    meta = {}
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return meta, "\n".join(lines[index + 1:])
        if ":" in lines[index]:
            key, value = lines[index].split(":", 1)
            meta[key.strip()] = value.strip()
    return None, text


def write_frontmatter(meta, body):
    head = "".join("%s: %s\n" % (key, one_line(value)) for key, value in meta.items())
    return "---\n" + head + "---\n" + body


def fill(template, **values):
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", str(value))
    return template


_sequence = 0


def receipt(root, action, outcome, **details):
    """Write one receipt file and return its path.

    Filename: date, time with seconds, timezone, session id, counter, action.
    Receipts hold ids, paths and outcomes. They never hold captured text.
    If the details still look like a secret they are replaced before writing.
    """
    global _sequence
    record = {"kit": KIT_VERSION, "time": iso(), "session": SESSION,
              "action": action, "outcome": outcome, "details": details}
    hit = find_secret(json.dumps(record))
    if hit:
        record["details"] = {"redacted": "details looked like a " + hit}
    text = json.dumps(record, indent=2, sort_keys=True) + "\n"
    folder = Path(root) / "logs" / "receipts"
    while True:
        _sequence += 1
        path = folder / ("%s_%s_%03d_%s.json" % (stamp(), SESSION, _sequence, action))
        try:
            write_new(path, text)
            return path
        except FileExistsError:
            continue


PROJECT_ROOMS = {
    "": ("One client project. CURRENT.md is the single statement of where it stands.",
         "CURRENT.md, then open work orders.",
         "Work the next step. Keep CURRENT.md honest.",
         "Updated CURRENT.md, work orders, deliverables."),
    "assets": ("Material received from the client for this project.",
               "Files the client sent.", "Store as received. Do not edit originals.",
               "None. Reference only."),
    "deliverables": ("Things made for the client in this project.",
                     "The work order that asked for the deliverable.",
                     "Save each version under the revision naming rule in routing/registry.json.",
                     "Files that a work order can point to as evidence."),
    "work-orders": ("One file per next action for this project, each with a testable done-when.",
                    "Created by tools/capture.py route.",
                    "Do the work, then close with evidence using tools/capture.py close.",
                    "Work orders that end as delivered or dropped."),
}


def context_text(template, folder, purpose, read, do, output, check, skip, date):
    return fill(template, folder=folder, purpose=purpose, input=read, do=do,
                output=output, check=check, skip=skip, date=date)


def project_files(tpl_context, tpl_current, clients_dir, client_name, project_name, date, gate):
    """Files for one client project, as {relative path: text}. Used by setup and new-project."""
    client, project = slug(client_name), slug(project_name)
    base = "%s/%s" % (clients_dir, client)
    files = {base + "/context.md": context_text(
        tpl_context, base, "Everything for the client '%s'. One subfolder per project." % client_name,
        "The project folder you were asked to work in.", "Work inside one project at a time.",
        "Nothing is written at this level.", gate, "every other client folder", date)}
    for sub, (purpose, read, do, output) in PROJECT_ROOMS.items():
        folder = "%s/%s" % (base, project) + ("/" + sub if sub else "")
        files[folder + "/context.md"] = context_text(
            tpl_context, folder, purpose, read, do, output, gate, "every other client folder", date)
    files["%s/%s/CURRENT.md" % (base, project)] = fill(
        tpl_current, client=client, project=project, client_name=client_name,
        project_name=project_name, date=date)
    return files
