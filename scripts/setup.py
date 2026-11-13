#!/usr/bin/env python3
"""Create a new folder system from intake answers.

  python3 setup.py --answers intake-answers.json --target ~/work-system

ADDITIVE ONLY. It creates one new folder tree and nothing else.
  * It refuses a target that already has anything in it.
  * It never moves, deletes or overwrites a file. Every file is created with
    "fail if it exists". There is no force option, on purpose.
  * It writes nothing outside the target folder.
  * It records every file it creates in .install/install.json so that
    tools/uninstall.py can remove exactly those files and no others.
Python 3 standard library only. No network. No credentials.
"""
import sys
sys.dont_write_bytecode = True
import argparse
import json
import os
import platform
import subprocess
from pathlib import Path

import common as c

KIT = Path(__file__).resolve().parent
TOOLS = ["common.py", "capture.py", "lint.py", "doctor.py", "search.py", "eod.py",
         "uninstall.py"]
ALWAYS_OUT = ["personal journaling", "passwords, API keys and other credentials",
              "banking and card details", "health information",
              "private notes about people"]

CONTEXT_TPL = """---
title: Contract for {{folder}}
type: contract
status: active
created: {{date}}
---
# {{folder}}

Purpose: {{purpose}}

- Input (read first): {{input}}
- Do: {{do}}
- Output: {{output}}
- Human check (stop and wait here): {{check}}
- Hard skip (do not read): {{skip}}

Rules are not repeated here. Routing and naming: routing/registry.json.
Types and statuses: routing/taxonomy.json.
"""

CURRENT_TPL = """---
title: {{project_name}} current state
type: current
client: {{client}}
project: {{project}}
status: setup
next_step: Write the first real next step for this project
done_when: tools/capture.py next has been run for this project and its status is active
created: {{date}}
updated: {{date}}
---
# {{project_name}} ({{client_name}}): CURRENT

The lines that matter are at the top of this file: status, next_step, done_when, updated.
Change them with tools/capture.py next so the change is logged. Refresh them every week.

## Notes

## Running log
- {{date}} Project folder created.
"""

WORK_ORDER_TPL = """---
title: {{title}}
type: work-order
work_id: {{work_id}}
status: open
room: {{room}}
source_item: {{source_item}}
next_step: {{next_step}}
done_when: {{done_when}}
created: {{date}}
---
# {{work_id}}

## Request (as captured)
{{request}}

## Input files

## Acceptance criteria
- {{done_when}}

## Produced artifacts

## States
open, then verified (tool evidence), then accepted (a person), then delivered.
Change state only with tools/capture.py close and tools/capture.py mark.

## Evidence and state log
- {{date}} Opened.
"""

BRIEF_TPL = """---
title: {{title}}
type: brief
status: draft
created: {{date}}
---
# Brief: {{title}}

## Who it is for

## What they asked for (their words)

## What a good result looks like (testable)

## What a failed or sloppy result looks like

## Inputs and where they live

## Human check before it goes out

## Out of scope
"""

MAP_TPL = """# Root map

This exact text ships as both CLAUDE.md and AGENTS.md so any AI tool finds it.
The two files must stay byte-identical. tools/lint.py fails if they differ.

Owner: {{owner}}. Installed {{date}}. Kit {{version}}.

## Where each rule lives (one place each)

| Rule | Only source |
| :--- | :--- |
| Routing, naming, inbox writer, search scope, review gates, what stays out | routing/registry.json |
| Types, statuses, required fields | routing/taxonomy.json |
| The job of one folder | that folder's context.md |
| Current state | computed by tools/eod.py from the files |
| Priorities and environment notes | BOOT.md |
| Voice | VOICE.md |

This map is a summary. If anything here or elsewhere disagrees with
routing/registry.json, registry.json wins and the other text is a bug to fix
and record with tools/capture.py change.

## Floor plan

| Folder | Job |
| :--- | :--- |
{{floor}}

## How work moves

1. Capture: everything new goes in through tools/capture.py add. Nothing else writes to the inbox.
2. Route: tools/capture.py route turns an item into a work order. It refuses without a next step and a testable done-when. Filing is not doing.
3. Do the work inside one room. Read that room's context.md first.
4. Verify: tools/capture.py close needs tool evidence (a file check or a command that passes). Saying "done" closes nothing.
5. A person accepts, then it is delivered: tools/capture.py mark.
6. Record: every step writes a receipt in logs/receipts. Failures are recorded with tools/capture.py fail, never skipped.
7. Learn: corrections go in CHANGELOG.md through tools/capture.py change.

## Session start (for an AI tool)

1. Read BOOT.md.
2. Run tools/eod.py to see the current state.
3. Read the context.md of the ONE folder you will work in. Do not open other clients' folders.
4. Search only with tools/search.py, which is scoped to one client plus shared folders.
5. Ask before deleting, moving or overwriting anything. Never create links or pointer files in place of real content.
6. Never store or ask for passwords or keys. The keep-out list is in routing/registry.json.
"""

BOOT_TPL = """---
title: BOOT state ledger
type: state
status: active
created: {{date}}
---
# BOOT

Live state is not copied here. Run tools/eod.py to compute it from the files.
This file holds what the files cannot say: priorities, environment, open gates.

## Priorities (edit by hand, keep to three)
1. Run the synthetic example project end to end.
2. Pick one real project and set its next step.
3.

## Environment
- Installed: {{date}} on {{platform}} with Python {{python}}
- AI tool (harness): {{harness}}
- Storage and backup: {{storage}}

## From the intake
- Work: {{work}}
- Weekly task to systematise: {{weekly}}
- Where material arrives: {{arrivals}}
- A failed result looks like: {{failure}}
- Corrections from the intake review: {{corrections}}

## Gates before any real data (tick only with evidence)
- [ ] Inventory written: what data and secrets exist, and where they live outside this folder
- [ ] Private material is outside this folder behind real access control
- [ ] Canary: tools/doctor.py --boundary-canary reports BOUNDARY BLOCKED when run the way the AI tool runs
- [ ] Log cleanliness: tools/doctor.py secret scan is live

## Pilot is done when
- [ ] capture, route, close and mark have run on one real project
- [ ] the receipts show what happened, including failures
- [ ] the owner can state the next action for every active project without help
"""

VOICE_TPL = """---
title: Voice
type: voice
status: active
created: {{date}}
---
# Voice

Rules given in the intake. Edit this file when they change.

{{rules}}
"""

CHANGELOG_TPL = """---
title: Change ledger
type: changelog
status: active
created: {{date}}
---
# Change ledger

One line per change to the system itself (rules, folders, tools), newest last.
Add lines with tools/capture.py change so each one has a time and a session id.

- {{time}} [{{session}}] System installed from kit {{version}}. Why: first install.
"""

TAXONOMY = {
    "format_version": 1,
    "note": "The only place types, statuses and required fields are defined. "
            "tools/lint.py enforces this file.",
    "base_required": ["title", "type", "status", "created"],
    "types": {
        "contract": {"required": [], "statuses": ["active"]},
        "state": {"required": [], "statuses": ["active"]},
        "voice": {"required": [], "statuses": ["active"]},
        "changelog": {"required": [], "statuses": ["active"]},
        "current": {"required": ["client", "project", "next_step", "done_when", "updated"],
                    "statuses": ["setup", "active", "waiting", "done", "archived"]},
        "work-order": {"required": ["work_id", "room", "next_step", "done_when"],
                       "statuses": ["open", "verified", "accepted", "delivered", "dropped"],
                       "required_when": {"verified": ["evidence"], "accepted": ["evidence"],
                                         "delivered": ["evidence"]}},
        "inbox-item": {"required": ["id", "source", "captured", "writer"],
                       "statuses": ["new", "routed", "discarded"],
                       "required_when": {"routed": ["routed_to"], "discarded": ["reason"]}},
        "brief": {"required": [], "statuses": ["draft", "approved"]},
        "content": {"required": [], "statuses": ["idea", "draft", "review", "published"]},
        "offer": {"required": [], "statuses": ["draft", "live", "retired"]},
        "note": {"required": [], "statuses": ["active", "archived"]},
    },
}

# folder: (purpose, input, do, output, hard skip)
ROOMS = {
    "0-inbox": ("The one landing place for anything new. Only tools/capture.py writes here.",
                "Text handed to tools/capture.py add.",
                "Every day, route or discard each item. Never edit or add files by hand.",
                "Each item becomes a work order (route) or is closed with a reason (discard).",
                "all client folders"),
    "0-inbox/_routed": ("Inbox items that became work orders. Kept as a trail.",
                        "Nothing. Written by tools/capture.py route.", "Leave as is.",
                        "None.", "everything else"),
    "0-inbox/_discarded": ("Inbox items closed with a reason and no action.",
                           "Nothing. Written by tools/capture.py discard.", "Leave as is.",
                           "None.", "everything else"),
    "1-clients": ("Client work. One folder per client, one subfolder per project.",
                  "Only the one client folder you were asked to work in.",
                  "Add projects with tools/capture.py new-project.",
                  "Nothing is written at this level.", "every client folder except the active one"),
    "4-templates": ("Blank forms that the tools copy: CURRENT, work order, brief, context.",
                    "The template you need.", "Edit a template to change all future copies.",
                    "None. Copies are written elsewhere.", "all client folders"),
    "5-archive": ("Finished or stopped work that is kept for reference.",
                  "Only what you were asked to look up.",
                  "Move a whole project folder here by hand when it is finished, and log it "
                  "with tools/capture.py change.", "None.", "all active client folders"),
    "routing": ("The rule books: registry.json and taxonomy.json. One source for each rule.",
                "registry.json, taxonomy.json.",
                "Change a rule here and nowhere else. Log it with tools/capture.py change.",
                "Updated rule files.", "all client folders"),
    "skills": ("Reusable how-to notes and small helpers. Real files only, never links or pointers.",
               "The one skill the task names.", "Add a skill as a real Markdown file with frontmatter.",
               "Skill files of type note.", "all client folders"),
    "logs": ("Records of what the tools did.", "logs/receipts.", "Read only.", "None.",
             "all client folders"),
    "logs/receipts": ("One JSON receipt per tool action, including every failure. "
                      "Receipts hold ids and outcomes, never captured text.",
                      "Today's receipts, usually through tools/eod.py.",
                      "Never edit or delete receipts.", "Written only by the tools.",
                      "all client folders"),
    "tools": ("The small scripts that run the system.", "The docstring at the top of a script.",
              "Run them. Do not edit them without logging the change.", "None.",
              "all client folders"),
}
CONTENT_ROOMS = {
    "2-content": ("Training and content work, from idea to published.",
                  "work-orders, then the stage folder you are in.",
                  "Move a piece forward one stage at a time: ideas, drafts, published.",
                  "Files of type content.", "all client folders"),
    "2-content/ideas": ("Raw ideas worth keeping.", "The idea file.",
                        "Write one idea per file, status idea.", "Idea files.", "all client folders"),
    "2-content/drafts": ("Pieces being written.", "The idea it came from, and VOICE.md.",
                         "Draft, then check against VOICE.md.", "Draft files, status draft or review.",
                         "all client folders"),
    "2-content/published": ("Final versions that went out, with the date in the filename.",
                            "The approved draft.", "Store the final text as published.",
                            "Published files, status published.", "all client folders"),
    "2-content/work-orders": ("Next actions for content, each with a testable done-when.",
                              "Created by tools/capture.py route --content.",
                              "Do the work, then close with evidence.",
                              "Work orders that end as delivered or dropped.", "all client folders"),
    "3-offers": ("What is for sale: courses, packages, services. No prices history, no money tracking.",
                 "The offer file.", "One offer per file, type offer.", "Offer files.",
                 "all client folders"),
}
MONEY_ROOM = {
    "6-money": ("OPTIONAL module, switched on in the intake. Invoice status notes only "
                "(sent, due, paid). Never bank details, card numbers or logins.",
                "The note for the invoice in question.", "One note per invoice, type note.",
                "Note files.", "all client folders"),
}


def load_answers(path):
    try:
        raw = c.read_text(path)
        answers = json.loads(raw)
    except (OSError, ValueError) as error:
        c.die("Cannot read the answers file (%s). Nothing was created." % type(error).__name__)
    hit = c.find_secret(raw)
    if hit:
        c.die("The answers file looks like it contains a secret (%s). Remove it and run "
              "again. Nothing was created." % hit)
    if not isinstance(answers, dict) or answers.get("format_version") != 1:
        c.die("The answers file must be a JSON object with \"format_version\": 1.")
    if not c.one_line(answers.get("owner_name", "")):
        c.die("The answers file needs an owner_name.")
    clients = answers.get("clients", [])
    for entry in clients:
        names = [entry.get("name", "")] + list(entry.get("projects", [])) \
            if isinstance(entry, dict) else [""]
        if not all(c.slug(n) for n in names) or len(names) < 2:
            c.die("Each client needs a name and at least one project name.")
    return answers


def check_target(target):
    if target.is_symlink():
        c.die("The target is a link. Give a real folder path.")
    if target.exists():
        if not target.is_dir():
            c.die("The target exists and is not a folder.")
        found = [n for n in os.listdir(target) if n not in c.IGNORED_NAMES]
        if found:
            c.die("The target folder is not empty (%d item(s) found). This installer only "
                  "creates a new tree and never overwrites. Choose a folder name that does "
                  "not exist yet. There is no force option." % len(found))
    elif not target.parent.is_dir():
        c.die("The folder that should contain the target does not exist: %s" % target.parent)
    if c.inside(KIT.parent, target) or c.inside(target, KIT):
        c.die("Choose a target outside the kit folder.")


def listing(values, fallback):
    values = [c.one_line(v) for v in values if c.one_line(v)]
    return values or [fallback]


def build(answers):
    """Return {relative path: text} for every file of the new tree."""
    date = c.today()
    owner = c.one_line(answers["owner_name"])
    content = bool(answers.get("content_business", True))
    money = bool(answers.get("modules", {}).get("money", False))
    gates = listing(answers.get("review_gates", []), "Before anything is sent to a client")
    gate = "; ".join(gates)
    rooms = dict(ROOMS)
    rooms.update(CONTENT_ROOMS if content else {})
    rooms.update(MONEY_ROOM if money else {})
    files = {}
    for folder, (purpose, read, do, output, skip) in rooms.items():
        files[folder + "/context.md"] = c.context_text(
            CONTEXT_TPL, folder, purpose, read, do, output, gate, skip, date)
    clients = [{"name": "Example Client (synthetic)", "projects": ["Sample Project"]}] \
        if answers.get("include_synthetic_example", True) else []
    for entry in clients + answers.get("clients", []):
        for project in entry["projects"]:
            files.update(c.project_files(CONTEXT_TPL, CURRENT_TPL, "1-clients",
                                         c.one_line(entry["name"]), c.one_line(project),
                                         date, gate))
    files["4-templates/context.template.md"] = CONTEXT_TPL
    files["4-templates/CURRENT.template.md"] = CURRENT_TPL
    files["4-templates/work-order.template.md"] = WORK_ORDER_TPL
    files["4-templates/brief.template.md"] = BRIEF_TPL

    sources = ["manual"] + [s for s in (c.slug(v) for v in answers.get("arrival_points", []))
                            if s and s != "manual"]
    registry = {
        "format_version": 1,
        "note": "The only place routing, naming, the inbox writer, search scope, review "
                "gates and the keep-out list are defined. If another file disagrees, this "
                "file wins.",
        "owner": owner,
        "inbox": {"path": "0-inbox", "writer": "tools/capture.py", "sources": sources},
        "rooms": {"clients": "1-clients", "content": "2-content" if content else None},
        "templates": "4-templates",
        "routes": [
            {"when": "It belongs to a client project",
             "do": "tools/capture.py route --id ID --client CLIENT --project PROJECT "
                   "--next \"...\" --done-when \"...\""},
            {"when": "It is an idea or task for training or content",
             "do": "tools/capture.py route --id ID --content --next \"...\" --done-when \"...\""},
            {"when": "It needs no action",
             "do": "tools/capture.py discard --id ID --reason \"...\""},
            {"when": "It is on the keep_out list",
             "do": "Do not capture it. It stays outside this system."},
        ],
        "naming": {
            "slug": {"rule": "lowercase letters, numbers and hyphens",
                     "pattern": "^[a-z0-9]+(-[a-z0-9]+)*$"},
            "inbox_item": {"rule": "<YYYYMMDD>_<item id>.md",
                           "pattern": "^\\d{8}_c[0-9a-f]{15}\\.md$"},
            "work_order": {"rule": "WO-<first 8 characters of the item id>.md",
                           "pattern": "^WO-c[0-9a-f]{7}\\.md$"},
            "receipt": {"rule": "<YYYYMMDD>T<HHMMSS><timezone offset>_<session id>_"
                                "<counter>_<action>.json",
                        "pattern": "^\\d{8}T\\d{6}[+-]\\d{4}_[A-Za-z0-9]{1,32}_\\d{3,}_[a-z-]+\\.json$"},
            "revision": {"rule": "<name>_<draft or v2, v3 ...>_<short-description>.<ext>"},
            "dated_file": {"rule": "<YYYY-MM-DD>_<type>_<short-description>.md"},
        },
        "search": {"shared_whitelist": ["4-templates", "skills", "routing"]},
        "frontmatter_exempt": ["CLAUDE.md", "AGENTS.md"],
        "required_files": ["CLAUDE.md", "AGENTS.md", "BOOT.md", "VOICE.md", "CHANGELOG.md",
                           "routing/registry.json", "routing/taxonomy.json",
                           "4-templates/context.template.md", "4-templates/CURRENT.template.md",
                           "4-templates/work-order.template.md", "4-templates/brief.template.md"],
        "review_gates": gates,
        "keep_out": ALWAYS_OUT + [v for v in listing(answers.get("keep_out", []), "")
                                  if v and v not in ALWAYS_OUT],
        "modules": {"money": money},
    }
    files["routing/registry.json"] = json.dumps(registry, indent=2) + "\n"
    files["routing/taxonomy.json"] = json.dumps(TAXONOMY, indent=2) + "\n"

    tops = sorted(set(name.split("/")[0] for name in rooms))
    floor = "\n".join("| %s/ | %s |" % (name, rooms[name][0]) for name in tops)
    root_map = c.fill(MAP_TPL, owner=owner, date=date, version=c.KIT_VERSION, floor=floor)
    files["CLAUDE.md"] = root_map
    files["AGENTS.md"] = root_map

    def said(key, fallback="not answered in the intake"):
        value = answers.get(key, "")
        value = ", ".join(value) if isinstance(value, list) else value
        return c.one_line(value) or fallback

    files["BOOT.md"] = c.fill(
        BOOT_TPL, date=date, platform=platform.system() or "unknown",
        python=platform.python_version(), harness=said("harness", "unconfirmed"),
        storage=said("storage", "unconfirmed"), work=said("work_summary"),
        weekly=said("weekly_task"), arrivals=said("arrival_points"),
        failure=said("failure_definition"), corrections=said("corrections", "none given"))
    rules = listing(answers.get("voice_rules", []), "No voice rules were given in the intake.")
    files["VOICE.md"] = c.fill(VOICE_TPL, date=date, rules="\n".join("- " + r for r in rules))
    files["CHANGELOG.md"] = c.fill(CHANGELOG_TPL, date=date, time=c.iso(), session=c.SESSION,
                                   version=c.KIT_VERSION)
    for name in TOOLS:
        files["tools/" + name] = c.read_text(KIT / name)
    return files


def install(target, files):
    preexisted = target.exists()
    made_dirs, made_files = [], []
    try:
        if not preexisted:
            target.mkdir()
        for name in sorted(files):
            parts = name.split("/")[:-1]
            for depth in range(1, len(parts) + 1):
                folder = "/".join(parts[:depth])
                if not (target / folder).exists():
                    (target / folder).mkdir()
                    made_dirs.append(folder)
            c.write_new(target / name, files[name])
            made_files.append(name)
        (target / ".install").mkdir()
        made_dirs.append(".install")
        receipt = c.receipt(target, "install", "installed", files=len(made_files))
        made_files.append(receipt.relative_to(target).as_posix())
        manifest = {
            "kit_version": c.KIT_VERSION, "installed": c.iso(),
            "platform": platform.system(), "python": platform.python_version(),
            "target_preexisted": preexisted, "dirs": made_dirs,
            "files": {name: c.sha256_file(target / name) for name in made_files},
        }
        c.write_new(target / c.MANIFEST, json.dumps(manifest, indent=2) + "\n")
    except BaseException:
        # Undo only what this run created, then report the failure.
        for name in made_files + [c.MANIFEST]:
            if (target / name).is_file():
                (target / name).unlink()
        for folder in sorted(made_dirs, key=len, reverse=True):
            if (target / folder).is_dir():
                (target / folder).rmdir()
        if not preexisted and target.is_dir():
            target.rmdir()
        print("ERROR: install failed part way. Everything this run created was removed.",
              file=sys.stderr)
        raise
    return len(made_files)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--answers", required=True, help="the intake answers file (JSON)")
    parser.add_argument("--target", required=True, help="new folder to create")
    args = parser.parse_args()
    target = Path(args.target).expanduser().absolute()
    check_target(target)
    answers = load_answers(Path(args.answers).expanduser())
    count = install(target, build(answers))
    print("Created %d files in %s" % (count, target))
    lint = subprocess.run([sys.executable, str(target / "tools" / "lint.py")],
                          capture_output=True, text=True)
    print("Check: " + (lint.stdout.strip().splitlines() or ["lint gave no output"])[-1])
    if lint.returncode != 0:
        print(lint.stdout)
        c.die("The new tree did not pass its own lint. Please report this.", code=1)
    print("Next: open INSTALL.md at the step called 'First run'.")


if __name__ == "__main__":
    main()
