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
  contract.py                 acceptance-contract validator (candidate, see below)
  capture.py                  capture, route, verify, record (the only inbox writer)
  lint.py                     structure and frontmatter check with real exit codes
  doctor.py                   health check and boundary canary
  search.py                   search scoped to one client plus shared folders
  eod.py                      end-of-day view
  uninstall.py                rollback: removes only what the installer created
tests/
  test_kit.py                 end-to-end test on synthetic data with canary secrets
  mutation_check.py           removes chosen guards in disposable copies; the tests must fail
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
python3 tools/capture.py close --work-id WO-c1a2b3c4 --contract     (candidate: instead of the line above, when the work order has an acceptance contract)
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
| Done means the stated criteria held for these exact bytes (candidate) | Optional acceptance contract per work order; all criteria evaluated; evidence bound to contract hash and artifact hash; stale evidence blocks accepted and delivered. | Local Linux only (63 to 75, plus 5 targeted mutants). Native CI pending |
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

## Acceptance contracts (candidate change)

Status: implemented and tested locally on Linux only (Python 3.11, 3.12 and 3.13). Not in
native CI. No install-ready release. The existing folder layout and the
existing states (open, verified, accepted, delivered, dropped) are unchanged.
There is no new database, service or dependency.

Scope of the change: one new module (`scripts/contract.py`), one new flag
(`capture.py close --contract`), a staleness check in `capture.py mark` and in
lint, a label in the end-of-day view, an example file in `4-templates/`, and
tests. Doctor needed no change: it already runs lint and reports its result.

**The file.** `work-orders/WO-<id>.contract.json`, next to `WO-<id>.md`:

```json
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
```

**Strict validation.** UTF-8 JSON of at most 65,536 bytes. Exactly the four
top-level keys. `contract_version` must be the integer 1. `work_id` must match
the work order. 1 to 50 criteria, each with a unique lowercase id, a type from
the three above, and single-line text of 1 to 500 characters; `ignore_case` is
optional and must be true or false. Refused: duplicate keys, unknown keys,
wrong types, other versions, empty or unsupported criteria, non-standard JSON
numbers, and contract text that matches the secret patterns.

**The artifact.** A path relative to the work order's own project folder, with
forward slashes. Refused: absolute paths, drive letters, backslashes, `..`,
`.`, empty or dot-first segments, anything under `work-orders/`, any link on
the path, a missing or empty file, more than 2,000,000 bytes, text that is not
valid UTF-8. Another client's folder is therefore out of reach.

**Evaluation.** The artifact is read once. Every criterion is evaluated on
those bytes with plain text comparison; nothing is executed and there are no
patterns. One failed criterion fails the contract. The failure receipt lists
each criterion id as pass or fail. Receipts hold ids, counts and hashes, never
contract text or artifact text.

**Binding.** A pass writes `evidence_mode: contract-v1`, `contract_sha256`,
`artifact` and `artifact_sha256` into the work order's frontmatter.

**Staleness.** Before `accepted` and before `delivered`, the tool recomputes
both hashes. A changed, missing or invalid contract, or a changed or missing
artifact, is refused with a failure receipt. Lint reports the same as an error
for verified and accepted work orders, and as a warning after delivery.
`close --contract` may be run again on a verified or accepted work order: a
pass sets it to verified (an earlier acceptance no longer applies), a failure
reopens it and removes the evidence fields.

**Legacy checks.** `--check-file` and `--check-cmd` still work for work orders
without a contract. They are recorded as `evidence_mode: legacy-technical` and
described as such in the output, the work order and the end-of-day view. They
are refused when a contract file exists, and a work order verified the legacy
way cannot be accepted or delivered once a contract is added until it passes
`close --contract`.

**What it does not establish.** That the criteria were good ones. That a person
reviewed anything: `--by` is typed text. That anything was delivered. That the
files were not edited directly, hashes included. See `KNOWN-GAPS.md`.

**Local results (Linux, synthetic data; tests on Python 3.11, 3.12 and 3.13, mutation check on 3.13).**
`python3 tests/test_kit.py`: 75 passed, 0 failed, 0 skipped.
`python3 tests/mutation_check.py`: 5 mutants, 5 killed, 0 survived, 0 invalid.
Each mutant removes one guard in a disposable copy: the all-criteria result,
the artifact-hash comparison, the contract-hash comparison, the refusal of
legacy checks when a contract exists, and the refusal in `mark`. This is not
mutation coverage.

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

## Independent review candidate, 14 November 2026

Current isolated candidate: 77 checks passed on Linux Python 3.10, no failures
or skips; five targeted mutations killed, none survived or invalid. Two checks
added after independent review reject a linked work-order boundary and control
characters in artifact paths. Native CI of this candidate is pending until the
updated commit runs. Historical native results above belong to baseline 5268eac,
not proof of the current upgrade. No real-user acceptance or delivery is proven.
