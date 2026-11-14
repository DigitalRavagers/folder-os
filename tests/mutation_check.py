#!/usr/bin/env python3
"""Targeted mutation check for the acceptance-contract guards.

  python3 tests/mutation_check.py [--scratch-base FOLDER]

It answers one narrow question: if a specific guard is removed, do the tests
that are meant to protect it fail? It works only on disposable copies of the
kit. The real files are hashed before and after and must be identical.

For each mutant below, one exact piece of code is replaced in a fresh copy and
that copy's own tests/test_kit.py is run.
  KILLED    every intended test failed (the tests caught the defect)
  SURVIVED  the suite still passed (the tests missed the defect)
  INVALID   the mutant could not be applied, did not compile, or the run broke
            in a way that says nothing about the intended tests
This is a handful of hand-picked mutants. It is not mutation coverage and makes
no claim about any guard that is not listed here.
Exit code 0 only when the control run passes, every mutant is KILLED and the
real files are unchanged. Standard library only.
"""
import sys
sys.dont_write_bytecode = True
import argparse
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
SKIP = shutil.ignore_patterns(".git", "__pycache__")

# name, file, exact code to replace (must occur once), replacement, intended tests
MUTANTS = [
    ("M1 criterion-failure guard: a contract always passes",
     "scripts/contract.py",
     '{"ok": all(met for _, _, met in results), "results": results,',
     '{"ok": True, "results": results,',
     ["64", "66", "69"]),
    ("M2 staleness guard: artifact hash is no longer compared",
     "scripts/contract.py",
     'if c.sha256_bytes(data) != meta.get("artifact_sha256"):',
     'if False:',
     ["68", "69"]),
    ("M3 staleness guard: contract hash is no longer compared",
     "scripts/contract.py",
     'if contract_hash != meta.get("contract_sha256"):',
     'if False:',
     ["67"]),
    ("M4 bypass guard: legacy checks may close a work order that has a contract",
     "scripts/capture.py",
     '    if k.exists(order):\n        return False, ("this work order has an acceptance contract',
     '    if False:\n        return False, ("this work order has an acceptance contract',
     ["65"]),
    ("M5 staleness is computed but mark no longer refuses on it",
     "scripts/capture.py",
     'reason = k.stale(order, meta) if a.status in ("accepted", "delivered") else None',
     'reason = None',
     ["67", "68", "69"]),
]


def digest(base):
    out = {}
    for folder, dirs, names in os.walk(base):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
        for name in names:
            path = Path(folder) / name
            out[path.relative_to(base).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def run_suite(copy, scratch):
    """Return (exit code, set of failed test numbers, whether a RESULT line was printed)."""
    done = subprocess.run([sys.executable, str(copy / "tests" / "test_kit.py"),
                           "--scratch-base", str(scratch)], capture_output=True, text=True)
    failed = set(re.findall(r"^FAIL (\w+) ", done.stdout, re.M))
    return done.returncode, failed, "RESULT:" in done.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scratch-base")
    args = parser.parse_args()
    before = digest(KIT)
    work = Path(tempfile.mkdtemp(prefix="pofs-mutation-", dir=args.scratch_base)).resolve()
    os.chmod(work, 0o755)
    print("Disposable copies in: %s" % work)
    counts = {"KILLED": 0, "SURVIVED": 0, "INVALID": 0}
    try:
        control = work / "control"
        shutil.copytree(KIT, control, ignore=SKIP)
        code, failed, finished = run_suite(control, work)
        print("CONTROL  unmodified copy: exit %d, failed tests: %s"
              % (code, sorted(failed) or "none"))
        if code != 0 or not finished:
            print("The unmodified copy does not pass, so no mutant result would mean anything.")
            return 1
        for number, (name, target, old, new, intended) in enumerate(MUTANTS, 1):
            copy = work / ("mutant%d" % number)
            shutil.copytree(KIT, copy, ignore=SKIP)
            source = (copy / target).read_text(encoding="utf-8")
            verdict, note = "INVALID", ""
            if source.count(old) != 1:
                note = "target code found %d times in %s, expected once" % (source.count(old), target)
            else:
                (copy / target).write_text(source.replace(old, new), encoding="utf-8")
                try:
                    compile(source.replace(old, new), target, "exec")
                except SyntaxError:
                    note = "mutant does not compile"
                else:
                    code, failed, finished = run_suite(copy, work)
                    missed = sorted(set(intended) - failed)
                    extra = sorted(failed - set(intended))
                    note = "exit %d, failed tests: %s" % (code, sorted(failed) or "none")
                    if not finished:
                        note += " (suite did not finish)"
                    elif code == 0 and not failed:
                        verdict = "SURVIVED"
                    elif not missed:
                        verdict = "KILLED"
                        note += "; also failed, not intended: %s" % extra if extra else ""
                    else:
                        note += "; intended tests that did NOT fail: %s" % missed
            counts[verdict] += 1
            print("%-8s %s\n         intended tests: %s; %s" % (verdict, name, intended, note))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    untouched = digest(KIT) == before
    print("Real kit files unchanged: %s (%d files hashed before and after)"
          % ("yes" if untouched else "NO", len(before)))
    print("MUTATION RESULT: %d mutants: %d killed, %d survived, %d invalid"
          % (len(MUTANTS), counts["KILLED"], counts["SURVIVED"], counts["INVALID"]))
    return 0 if untouched and counts["KILLED"] == len(MUTANTS) else 1


if __name__ == "__main__":
    sys.exit(main())
