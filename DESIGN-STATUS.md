# FolderOS design and test status

This file is the full description of what the kit builds and how far each design rule was tested. The short entry page is README.md. Version 0.1.0-pilot. Status: pilot, native automated tests pass on Linux, macOS and Windows, Python 3.10 and 3.13. Windows skips POSIX-only test 45; manual first runs remain pending.

## What it is

A kit that creates one new folder on your computer for running client work and a
training or content business. Inside it:

- plain folders, one per client and project
- one short contract file (`context.md`) in every folder saying what the folder is for
- one inbox with one declared writer tool; a file written any other way is caught later by lint, not blocked
- a small set of readable Python scripts that capture, route, verify, record and report
- two identical root maps (`CLAUDE.md` and `AGENTS.md`) so any AI tool can find its way

There is no database, no server, no account and no network use. Everything is a
text file you can open.

The one idea behind it: **filed is not done.** Every captured item must become a
next action with a testable "done when", the result must be checked by a tool,
and the outcome (including failure) is written down.

## Who it is for

A first pilot user who is not technical, works on a Mac, runs client projects plus
training or content, and wants first of all to know the next step on every
client project. Money tracking is not built in. An optional folder for invoice
status notes exists and is off unless you switch it on in the intake.

## What is in the kit

```
DESIGN-STATUS.md             this file
INSTALL.md                    step-by-step install, Mac and Windows
INTAKE.md                     the intake interview and the answers file format
KNOWN-GAPS.md                 what is unproven
intake-answers.example.json   an example answers file
scripts/
  intake.py                   asks the intake questions, writes the answers file
  setup.py                    creates the new folder tree from the answers
  common.py                   shared helpers (copied into the new tree)
  capture.py                  capture, route, verify, record (the only inbox writer)
  lint.py                     structure and frontmatter check with real exit codes
  doctor.py                   health check and boundary canary
  search.py                   search scoped to one client plus shared folders
  eod.py                      end-of-day view
  uninstall.py                rollback: removes only what the installer created
tests/
  test_kit.py                 end-to-end test on synthetic data with canary secrets
```

## What gets created (default answers)

```
<your new folder>/
  CLAUDE.md  AGENTS.md        the same root map, twice, kept byte-identical
  BOOT.md                     priorities, environment, gates before real data
  VOICE.md                    your writing rules from the intake
  CHANGELOG.md                change ledger for the system itself
  0-inbox/                    single landing place (plus _routed, _discarded)
  1-clients/<client>/<project>/
      CURRENT.md              status, next step, done-when, running log
      assets/  deliverables/  work-orders/
  2-content/                  ideas, drafts, published, work-orders
  3-offers/
  4-templates/                CURRENT, work-order, brief and context templates
  5-archive/
  routing/registry.json       the ONE source for routing, naming, writer, search scope
  routing/taxonomy.json       the ONE source for types, statuses, required fields
  skills/
  logs/receipts/              one receipt per action, failures included
  tools/                      the scripts
  .install/install.json       the list of files the installer created
```

Every folder also holds a `context.md`. The names above are a neutral default.
The intake changes the client and project folders, and can switch off the
content folders.

## The daily and weekly rhythm

Daily (5 minutes): capture what arrived, then route or discard everything in the inbox.

```
python3 tools/capture.py add --text "Client asked for a new headline by Friday"
python3 tools/capture.py route --id c1a2b3c4 --client "client-name" --project "project-name" --next "Draft three headlines" --done-when "headlines file exists in deliverables"
python3 tools/eod.py
```

When the work is finished: close with evidence, then a person accepts it.

```
python3 tools/capture.py close --work-id WO-c1a2b3c4 --check-file 1-clients/client-name/project-name/deliverables/headlines_draft_first.md
python3 tools/capture.py mark --work-id WO-c1a2b3c4 --status accepted --by "Your Name"
python3 tools/capture.py mark --work-id WO-c1a2b3c4 --status delivered --by "Your Name"
```

Weekly (15 minutes): refresh the next step of every project.

```
python3 tools/capture.py next --client "client-name" --project "project-name" --next "..." --done-when "..."
python3 tools/lint.py
```

When something goes wrong, write it down instead of skipping it:

```
python3 tools/capture.py fail --meant "send the weekly summary" --failed "export crashed" --cause "unknown" --recovery not-tried
```

## How the design rules are enforced, and how far each was tested

Labels: **RUN-TESTED** below originally referred to the Linux checks. The full suite now also passes native macOS and Windows CI, with Windows test 45 skipped. **DESIGNED-FOR** means the code is written for it but it was not
run. **UNTESTED** means exactly that.

| Rule | How | Status |
| :--- | :--- | :--- |
| Install is additive only | Every file is created with "fail if it exists". Non-empty target refused. No force option exists. | RUN-TESTED (tests 06 to 11) |
| Rollback touches only installer files | Uninstall reads the install record and compares hashes. Your files, edited files and receipts stay. | RUN-TESTED (47 to 52) |
| One source of truth | Routing and naming only in `routing/registry.json`; types only in `routing/taxonomy.json`; the two root maps must be byte-identical or lint fails. | RUN-TESTED (04, 18, 20) |
| One inbox writer | Only `tools/capture.py` writes inbox items. Lint detects any other file by name and by content hash. This is detection after the fact, not a lock. | RUN-TESTED (17) |
| No duplicates | An item's id is a hash of its text. Same text, same id, no second entry. | RUN-TESTED (21, 22, 25) |
| Filed is not done | Route refuses without a next step and a done-when. | RUN-TESTED (23, 24) |
| Done means tool evidence | A work order closes only on a file check or a passing command. Then accepted by a person, then delivered, in that order. | RUN-TESTED (26 to 31) |
| Failures are recorded | Refusals and failed checks write a failure receipt with meant, failed, cause, recovery. | RUN-TESTED (23, 27, 32) |
| Lint never masks errors | Exit 0 clean, 1 errors, 2 cannot run. | RUN-TESTED (12 to 20) |
| Search does not cross clients | `tools/search.py` needs one client or shared-only. It scopes this tool only. | RUN-TESTED for the tool (37 to 39) |
| No secrets in the kit, logs or receipts | Secret-looking input is refused. Receipts never hold captured text. Doctor scans the tree. Pattern based, so best effort. | RUN-TESTED with four canaries (11, 33, 42, 46, 59) |
| Boundary is access control, not a label | Private material stays outside the folder. `doctor.py --boundary-canary` tests whether the running process can actually read a private folder. The kit cannot create the boundary for you. | Canary check RUN-TESTED on Linux (44, 45). Your real boundary: UNTESTED |
| No links or pointer stubs | Lint and doctor fail on any link in the tree and on a file that is only a path. Search never follows links. | RUN-TESTED on Linux (19, 43). Windows text-stub behaviour: UNTESTED |
| Log names cannot collide | Date, time with seconds, timezone, session id, counter. | RUN-TESTED (35, 36) |
| Works on a Mac | Standard library Python, no shell scripts, no links. | Native CI passed; manual first run pending |
| Works on Windows | Same. | Native CI passed except POSIX-only test 45 skipped; manual first run pending |
| Works with any AI tool | Plain files plus `CLAUDE.md` and `AGENTS.md`. | DESIGNED-FOR, no AI tool was run against it |

## Honest limits

- Native synthetic CI passed on Linux, Mac and Windows. No manual first run on
  a personal Mac or Windows PC, no real person or real data. See `KNOWN-GAPS.md`.
- The scripts cannot stop an AI tool, or you, from reading or writing files
  directly. They make the right path easy and make the wrong path visible in
  lint, doctor and the receipts.
- The secret check is a list of patterns. It will miss secrets that do not look
  like the patterns. Do not rely on it. Keep secrets out.
- There is no backup. Back the folder up yourself, and do not point a sync or
  mirror tool at it until that tool has been tested on a copy.
- Do not put real client data in until the four gates in `BOOT.md` are ticked.

## Run the test yourself

```
python3 tests/test_kit.py
```

It works in a temporary scratch folder with synthetic data and removes it afterwards.

## Automated platform evidence (13 Nov 2026)

Passing run: https://github.com/DigitalRavagers/folder-os/actions/runs/43407934320
Tested code commit: ee97bdd191bc5d1622d0a7feab3d9630d84e3429.
GitHub-hosted ubuntu-latest and macos-latest, each with Python 3.10 and 3.13:
62 passed, 0 failed, 0 skipped. Windows-latest with both Python versions:
61 passed, 0 failed, 1 skipped. Test 45 (permission-denied boundary canary)
is POSIX-only and was skipped on Windows. Windows access-control blocking
is not verified. These are synthetic scratch-folder tests, not a manual
first run on a person's Mac or Windows PC. No install-ready release is made.

Earlier runs found a .git text-scan error, a test function shadowed by a local
variable, and a real Windows command-quoting bug. All were fixed before the
passing run. The earlier failed runs remain visible in Actions.
