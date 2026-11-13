# FolderOS candidate review record

Product / version: FolderOS 0.1.0-pilot (public pilot source, no install-ready release)
Repository / visibility: public, pilot. Approved by the owner on 13 Nov 2026.
Payload allowlist: README.md, INSTALL.md, INTAKE.md, DESIGN-STATUS.md, KNOWN-GAPS.md, RELEASE-REVIEW.md, intake-answers.example.json, scripts/, tests/, LICENSE, .github/workflows/test.yml. Nothing else.
Exclusions: skills, vault material, personas, voice samples, named-person intake, any account data.
Rights evidence and licence: MIT, copyright George John, approved by the owner on 13 Nov 2026. Original code written by an AI assistant for the owner; third-party content: none identified (stdlib only).
First-run result (Linux, Python 3.10, archive extracted into a path with spaces): README first-run commands ran as written. Setup created 48 files, doctor 11 checks 0 broken, lint 0 errors 0 warnings, eod ran, second setup into the same target refused (exit 2). Run by the reviewer, 13 Nov 2026.
Linux automated: 62 passed, 0 failed, 0 skipped (Python 3.10, independent). Author: 60 (Python 3.13).
macOS automated: 62 passed on Python 3.10 and 3.13. Manual: pending.
Windows automated: 61 passed, 1 skipped (POSIX-only test 45) on Python 3.10 and 3.13. Manual: pending.
Skipped checks and known limits: KNOWN-GAPS.md.
Help / maintenance owner: not assigned.
Approval needed: a release or install-ready claim still needs manual first runs, an extracted-archive check and owner approval.

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
