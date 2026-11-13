# FolderOS

A local folder system for client projects and content work, with explicit next steps and an evidence-backed completion log.

**Pilot candidate: 0.1.0-pilot. Not yet validated on macOS or Windows.**

> Pilot source, published to get real macOS and Windows test results. There is no install-ready release yet.

## What it does

FolderOS creates a new workspace with client/project folders, short folder descriptions, a capture inbox, work orders and action receipts. Plain Python scripts capture an item, route it to a project with a next step, check completion evidence and show unfinished work.

The files are readable without a database or a server. The supplied scripts use Python's standard library. There is no automatic cloud sync or backup. Secrets and private material must stay out of this workspace.

## What the workspace looks like

```text
work-system/
  CLAUDE.md, AGENTS.md       matching workspace maps
  BOOT.md, VOICE.md          first-run gates and writing rules
  0-inbox/                  captured items
  1-clients/<client>/<project>/
    CURRENT.md              status and next action
    assets/, deliverables/, work-orders/
  2-content/, 3-offers/, 4-templates/, 5-archive/
  routing/                  naming and routing rules
  logs/receipts/             action results, including failures
  tools/                    local scripts
```

The intake can change client/project names and disable content folders. This is an output excerpt, not a claim that installation has run on your machine.

## Requirements and current evidence

Python 3 is required. The kit is written for Python 3.8+, but that lower bound has not been run-tested. Before a release, declare the minimum version supported by actual results.

| Environment | Evidence in the supplied kit |
| --- | --- |
| Linux, Python 3.13 | Author-run synthetic tests recorded. |
| Linux, Python 3.10, non-root | Independent review records 62 passing checks after fixes. Not rerun for this README review. |
| macOS | Native tests and manual first run pending. |
| Windows | Native tests and manual first run pending. |
| AI assistants | File-based design; no assistant or cross-assistant handoff has been run-tested. |

## First run: synthetic data only

Start inside this repository's folder (download it as a ZIP from GitHub's Code button and extract it, or clone it). Use only this repository, not a copy from elsewhere.

Check Python and run the kit's tests:

```sh
# macOS / Linux
python3 --version
python3 tests/test_kit.py
```

```powershell
# Windows
py -3 --version
py -3 tests/test_kit.py
```

Inspect `intake-answers.example.json`. It contains synthetic client/project data. Choose a new folder outside your existing projects and sync folders. Setup creates files; it is not a preview command.

```sh
# macOS / Linux, from the kit directory
python3 scripts/setup.py --answers intake-answers.example.json --target ~/folderos-demo
cd ~/folderos-demo
python3 tools/doctor.py
python3 tools/lint.py
python3 tools/eod.py
```

```powershell
# Windows PowerShell, from the kit directory
py -3 scripts/setup.py --answers intake-answers.example.json --target ~/folderos-demo
cd ~/folderos-demo
py -3 tools/doctor.py
py -3 tools/lint.py
py -3 tools/eod.py
```

Expected: setup reports created files and a clean lint result. Doctor/lint must be read for warnings and failures, not merely checked for output. A non-empty target is refused; choose a new name, do not delete existing work or add a force flag. These commands reflect the current script interface; the macOS/Windows paths still require native validation.

For the complete capture-to-delivery example, intake interview, boundary gates and removal instructions, see [INSTALL.md](INSTALL.md), [INTAKE.md](INTAKE.md), [DESIGN-STATUS.md](DESIGN-STATUS.md) and [KNOWN-GAPS.md](KNOWN-GAPS.md). Keep those files beside this README in the release.

## Human or assistant setup

You can ask an assistant:

> Read README.md, INSTALL.md and KNOWN-GAPS.md from this downloaded kit. Identify my OS and Python version. Explain what setup will write and propose a new, non-synced target before running it. Use only synthetic example data first. Run the documented tests, doctor and lint; show failures and skipped checks. Do not move my files, change permissions, install software, enable sync or ingest real client/private data without asking me. Do not claim that folder rules isolate data from other tools.

This is a setup brief, not evidence that every assistant follows these files correctly.

## Important limits

- Folder rules and scoped search are not OS access control. Other tools may still read/write files directly.
- Secret detection is pattern-based and can miss secrets. Do not use it as a vault or a security guarantee.
- Concurrent users/processes, sync tools and real client workflows have not been proven.
- Capture is text-only. There is no automatic backup, version history or upgrade/migration path.
- A file existing proves only that a file exists, not that its content is good. Review the output before accepting or delivering it.
- `capture.py close --check-cmd` executes the specified program with your permissions. Read any proposed command before approving it.
- Uninstall is manifest/hash-based cleanup, not a backup restore. Read its preview and preservation limits before removal; do not opt into removing modified files casually.

## Licence and help

MIT licence, copyright George John. See [LICENSE](LICENSE). This is an unsupported pilot: no support, response time or security-reporting channel is promised. Questions and problems can be raised as GitHub issues on this repository. Never paste private files or secrets into an issue.

## Before this becomes a release

Native macOS and Windows results (see the Actions tab for the automated runs), a manual first run on a real Mac and Windows machine, and an extracted-archive check of the first-run steps. No release or ready-for-production claim is made until then.
