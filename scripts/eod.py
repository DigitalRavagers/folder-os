#!/usr/bin/env python3
"""End-of-day view. Computes the current state from the files and prints it:
what is still in the inbox, each project's next step and done-when, open work
orders, and what today's receipts say, including every failure.

  python3 tools/eod.py
  python3 tools/eod.py --date 20261113

Read-only: it prints and changes nothing. Python 3 standard library only.
"""
import sys
sys.dont_write_bytecode = True
import argparse
import json

import common as c


def main():
    root = c.tool_root()
    reg, _ = c.load_rules(root)
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--date", default=c.now().strftime("%Y%m%d"), help="YYYYMMDD")
    day = parser.parse_args().date

    print("END OF DAY VIEW for %s" % day)
    items = sorted((root / reg["inbox"]["path"]).glob("*_c*.md"))
    print("\nINBOX: %d item(s) waiting for a next step" % len(items))
    for path in items:
        meta, _ = c.read_frontmatter(c.read_text(path))
        print("  %s  %s" % ((meta or {}).get("id", "?")[:8], (meta or {}).get("title", path.name)))

    orders, currents = {}, []
    for folder, _, files in c.walk(root):
        if folder.name == "work-orders":
            for name in files:
                if name.startswith("WO-"):
                    meta, _ = c.read_frontmatter(c.read_text(folder / name))
                    if meta:
                        orders.setdefault(folder.parent, []).append(meta)
        if "CURRENT.md" in files:
            currents.append(folder)

    print("\nPROJECTS: %d" % len(currents))
    for folder in sorted(currents):
        meta, _ = c.read_frontmatter(c.read_text(folder / "CURRENT.md"))
        meta = meta or {}
        print("  %s  [%s]  updated %s" % (folder.relative_to(root).as_posix(),
                                          meta.get("status", "?"), meta.get("updated", "?")))
        print("    next step: %s" % meta.get("next_step", "MISSING"))
        print("    done when: %s" % meta.get("done_when", "MISSING"))
    print("\nWORK ORDERS NOT YET DELIVERED")
    waiting = 0
    for folder in sorted(orders):
        for meta in orders[folder]:
            if meta.get("status") in ("open", "verified", "accepted"):
                waiting += 1
                mode = {"contract-v1": ", contract evidence",
                        "legacy-technical": ", legacy evidence"}.get(
                            meta.get("evidence_mode"), "")
                print("  %s  [%s%s]  %s" % (meta.get("work_id"), meta.get("status"), mode,
                                            folder.relative_to(root).as_posix()))
                print("    next step: %s" % meta.get("next_step"))
                print("    done when: %s" % meta.get("done_when"))
    if not waiting:
        print("  none")

    counts, failures = {}, []
    for path in sorted((root / "logs" / "receipts").glob(day + "T*.json")):
        try:
            record = json.loads(c.read_text(path))
        except (OSError, ValueError):
            failures.append({"details": {"meant": "read receipt " + path.name,
                                         "failed": "receipt is not readable"}})
            continue
        key = "%s/%s" % (record.get("action"), record.get("outcome"))
        counts[key] = counts.get(key, 0) + 1
        if record.get("outcome") == "failed":
            failures.append(record)
    print("\nRECEIPTS TODAY: %d" % sum(counts.values()))
    for key in sorted(counts):
        print("  %-28s %d" % (key, counts[key]))
    print("\nFAILURES TODAY: %d" % len(failures))
    for record in failures:
        d = record.get("details", {})
        print("  meant: %s" % d.get("meant", d.get("redacted", "?")))
        print("    failed: %s | cause: %s | recovery: %s"
              % (d.get("failed", "?"), d.get("cause", "unknown"), d.get("recovery", "?")))


if __name__ == "__main__":
    main()
