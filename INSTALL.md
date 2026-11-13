# Install

| Platform | Status |
| :--- | :--- |
| Linux, Python 3.13 | Native CI: 62 passed, no failures or skips |
| Linux, Python 3.10 | Native CI and independent local run: 62 passed |
| Mac | Native CI on Python 3.10 and 3.13: 62 passed. Manual steps below not yet tried on a personal Mac. |
| Windows | Native CI on Python 3.10 and 3.13: 61 passed, 1 POSIX-only check skipped. Manual first run pending. |

Automated tests passed, but the first manual install on Mac or Windows is still
a pilot test. Do it with the synthetic example only, and write down anything that does
not match these steps.

The installer creates one new folder and nothing else. It does not move, delete
or change any file you already have. If you change your mind, the last section
removes it again.

You will not be asked for any password or key at any point. If something asks
for one, stop.

## Mac (manual first run pending)

### 1. Open Terminal

Press Command and Space together, type `Terminal`, press Return. A window with
a text prompt opens. You type a line, then press Return to run it.

### 2. Check that Python is there

Type this and press Return:

```
python3 --version
```

- If you see `Python 3.8` or a higher number: good, go on.
- If the Mac offers to install "command line developer tools": click Install,
  wait for it to finish, then run the line again. (Expected Mac behaviour. Untested here.)
- If you see a lower number or an error: install Python 3 from python.org, then
  open a new Terminal window and run the line again.

### 3. Go to the kit folder

Type `cd ` (with a space after it), then drag the kit folder from Finder into
the Terminal window, then press Return. Check you are in the right place:

```
ls
```

You should see `README.md`, `INSTALL.md` and `scripts`.

### 4. Answer the intake questions

```
python3 scripts/intake.py --out my-answers.json
```

It asks one question at a time. `INTAKE.md` explains each one. Press Return to
skip a question. Nothing is installed yet.

### 5. Create the system

Pick a folder name that does not exist yet. A folder directly in your home
folder is the safest choice, because Desktop and Documents are often synced to
iCloud and sync tools can delete or replace folders.

```
python3 scripts/setup.py --answers my-answers.json --target ~/work-system
```

You should see `Created ... files` and `Check: lint: 0 error(s)`.
If it says the target is not empty, choose another name. There is no way to
force it, on purpose.

### 6. First run (synthetic example only)

```
cd ~/work-system
python3 tools/doctor.py
python3 tools/capture.py add --text "Example client asked for a one page summary"
python3 tools/eod.py
```

`eod.py` shows the item waiting in the inbox with a short id such as `c1a2b3c4`.
Use your id in the next lines:

```
python3 tools/capture.py route --id c1a2b3c4 --client "Example Client (synthetic)" --project "Sample Project" --next "Write the summary" --done-when "summary file exists in deliverables"
python3 tools/eod.py
```

Now make any small text file in
`1-clients/example-client-synthetic/sample-project/deliverables/` that starts
with these lines (this is the frontmatter every Markdown file needs):

```
---
title: Summary
type: note
status: active
created: 2026-01-01
---
```

Save it as `summary_draft_first.md`, then close the work order with that file as evidence:

```
python3 tools/capture.py close --work-id WO-c1a2b3c4 --check-file 1-clients/example-client-synthetic/sample-project/deliverables/summary_draft_first.md
python3 tools/capture.py mark --work-id WO-c1a2b3c4 --status accepted --by "Your Name"
python3 tools/capture.py mark --work-id WO-c1a2b3c4 --status delivered --by "Your Name"
python3 tools/lint.py
python3 tools/eod.py
```

If every line ran and `lint` says `0 error(s)`, the route works on your machine.

### 7. Before any real data: the boundary check

Private things (journal, passwords and keys, banking, health, private notes
about people) must live OUTSIDE the system folder. A written rule does not stop
an AI tool from reading a folder. Only the computer's own access control does.

Test it. Run this the same way your AI tool runs commands (ask the AI tool to
run it, do not only run it yourself), with the path of a folder that must stay private:

```
python3 tools/doctor.py --boundary-canary ~/path/to/private-folder
```

- `BOUNDARY BLOCKED`: that process cannot read the folder. Good.
- `BOUNDARY OPEN`: it can. The boundary is only a label. Options: run the AI
  tool under a separate Mac user account that has no access to the private
  folder, or keep the private folder on an encrypted disk image that stays
  locked while the AI tool runs. Then test again.

Then tick the four gates in `BOOT.md`, add one real project, and set its next step:

```
python3 tools/capture.py new-project --client "Real Client" --project "Real Project"
python3 tools/capture.py next --client "Real Client" --project "Real Project" --next "..." --done-when "..."
```

## Windows (manual first run pending)

Same steps, with these differences:

1. Open PowerShell: press the Windows key, type `PowerShell`, press Enter.
2. Use `py -3` wherever the Mac steps say `python3`. Check with `py -3 --version`.
   If that fails, install Python 3 from python.org and tick "Add python.exe to PATH".
3. Go to the kit folder with `cd`, then a space, then the folder path in quotes.
4. Install into your user folder, not into OneDrive:

```
py -3 scripts\intake.py --out my-answers.json
py -3 scripts\setup.py --answers my-answers.json --target ~/work-system
cd ~/work-system
py -3 tools\doctor.py
```

Windows risks beyond the synthetic CI checks: Desktop and Documents are often inside
OneDrive; links can turn into small text files (lint and doctor are written to
flag both links and such stubs); a folder that is open in another window may
refuse to be removed by uninstall.

## Remove it again (rollback)

From inside the system folder:

```
python3 tools/uninstall.py
```

This only shows the plan. To actually remove:

```
python3 tools/uninstall.py --yes
```

It removes the files the installer created and that you have not changed. It
leaves, and lists, everything else: files you added, files you edited, captured
items, work orders and receipts. If you want those gone too, delete the folder
by hand. Nothing outside the system folder is touched in either case.

## If something goes wrong

- Run `python3 tools/doctor.py`. Every line that is not `LIVE` comes with a `fix:` line.
- Run `python3 tools/lint.py`. Every `ERROR` line names the file and the problem.
- Nothing here needs the internet, an account, or a password.

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
