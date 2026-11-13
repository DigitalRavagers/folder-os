#!/usr/bin/env python3
"""Scoped search. Looks only in ONE client's folder plus the shared folders
whitelisted in routing/registry.json, so one client's material never shows up
while you work on another.

  python3 tools/search.py --client example-client "invoice"
  python3 tools/search.py --shared-only "template"

There is no search-everything mode. Read-only. Never follows links.
Limit: this scopes THIS tool. It cannot stop another program from searching wider.
Python 3 standard library only.
"""
import sys
sys.dont_write_bytecode = True
import argparse

import common as c


def main():
    root = c.tool_root()
    reg, _ = c.load_rules(root)
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("term")
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--client")
    scope.add_argument("--shared-only", action="store_true")
    args = parser.parse_args()

    folders = [root / name for name in reg["search"]["shared_whitelist"]]
    if args.client:
        client = root / reg["rooms"]["clients"] / c.slug(args.client)
        if not client.is_dir() or not c.slug(args.client):
            c.die("No such client folder: " + c.slug(args.client))
        folders.insert(0, client)
    term, found = args.term.lower(), 0
    for base in folders:
        for folder, dirs, files in c.walk(base):
            dirs[:] = [d for d in dirs if not (folder / d).is_symlink()]
            for name in files:
                path = folder / name
                if path.is_symlink():
                    continue
                try:
                    lines = c.read_text(path).splitlines()
                except (OSError, UnicodeDecodeError):
                    continue
                for number, line in enumerate(lines, 1):
                    if term in line.lower():
                        found += 1
                        print("%s:%d: %s" % (path.relative_to(root).as_posix(), number,
                                             line.strip()[:160]))
    print("search: %d match(es) in %s" % (found, ", ".join(
        f.relative_to(root).as_posix() for f in folders)))


if __name__ == "__main__":
    main()
