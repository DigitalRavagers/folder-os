#!/usr/bin/env python3
"""Rollback. Removes ONLY files the installer created, using the install record.

  python3 tools/uninstall.py                 show the plan, change nothing
  python3 tools/uninstall.py --yes           remove unchanged installer files
  python3 tools/uninstall.py --yes --remove-modified
                                             also remove installer files you edited

Never removed: anything not in the install record. That means files you added,
captured items, work orders and receipts all stay, and are listed at the end.
Folders are removed only when they are empty. Nothing outside the system folder
is read or changed. Python 3 standard library only.
"""
import sys
sys.dont_write_bytecode = True
import argparse
import json
import os

import common as c


def main():
    root = c.tool_root()
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--yes", action="store_true", help="actually remove files")
    parser.add_argument("--remove-modified", action="store_true")
    args = parser.parse_args()
    try:
        manifest = json.loads(c.read_text(root / c.MANIFEST))
    except (OSError, ValueError):
        c.die("The install record cannot be read, so nothing will be removed.")

    remove, keep = [], []
    for name, digest in sorted(manifest["files"].items()):
        path = root / name
        if not c.inside(root, path) or path.is_symlink() or not path.is_file():
            continue
        if c.sha256_file(path) == digest or args.remove_modified:
            remove.append(path)
        else:
            keep.append(name)
    print("Installer files to remove: %d" % len(remove))
    print("Installer files you changed since install (kept): %d" % len(keep))
    for name in keep:
        print("  kept: " + name)
    if not args.yes:
        print("Nothing was changed. Run again with --yes to remove.")
        return
    os.chdir(root.parent)
    for path in remove:
        path.unlink()
    (root / c.MANIFEST).unlink()
    folders = sorted(manifest["dirs"], key=len, reverse=True)
    for name in folders:
        folder = root / name
        # The install record is trusted only as far as it points inside this folder.
        if not c.inside(root, folder) or folder.is_symlink() or folder.resolve() == root.resolve():
            continue
        try:
            folder.rmdir()  # fails, on purpose, when the folder is not empty
        except OSError:
            pass
    if not manifest.get("target_preexisted"):
        try:
            root.rmdir()
        except OSError:
            pass
    left = [(folder / n).relative_to(root).as_posix()
            for folder, _, names in c.walk(root) for n in names] if root.is_dir() else []
    print("Removed %d file(s)." % (len(remove) + 1))
    if left:
        print("%d file(s) were left in place (yours, or installer files you changed):" % len(left))
        for name in sorted(left)[:50]:
            print("  left: " + name)
        print("They are yours. Delete the folder by hand only if you no longer want them.")
    elif root.is_dir() and manifest.get("target_preexisted"):
        print("The folder existed before install, so it was left in place, empty.")
    elif root.is_dir():
        print("All files are gone, but some empty folders could not be removed.")
    else:
        print("The system folder is gone. Nothing outside it was touched.")


if __name__ == "__main__":
    main()
