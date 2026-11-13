#!/usr/bin/env python3
"""Health check. Reports each capability as live, broken, warning or missing-optional,
with a fix for anything that is not live. Missing optional tools never break it.

  python3 tools/doctor.py
  python3 tools/doctor.py --boundary-canary /path/to/a/private/folder

The boundary canary answers one question: can THIS process read that folder?
Run it the same way your AI tool runs commands (same user account, same sandbox).
If the answer is OPEN, the boundary is only a label.

Exit code 0 when nothing is broken, 1 when something is broken. Read-only.
Python 3 standard library only.
"""
import sys
sys.dont_write_bytecode = True
import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import common as c

SYNC_WORDS = ["icloud", "mobile documents", "cloudstorage", "dropbox", "onedrive",
              "google drive", "googledrive"]


def boundary(root, target):
    target = Path(target).expanduser()
    if c.inside(root, target):
        return ("broken", "boundary canary", "that folder is INSIDE the system",
                "Private material must live outside the system folder. Move it out.")
    if not os.path.lexists(target):
        return ("warning", "boundary canary", "BOUNDARY UNTESTED: path does not exist",
                "Give the path of a real private folder.")
    try:
        names = os.listdir(target)
        for name in names:
            if (target / name).is_file():
                with open(target / name, "rb") as handle:
                    handle.read(1)
                break
    except PermissionError:
        return ("live", "boundary canary", "BOUNDARY BLOCKED: this process cannot read it", "")
    except OSError as error:
        return ("warning", "boundary canary",
                "BOUNDARY UNTESTED: %s" % type(error).__name__, "Check the path.")
    return ("broken", "boundary canary",
            "BOUNDARY OPEN: this process can read that folder (%d item(s) visible)" % len(names),
            "A written rule will not stop an AI tool from reading it. Use real access "
            "control: run the AI tool under a separate user account that has no "
            "permission on that folder, or keep the folder on an encrypted volume that "
            "is locked while the AI tool runs. Then run this check again.")


def checks(root, canary):
    out = []
    ok = sys.version_info >= (3, 8)
    out.append(("live" if ok else "broken", "python", "version %d.%d" % sys.version_info[:2],
                "" if ok else "Install Python 3.8 or newer from python.org."))
    try:
        manifest = json.loads(c.read_text(root / c.MANIFEST))
        out.append(("live", "install record", c.MANIFEST, ""))
    except (OSError, ValueError):
        manifest = {"files": {}}
        out.append(("broken", "install record", "unreadable",
                    "Uninstall cannot work without it. Restore it from a backup."))
    rules_ok = True
    for name in ("routing/registry.json", "routing/taxonomy.json"):
        try:
            json.loads(c.read_text(root / name))
            out.append(("live", name, "readable", ""))
        except (OSError, ValueError):
            rules_ok = False
            out.append(("broken", name, "unreadable",
                        "Undo your last edit to this file (CHANGELOG.md lists changes)."))
    writable = os.access(root / "logs" / "receipts", os.W_OK)
    out.append(("live" if writable else "broken", "receipt log", "logs/receipts",
                "" if writable else "Make logs/receipts writable for your user."))
    for name, digest in sorted(manifest["files"].items()):
        if name.startswith("tools/") and name.endswith(".py"):
            path = root / name
            if not path.is_file():
                out.append(("broken", name, "missing",
                            "Copy %s from the kit's scripts folder." % path.name))
            elif c.sha256_file(path) != digest:
                out.append(("warning", name, "changed since install (stale or edited)",
                            "If you did not change it on purpose, copy it again from the kit."))
    links, secrets = [], []
    for folder, dirs, files in c.walk(root):
        for name in dirs + files:
            path = folder / name
            if path.is_symlink():
                links.append(path.relative_to(root).as_posix())
            elif path.is_file() and path.stat().st_size < 1000000:
                try:
                    hit = c.find_secret(c.read_text(path))
                except (OSError, UnicodeDecodeError):
                    continue
                if hit:
                    secrets.append("%s (%s)" % (path.relative_to(root).as_posix(), hit))
    out.append(("broken", "links", ", ".join(links),
                "Replace each link with the real file or folder, then remove the link.")
               if links else ("live", "links", "none found", ""))
    out.append(("broken", "secret scan", "; ".join(secrets),
                "Move it out of the system folder, and change that key or password "
                "because it has been stored in plain text.")
               if secrets else ("live", "secret scan", "no known patterns found (best effort)", ""))
    synced = [w for w in SYNC_WORDS if w in str(root).lower()]
    out.append(("warning", "sync folder", "path looks synced (%s)" % synced[0],
                "Sync tools can delete or replace folders. Prefer a folder that is not "
                "synced, and back it up separately.")
               if synced else ("live", "sync folder", "path does not look synced", ""))
    reg_pattern = r"^\d{8}T\d{6}[+-]\d{4}$"
    clock = re.match(reg_pattern, c.stamp()) is not None
    out.append(("live" if clock else "broken", "clock and timezone", c.stamp(),
                "" if clock else "Set the computer's timezone in system settings."))
    git = shutil.which("git")
    out.append(("live", "git (optional)", "found", "") if git else
               ("missing-optional", "git (optional)", "not installed; nothing depends on it",
                "Only if you want version history. Mac: xcode-select --install   "
                "Windows: install Git for Windows."))
    if rules_ok:
        run = subprocess.run([sys.executable, str(root / "tools" / "lint.py")],
                             capture_output=True, text=True)
        last = (run.stdout.strip().splitlines() or ["no output"])[-1]
        out.append(("live" if run.returncode == 0 else "broken", "lint", last,
                    "" if run.returncode == 0 else "Run: %s tools/lint.py and fix each ERROR line." % ("py -3" if os.name == "nt" else "python3")))
    if canary:
        out.append(boundary(root, canary))
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--boundary-canary", metavar="FOLDER")
    args = parser.parse_args()
    results = checks(c.tool_root(), args.boundary_canary)
    for status, name, detail, fix in results:
        print("%-17s %-24s %s" % (status.upper(), name, detail))
        if fix:
            print("%-17s fix: %s" % ("", fix))
    broken = sum(1 for r in results if r[0] == "broken")
    print("doctor: %d check(s), %d broken" % (len(results), broken))
    sys.exit(1 if broken else 0)


if __name__ == "__main__":
    main()
