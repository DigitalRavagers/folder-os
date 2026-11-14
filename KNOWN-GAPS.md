# Known gaps

What was actually run: `tests/test_kit.py`, run clean on Linux on synthetic data: by the kit's
author (Python 3.13, running as the root user) and again by an independent reviewer (Python 3.10,
non-root, 62 checks after the review fixes below). Native CI now also passes on Mac and Windows; see the platform evidence below.
Everything below is unproven. Treat each line as a test still to do.

## Platforms and machines

| Gap | Why it matters | How to close it |
| :--- | :--- | :--- |
| **Mac: automated tests pass; manual first run pending.** | The pilot user is on a Mac. Python availability, the developer tools prompt, Finder's `.DS_Store` files, iCloud-synced Desktop and Documents, and case-insensitive disks are all untested. | Run `INSTALL.md` and `tests/test_kit.py` on a Mac. Record the output. |
| **Windows: automated tests pass; manual first run pending.** | The command-quoting bug found by CI is fixed. Manual `py -3` steps, sync/antivirus file locking and personal-PC permissions remain unverified. | Same, on Windows. |
| **A second machine: never tried.** | Moving or copying the folder to another computer, line-ending changes, different timezones in receipt names. | Copy an installed tree to a second machine, run doctor and lint there. |
| **Older Python: not run.** | The code is written for 3.8 and later but only 3.13 and 3.10 were run. | Run the test on the Mac's own Python version. |
| **Non-English file names and text: not tested.** | Client names with accents or other scripts become folder names with those letters dropped. | Try the intake with such names. |

## People and data

| Gap | Why it matters | How to close it |
| :--- | :--- | :--- |
| **No real user.** | The intake wording, the install steps and the commands have never been read by a non-technical person. Typing long command lines may be too much without an AI tool doing it. | Watch the pilot user do the install without help. Note every place they stop. |
| **No real data.** | Synthetic items are short and clean. Real captures are long, messy and arrive as files, which `capture.py` does not ingest (text only; files are placed in `assets` by hand). | One real project, after the BOOT.md gates are ticked. |
| **No week of use.** | The daily and weekly rhythm is a design, not an observation. | Two weeks of receipts from the pilot. |

## AI tools (harnesses)

| Gap | Why it matters | How to close it |
| :--- | :--- | :--- |
| **No AI tool was run against the tree.** | Whether a given tool reads `CLAUDE.md` or `AGENTS.md`, follows `context.md`, and uses `tools/search.py` instead of its own search is unknown. | Open the synthetic tree in the chosen tool and ask it to run the first-run steps. |
| **Cross-harness handoff test: not done.** | The claim that work can pass between two different AI tools through files alone is untested. | Tool A routes an item, tool B closes it, compare receipts. |
| **Scoped search binds only `tools/search.py`.** | An AI tool with its own search can still read every client folder. Client separation is therefore a habit plus a detector, not a wall. | Open the AI tool inside one client folder only, or use the tool's own folder restrictions, and test them with a canary term. |
| **The one-writer rule is detection, not prevention.** | Any program can still drop a file into the inbox. Lint will flag it afterwards. | Operating system permissions on the inbox, if the pilot shows it is needed. |

## Security

| Gap | Why it matters | How to close it |
| :--- | :--- | :--- |
| **The real boundary does not exist yet.** | The kit only tests a boundary (`doctor.py --boundary-canary`). Creating it (separate user account or locked encrypted volume) is manual and unverified on the pilot machine. | Do it, then run the canary from inside the AI tool. |
| **The canary test was run as root dropping to another user.** | That proves the check tells open from blocked on Linux. Native macOS CI now also passes this test. It says nothing about a personal Mac or an AI tool's sandbox. | Run on the Mac, from the AI tool. |
| **Secret detection is a pattern list.** | Seven patterns. Four canaries were tested. A password with no label next to it passes straight through. Long numbers such as phone lists can be refused by mistake. | Keep secrets out by habit. Extend the patterns from real misses. |
| **No inventory of the user's data and secrets.** | Gate 1 in BOOT.md. Nothing in the kit does this for you. | Write it by hand before real data. |
| **Sync and mirror tools: untested.** | Doctor warns when the path looks synced. No sync tool was run against the tree. | Test any sync tool on a copy first. |
| **No backup.** | The kit does not back anything up. | Decide a backup in the intake (question 13) and test a restore. |

## Acceptance contracts (candidate change, local results only)

What was run: on one Linux sandbox (Python 3.11, 3.12 and 3.13 for the tests, 3.13 for the mutation check; root user, synthetic data),
`tests/test_kit.py` passed 75 checks (the 62 existing ones plus 13 new, numbered
63 to 75) and `tests/mutation_check.py` killed 5 of 5 hand-picked mutants.
Nothing else is proven. In particular:

| Gap | Why it matters | How to close it |
| :--- | :--- | :--- |
| **Not run in native CI.** | The 62-check native results on Linux, Mac and Windows are for the code before this change. Path, link and line-ending handling for contracts is untested on Mac and Windows, and on Python 3.10 (not available where this was built). | Run the workflow on the candidate. |
| **Human acceptance is unproven.** | `mark --by` records whatever name is typed. There is no login, signature or second person. A tool can type a person's name. | A real review step by the pilot user, observed. |
| **Real handoff is unproven.** | "delivered" is a status in a text file. Nothing checks that a client received the bytes that were verified. | Compare the stored artifact hash with the file actually sent. |
| **Direct edits defeat it.** | The contract, the artifact, the work order and the stored hashes are all plain files. Anyone who can edit them can rewrite the hashes to match. The mechanism detects honest drift, not tampering. | Operating system permissions or signed records, if the pilot shows a need. |
| **Criteria can be weak.** | The tool checks the criteria it is given. A contract with one trivial check passes trivially. The contract author can also be the one doing the work. | A person writes or reviews the contract before work starts. |
| **Literal text checks only.** | No structure, no numbers, no meaning. `has_line` compares whole lines after trimming spaces; there is no Unicode normalisation. One artifact per contract, UTF-8 text, at most 2,000,000 bytes. | Extend criterion types only from real misses. |
| **Check and use are separate moments.** | The artifact is read once and those bytes are both checked and hashed, but a file can still be swapped between verification and sending. A link check followed by a read is not atomic. | Re-verify immediately before sending. |
| **Old work orders.** | Work orders closed before this change have no evidence mode and are treated as legacy. Nothing upgrades them. | Add a contract and run `close --contract`. |
| **Mutation check is narrow.** | Five chosen guards. It is not mutation coverage and says nothing about code it does not list. One mutant was first reported INVALID because the test suite crashed instead of failing; the test helper was fixed and the run repeated. | Add mutants when a guard is added. |
| **Installer counts changed.** | Setup now creates 50 files, not 48 (the validator and an example contract). RELEASE-REVIEW.md still describes the earlier code and was left as it was. | Update the review record after independent review. |

## Things not built

- Voice checking. `VOICE.md` holds the rules. No script checks drafts against them.
- File capture. `capture.py` takes text only.
- Editing or merging duplicates that differ by a word. Idempotency is exact-text (ignoring spacing) only.
- Two people or two processes using the tree at the same moment. Files are
  created with "fail if it exists", but concurrent use was not tested.
- Version history. Git is optional and nothing sets it up.
- Automatic archiving. Moving a finished project to `5-archive` is by hand.
- Upgrading an installed tree to a newer kit version. There is no upgrade path
  yet, and the installer will refuse the existing folder, by design.

## Design input that was not verified

The source notes this kit was distilled from make claims that were used as
ideas only and are not claimed here: token savings from context isolation, the
60-30-10 split between files, rules and model calls, and the idea that folder
contracts alone make an AI tool behave. Two choices also differ from those
notes on purpose: live state is computed by `tools/eod.py` instead of being
copied into `BOOT.md` (one source, not two), and there is no folder for
syncing outside repositories (sync tools must not be able to replace real folders).

## Found while building

The first full test run failed two checks. One was a real defect: uninstall
crashed while listing leftover files, after it had already removed the
installer's files. It was fixed and the run repeated clean. This is recorded
because a kit that reports only its passing run is not following its own rules.

## Review notes (independent bounded code review, before any real use)

- **Fixed:** uninstall trusted the folder list in its install record and could remove an empty folder
  outside the system folder if that record was edited. It now ignores any entry that is not inside the
  folder, is a link, or is the folder itself (test 62).
- **Fixed:** evidence for closing a work order could be any non-empty file in the tree, including the
  work order itself. It must now sit inside that work order's own project folder (test 61).
- **Wording fixed:** the inbox has one declared writer tool; lint detects other writers afterwards. It does
  not block them.
- **Open, by design:** `capture.py close --check-cmd` runs whatever program you name, with your own
  permissions, and treats exit code 0 as a pass. It proves a check ran, not that the check was good.
  Anyone, or any AI tool, that can run the kit's tools can run a command this way. Read the command
  before approving it. Windows CI exposed a quoting bug, now fixed and passing.
- **Open:** a person who can edit the install record can still make uninstall delete files inside the
  system folder. The record sits next to the files it describes, so it is not a security boundary.
- **Windows/Mac native CI completed:** the permission-denied test (45) is POSIX-only and is
  reported as SKIPPED elsewhere, not passed. Symlink checks are skipped where links cannot be made.
  Untested risks: Windows long paths and file locking by sync or antivirus tools, case-insensitive
  disks (Mac default, Windows) with names that differ only by case, and the old Mac Python shim.
  Synthetic native CI is now green on both; manual first-run compatibility remains pending.

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

## Independent review correction (14 November 2026)

A synthetic edge probe found that a linked work-order file could relocate the
evidence boundary through path resolution. Work-order lookup and contract load
now reject linked work orders and linked ancestors before reading evidence.
Tests 76 and 77 cover that boundary and control characters in artifact paths.
The native workflow now runs the targeted mutation check as well as the suite.
These changes still do not turn typed names into authenticated human approval.
