#!/usr/bin/env python3
"""End-to-end test of the kit on SYNTHETIC data in a scratch folder.

  python3 tests/test_kit.py [--scratch-base FOLDER] [--keep]

It builds a fake home folder with ordinary files and fake "canary" secrets,
installs the system next to them, uses it, breaks it on purpose, and rolls it
back. Each line of output is PASS, FAIL or SKIP. Exit code 1 if anything fails.
All secrets in this file are invented canaries. Standard library only.
"""
import sys
sys.dont_write_bytecode = True
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
SCRIPTS = KIT / "scripts"
CANARIES = {
    "api key": "sk-CANARY7f3a9b2c4d5e6f708192",
    "cloud key": "AKIACANARY0000000001",
    "passphrase": "hunter2-CANARY-passphrase",
    "card": "4000 1234 5678 9010",
}
RESULTS = []
TRANSCRIPT = []  # every byte the kit printed, scanned for canaries at the end


def record(status, name, detail=""):
    RESULTS.append(status)
    print("%-4s %s%s" % (status, name, (" :: " + detail) if detail else ""), flush=True)


def check(name, condition, detail=""):
    record("PASS" if condition else "FAIL", name, "" if condition else detail)
    return condition


def run(script, *args, stdin=None, env=None, **kwargs):
    full_env = dict(os.environ)
    full_env.pop("POFS_SESSION_ID", None)
    full_env.update(env or {})
    result = subprocess.run([sys.executable, str(script)] + [str(a) for a in args],
                            input=stdin, capture_output=True, text=True, env=full_env, **kwargs)
    TRANSCRIPT.append(result.stdout + result.stderr)
    return result


def snapshot(base, exclude=None):
    """Every file under base as {path: (sha256, mtime_ns)}, plus the set of folders."""
    files, folders = {}, set()
    for folder, dirs, names in os.walk(base):
        if exclude and Path(folder) == exclude:
            dirs[:] = []
            continue
        folders.add(os.path.relpath(folder, base))
        for name in names:
            path = Path(folder) / name
            files[os.path.relpath(path, base)] = (
                hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
    return files, folders


def tree_text(base):
    chunks = []
    for folder, _, names in os.walk(base):
        for name in names:
            chunks.append(name)
            chunks.append((Path(folder) / name).read_bytes().decode("utf-8", "replace"))
    return "\n".join(chunks)


def edit(path, old, new):
    text = path.read_text(encoding="utf-8")
    assert old in text, "test bug: %r not in %s" % (old, path)
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def answers(**extra):
    data = {
        "format_version": 1, "owner_name": "Synthetic Pilot",
        "work_summary": "Synthetic client work and training.",
        "weekly_task": "Know the next step for every project.",
        "arrival_points": ["email", "voice notes"],
        "clients": [{"name": "Client Alpha", "projects": ["Website Refresh"]},
                    {"name": "Client Beta", "projects": ["Workshop Series"]}],
        "content_business": True, "review_gates": ["Before anything is sent"],
        "voice_rules": ["Plain words"], "failure_definition": "No next step written.",
        "keep_out": [], "modules": {"money": False}, "include_synthetic_example": True,
    }
    data.update(extra)
    return json.dumps(data, indent=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scratch-base")
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()
    scratch = Path(tempfile.mkdtemp(prefix="pofs-test-", dir=args.scratch_base)).resolve()
    os.chmod(scratch, 0o755)
    print("Scratch folder: %s" % scratch)
    print("Platform: %s, Python %s\n" % (sys.platform, sys.version.split()[0]))

    # ---- A synthetic "home" with ordinary files and canary secrets -------------------
    home = scratch / "fake home"
    for name, data in {
        "Documents/notes.txt": b"ordinary notes\n",
        "Documents/draft.bin": bytes(range(256)) * 8,
        "private/journal.md": b"private journal canary line\n",
        "private/keys.env": ("API=%s\nCLOUD=%s\npassword: %s\n" % (
            CANARIES["api key"], CANARIES["cloud key"], CANARIES["passphrase"])).encode(),
        "private/bank.csv": ("card,%s\n" % CANARIES["card"]).encode(),
    }.items():
        (home / name).parent.mkdir(parents=True, exist_ok=True)
        (home / name).write_bytes(data)
    (home / "answers.json").write_text(answers(), encoding="utf-8")
    target = home / "work system"  # a space in the path, on purpose
    tools = target / "tools"
    before_home = snapshot(home)
    before_kit = snapshot(KIT)

    # ---- 1. Install ------------------------------------------------------------------
    r = run(SCRIPTS / "setup.py", "--answers", home / "answers.json", "--target", target)
    check("01 install into a new folder (path with a space) exits 0",
          r.returncode == 0, r.stdout + r.stderr)
    manifest = json.loads((target / ".install/install.json").read_text())
    on_disk = set(snapshot(target)[0]) - {os.path.join(".install", "install.json")}
    check("02 install record lists exactly the files on disk",
          on_disk == {n.replace("/", os.sep) for n in manifest["files"]})
    missing = [str(d) for d, _, names in os.walk(target)
               if Path(d) != target and Path(d).name != ".install" and "context.md" not in names]
    check("03 every folder has a context.md contract", not missing, str(missing))
    check("04 CLAUDE.md and AGENTS.md are byte-identical",
          (target / "CLAUDE.md").read_bytes() == (target / "AGENTS.md").read_bytes())
    check("05 money module is off by default (no 6-money folder)",
          not (target / "6-money").exists())
    check("06 nothing outside the new tree was touched by install",
          snapshot(home, exclude=target) == before_home and snapshot(KIT) == before_kit)

    # ---- 2. Refusals -----------------------------------------------------------------
    r = run(SCRIPTS / "setup.py", "--answers", home / "answers.json", "--target", target)
    check("07 installer refuses its own already-installed tree", r.returncode != 0)
    busy = home / "Documents"
    r = run(SCRIPTS / "setup.py", "--answers", home / "answers.json", "--target", busy)
    check("08 installer refuses a non-empty target and changes nothing",
          r.returncode != 0 and "not empty" in r.stderr
          and snapshot(home, exclude=target) == before_home)
    r = run(SCRIPTS / "setup.py", "--answers", home / "answers.json", "--target", busy, "--force")
    check("09 there is no --force option", r.returncode == 2
          and snapshot(home, exclude=target) == before_home)
    if hasattr(os, "symlink"):
        link = scratch / "link-target"
        os.symlink(home / "Documents", link)
        r = run(SCRIPTS / "setup.py", "--answers", home / "answers.json", "--target", link)
        check("10 installer refuses a target that is a link", r.returncode != 0)
        link.unlink()
    else:
        record("SKIP", "10 installer refuses a target that is a link", "no symlink support")
    bad = scratch / "bad-answers.json"
    bad.write_text(answers(work_summary="my api_key = " + CANARIES["api key"]), encoding="utf-8")
    r = run(SCRIPTS / "setup.py", "--answers", bad, "--target", scratch / "never")
    check("11 installer refuses an answers file holding a secret, creates nothing",
          r.returncode != 0 and not (scratch / "never").exists())

    # ---- 3. Lint ---------------------------------------------------------------------
    lint = tools / "lint.py"
    check("12 lint passes on a fresh install (exit 0)", run(lint).returncode == 0)
    current = target / "1-clients/client-alpha/website-refresh/CURRENT.md"

    def lint_fails(name, break_it, mend_it, code=1):
        break_it()
        broken = run(lint).returncode
        mend_it()
        mended = run(lint).returncode
        check(name, broken == code and mended == 0,
              "exit %d when broken (wanted %d), %d when mended" % (broken, code, mended))

    original = current.read_text(encoding="utf-8")
    restore = lambda: current.write_text(original, encoding="utf-8")
    lint_fails("13 lint exits 1 when a required frontmatter field is missing",
               lambda: edit(current, "next_step: Write the first real next step for this project\n", ""),
               restore)
    lint_fails("14 lint exits 1 on a status that is not in the taxonomy",
               lambda: edit(current, "status: setup", "status: nearly-done"), restore)
    lint_fails("15 lint exits 1 when a file has no frontmatter at all",
               lambda: current.write_text("just some text\n", encoding="utf-8"), restore)
    stray = target / "1-clients/client-alpha/new-folder"
    lint_fails("16 lint exits 1 when a folder has no context.md",
               stray.mkdir, stray.rmdir)
    foreign = target / "0-inbox/dropped-by-another-tool.md"
    lint_fails("17 lint exits 1 when anything but the declared writer puts a file in the inbox",
               lambda: foreign.write_text("---\ntitle: x\n---\nhello\n", encoding="utf-8"),
               foreign.unlink)
    agents = (target / "AGENTS.md").read_bytes()
    lint_fails("18 lint exits 1 when CLAUDE.md and AGENTS.md disagree",
               lambda: (target / "AGENTS.md").write_bytes(agents + b"\nextra rule\n"),
               lambda: (target / "AGENTS.md").write_bytes(agents))
    stub = target / "skills/pointer.md"
    lint_fails("19 lint exits 1 on a pointer stub standing in for real content",
               lambda: stub.write_text("../../somewhere/else/skill.md", encoding="utf-8"),
               stub.unlink)
    registry = (target / "routing/registry.json").read_bytes()
    lint_fails("20 lint exits 2 (cannot run) when registry.json is unreadable",
               lambda: (target / "routing/registry.json").write_bytes(b"{ not json"),
               lambda: (target / "routing/registry.json").write_bytes(registry), code=2)

    # ---- 4. Capture: one writer, idempotent ------------------------------------------
    capture = tools / "capture.py"
    text = "Alpha asked for a new homepage headline, ZEBRAFINCH wording"
    first = run(capture, "add", "--text", text, "--source", "email")
    again = run(capture, "add", "--text", "  Alpha asked for a new homepage   headline, ZEBRAFINCH wording\n")
    piped = run(capture, "add", "--stdin", stdin=text)
    items = sorted((target / "0-inbox").glob("*_c*.md"))
    check("21 the same text captured three times makes exactly one inbox item",
          len(items) == 1 and first.returncode == again.returncode == piped.returncode == 0
          and "Nothing added" in again.stdout, "%d item(s)" % len(items))
    item = items[0].stem.split("_")[1]
    kinds = [json.loads(p.read_text())["outcome"]
             for p in sorted((target / "logs/receipts").glob("*_capture.json"))]
    check("22 receipts show one capture and two skipped duplicates",
          sorted(kinds) == ["captured", "duplicate-skipped", "duplicate-skipped"], str(kinds))

    # ---- 5. Filed is not implemented --------------------------------------------------
    r = run(capture, "route", "--id", item[:8], "--client", "Client Alpha",
            "--project", "Website Refresh", "--next", "Draft three headlines", "--done-when", " ")
    failures = sorted((target / "logs/receipts").glob("*_failure.json"))
    check("23 route refuses without a done-when, and the refusal is recorded as a failure",
          r.returncode == 1 and len(failures) == 1 and items[0].exists()
          and set(json.loads(failures[0].read_text())["details"])
          >= {"meant", "failed", "cause", "recovery"})
    r = run(capture, "route", "--id", item[:8], "--client", "Client Alpha",
            "--project", "Website Refresh", "--next", "Draft three headlines",
            "--done-when", "deliverables/headlines_draft_three-options.md exists and is not empty")
    work_id = "WO-" + item[:8]
    order = target / "1-clients/client-alpha/website-refresh/work-orders" / (work_id + ".md")
    check("24 route creates a work order with next step and done-when; item leaves the inbox",
          r.returncode == 0 and order.is_file() and not items[0].exists()
          and (target / "0-inbox/_routed" / items[0].name).is_file()
          and "done_when: deliverables/headlines" in order.read_text()
          and run(lint).returncode == 0, r.stdout + r.stderr)
    r = run(capture, "add", "--text", text)
    check("25 re-capturing an already routed item still adds nothing",
          "Nothing added" in r.stdout and not list((target / "0-inbox").glob("*_c*.md")))

    # ---- 6. Verification doctrine ----------------------------------------------------
    evidence = "1-clients/client-alpha/website-refresh/deliverables/headlines_draft_three-options.md"
    r = run(capture, "close", "--work-id", work_id)
    check("26 close with no evidence check at all is refused", r.returncode == 2
          and "status: open" in order.read_text())
    r = run(capture, "close", "--work-id", work_id, "--check-file", evidence)
    failures = sorted((target / "logs/receipts").glob("*_failure.json"))
    check("27 close fails when the evidence file is missing; work order stays open; failure recorded",
          r.returncode == 1 and "status: open" in order.read_text() and len(failures) == 2)
    r = run(capture, "mark", "--work-id", work_id, "--status", "delivered", "--by", "Tester")
    check("28 an unverified work order cannot be marked delivered", r.returncode == 1
          and "status: open" in order.read_text())
    (target / evidence).write_text(
        "---\ntitle: Headlines\ntype: note\nstatus: active\ncreated: 2026-01-01\n---\nOne. Two. Three.\n",
        encoding="utf-8")
    r = run(capture, "close", "--work-id", work_id, "--check-file", evidence)
    check("29 close succeeds on real file evidence and records its hash",
          r.returncode == 0 and "status: verified" in order.read_text()
          and "sha256" in order.read_text(), r.stdout + r.stderr)
    r1 = run(capture, "mark", "--work-id", work_id, "--status", "accepted", "--by", "Tester")
    r2 = run(capture, "mark", "--work-id", work_id, "--status", "delivered", "--by", "Tester")
    check("30 verified, then accepted by a person, then delivered, in that order only",
          r1.returncode == 0 and r2.returncode == 0 and "status: delivered" in order.read_text())
    run(capture, "add", "--text", "Second synthetic task for a command check")
    second = sorted((target / "0-inbox").glob("*_c*.md"))[0].stem.split("_")[1][:8]
    run(capture, "route", "--id", second, "--content", "--next", "Run lint",
        "--done-when", "lint exits 0")
    r_bad = run(capture, "close", "--work-id", "WO-" + second, "--check-cmd",
                '"%s" -c "raise SystemExit(3)"' % sys.executable)
    r_ok = run(capture, "close", "--work-id", "WO-" + second, "--check-cmd",
               '"%s" tools/lint.py' % sys.executable)
    check("31 command evidence: a failing command does not close, a passing one does",
          r_bad.returncode == 1 and r_ok.returncode == 0, r_ok.stdout + r_ok.stderr)
    run(capture, "add", "--text", "Third synthetic task for evidence-scope checks")
    third = sorted((target / "0-inbox").glob("*_c*.md"))[0].stem.split("_")[1][:8]
    run(capture, "route", "--id", third, "--client", "Client Alpha", "--project", "Website Refresh",
        "--next", "Check evidence scope", "--done-when", "a deliverable file exists")
    third_order = "1-clients/client-alpha/website-refresh/work-orders/WO-%s.md" % third
    r_self = run(capture, "close", "--work-id", "WO-" + third, "--check-file", third_order)
    r_out = run(capture, "close", "--work-id", "WO-" + third, "--check-file", "BOOT.md")
    check("61 evidence file cannot be the work order itself or a file outside its project folder",
          r_self.returncode == 1 and r_out.returncode == 1
          and "status: open" in (target / third_order).read_text(),
          r_self.stdout + r_self.stderr + r_out.stdout + r_out.stderr)
    r = run(capture, "fail", "--meant", "send the weekly summary", "--failed", "export step crashed",
            "--recovery", "did-not-work")
    last = json.loads(sorted((target / "logs/receipts").glob("*_failure.json"),
                             key=lambda p: p.stat().st_mtime_ns)[-1].read_text())
    check("32 a manual failure record keeps meant, failed, cause (unknown) and recovery",
          r.returncode == 0 and last["details"]["cause"] == "unknown"
          and last["details"]["recovery"] == "did-not-work")

    # ---- 7. Secrets ------------------------------------------------------------------
    codes = [run(capture, "add", "--text", "note to self: " + CANARIES["api key"]).returncode,
             run(capture, "add", "--text", "key " + CANARIES["cloud key"]).returncode,
             run(capture, "add", "--text", "password: " + CANARIES["passphrase"]).returncode,
             run(capture, "add", "--stdin", stdin="card " + CANARIES["card"]).returncode,
             run(capture, "change", "--what", "x", "--why", "token=" + CANARIES["api key"]).returncode]
    check("33 capture refuses secret-looking text (exit 3) in every input path",
          codes == [3, 3, 3, 3, 3], str(codes))
    check("34 lint still passes after all of the above", run(lint).returncode == 0)

    # ---- 8. Receipts: names and collisions -------------------------------------------
    pattern = re.compile(json.loads((target / "routing/registry.json").read_text())
                         ["naming"]["receipt"]["pattern"])
    for n in range(25):
        run(capture, "add", "--text", "burst item number %d" % n, env={"POFS_SESSION_ID": "burst01"})
    names = [p.name for p in (target / "logs/receipts").glob("*.json")]
    burst = [n for n in names if "_burst01_" in n]
    check("35 every receipt name has date, time with seconds, timezone and session id",
          all(pattern.match(n) for n in names), str([n for n in names if not pattern.match(n)][:3]))
    check("36 25 rapid captures under one session id give 25 distinct receipts",
          len(burst) == 25 and len(set(burst)) == 25, "%d receipts" % len(burst))

    # ---- 9. Scoped search ------------------------------------------------------------
    search = tools / "search.py"
    (target / "1-clients/client-beta/workshop-series/assets/brief.md").write_text(
        "---\ntitle: Beta brief\ntype: brief\nstatus: draft\ncreated: 2026-01-01\n---\nOKAPI confidential plan\n",
        encoding="utf-8")
    a_own = run(search, "--client", "Client Alpha", "zebrafinch")
    a_other = run(search, "--client", "Client Alpha", "okapi")
    b_own = run(search, "--client", "client-beta", "okapi")
    b_other = run(search, "--client", "client-beta", "zebrafinch")
    check("37 search finds a client's own material", "ZEBRAFINCH" in a_own.stdout
          and "OKAPI" in b_own.stdout)
    check("38 search under one client never returns the other client's material",
          "OKAPI" not in a_other.stdout and "ZEBRAFINCH" not in b_other.stdout
          and "0 match" in a_other.stdout and "0 match" in b_other.stdout)
    check("39 search refuses to run without a scope", run(search, "okapi").returncode == 2)

    # ---- 10. Doctor ------------------------------------------------------------------
    doctor = tools / "doctor.py"
    r = run(doctor)
    check("40 doctor exits 0 on a healthy system", r.returncode == 0, r.stdout)
    r = run(doctor, env={"PATH": ""})
    check("41 a missing optional tool is reported with a fix and does not break doctor",
          r.returncode == 0 and "MISSING-OPTIONAL" in r.stdout and "fix:" in r.stdout, r.stdout)
    planted = target / "skills/oops.md"
    planted.write_text("---\ntitle: oops\ntype: note\nstatus: active\ncreated: 2026-01-01\n---\n"
                       "api_key = %s\n" % CANARIES["api key"], encoding="utf-8")
    r = run(doctor)
    check("42 doctor exits 1 on a secret planted in the tree, names the file, does not print it",
          r.returncode == 1 and "skills/oops.md" in r.stdout
          and CANARIES["api key"] not in r.stdout)
    planted.unlink()
    if hasattr(os, "symlink"):
        link = target / "skills/linked"
        os.symlink(home / "private", link)
        r = run(doctor)
        leaked = run(search, "--shared-only", "journal canary")
        check("43 doctor and lint both fail on a link inside the tree; search does not follow it",
              r.returncode == 1 and run(lint).returncode == 1 and "0 match" in leaked.stdout)
        link.unlink()
    else:
        record("SKIP", "43 link inside the tree", "no symlink support")

    # ---- 11. Boundary canary (real access control, not a label) ----------------------
    r = run(doctor, "--boundary-canary", home / "private")
    check("44 boundary canary reports OPEN (exit 1) for a private folder this process can read",
          r.returncode == 1 and "BOUNDARY OPEN" in r.stdout)
    locked = home / "private"
    name45 = "45 boundary canary reports BLOCKED once the OS denies access"
    if os.name != "posix":
        record("SKIP", name45, "permission test written for POSIX only")
    else:
        os.chmod(locked, 0o700)
        drop = {}
        if os.geteuid() == 0:
            # root ignores permissions, so run the check as the unprivileged user "nobody"
            import pwd
            try:
                nobody = pwd.getpwnam("nobody")
                drop = {"user": nobody.pw_uid, "group": nobody.pw_gid, "extra_groups": []}
            except KeyError:
                drop = None
        else:
            os.chmod(locked, 0o000)
        if drop is None:
            record("SKIP", name45, "running as root and no 'nobody' user to drop to")
        else:
            try:
                control = run(doctor, "--boundary-canary", home / "Documents", **drop)
                r = run(doctor, "--boundary-canary", locked, **drop)
                if "BOUNDARY OPEN" not in control.stdout:
                    record("SKIP", name45, "control folder not readable after dropping privileges")
                else:
                    check(name45, "BOUNDARY BLOCKED" in r.stdout and "BOUNDARY OPEN" not in r.stdout,
                          r.stdout + r.stderr)
            except (OSError, subprocess.SubprocessError, TypeError) as error:
                record("SKIP", name45, "could not drop privileges: %s" % type(error).__name__)
        os.chmod(locked, 0o755)

    # ---- 12. End-of-day view ---------------------------------------------------------
    run(capture, "next", "--client", "client-alpha", "--project", "website-refresh",
        "--next", "Send the three headlines for review", "--done-when", "client reply is captured")
    before_eod = snapshot(target)
    r = run(tools / "eod.py")
    check("45b end-of-day view shows next steps and failures and changes nothing",
          r.returncode == 0 and "Send the three headlines for review" in r.stdout
          and "FAILURES TODAY: " in r.stdout and "FAILURES TODAY: 0" not in r.stdout
          and snapshot(target) == before_eod, r.stdout[-400:])

    # ---- 13. No secrets anywhere the kit wrote or printed ----------------------------
    written = tree_text(target)
    printed = "\n".join(TRANSCRIPT)
    leaks = [name for name, value in CANARIES.items() if value in written or value in printed]
    check("46 no canary secret appears in any file of the tree, any receipt, or any output",
          not leaks, "leaked: %s" % leaks)

    # ---- 14. Rollback after real use -------------------------------------------------
    mine = target / "1-clients/client-alpha/website-refresh/assets/my-own-file.bin"
    mine.write_bytes(b"\x00user data\xff" * 100)
    mine_hash = hashlib.sha256(mine.read_bytes()).hexdigest()
    uninstall = tools / "uninstall.py"
    before_dry = snapshot(target)
    r = run(uninstall)
    check("47 uninstall without --yes is a dry run that changes nothing",
          r.returncode == 0 and snapshot(target) == before_dry)
    untouched = [n for n, h in manifest["files"].items()
                 if hashlib.sha256((target / n).read_bytes()).hexdigest() == h]
    changed = [n for n in manifest["files"] if n not in untouched]
    not_installer = set(before_dry[0]) - {n.replace("/", os.sep) for n in manifest["files"]} \
        - {os.path.join(".install", "install.json")}
    r = run(uninstall, "--yes", cwd=str(scratch))
    after = snapshot(target)[0] if target.exists() else {}
    check("48 uninstall --yes removes every unchanged installer file",
          r.returncode == 0 and not [n for n in untouched if (target / n).exists()], r.stdout + r.stderr)
    check("49 uninstall keeps the user's own file byte-identical, plus edited files and receipts",
          mine.exists() and hashlib.sha256(mine.read_bytes()).hexdigest() == mine_hash
          and all((target / n).exists() for n in changed)
          and all(after.get(n) == before_dry[0][n] for n in not_installer),
          "changed=%s" % changed)
    check("50 after use and rollback, everything outside the tree is byte-identical to the start",
          snapshot(home, exclude=target) == before_home and snapshot(KIT) == before_kit)

    # ---- 15. Clean rollback: install then uninstall straight away --------------------
    clean = home / "second system"
    run(SCRIPTS / "setup.py", "--answers", home / "answers.json", "--target", clean)
    r = run(clean / "tools/uninstall.py", "--yes", cwd=str(scratch))
    shutil.rmtree(target)
    check("51 install then immediate uninstall leaves no trace: the home folder is byte-identical",
          not clean.exists() and snapshot(home) == before_home, r.stdout + r.stderr)
    empty = home / "empty already here"
    empty.mkdir()
    run(SCRIPTS / "setup.py", "--answers", home / "answers.json", "--target", empty)
    installed = (empty / "tools/uninstall.py").is_file()
    run(empty / "tools/uninstall.py", "--yes", cwd=str(scratch))
    check("52 an empty folder that existed before install is accepted, and is left in place, empty",
          installed and empty.is_dir() and not os.listdir(empty))
    empty.rmdir()

    # ---- 16. Options and the interview -----------------------------------------------
    opt = scratch / "optional"
    (scratch / "money.json").write_text(
        answers(modules={"money": True}, content_business=False, clients=[]), encoding="utf-8")
    r = run(SCRIPTS / "setup.py", "--answers", scratch / "money.json", "--target", opt)
    check("53 optional money module appears only when switched on; content room can be off; lint passes",
          r.returncode == 0 and (opt / "6-money/context.md").is_file()
          and not (opt / "2-content").exists() and run(opt / "tools/lint.py").returncode == 0)
    r = run(opt / "tools/capture.py", "new-project", "--client", "New Client", "--project", "Kickoff")
    r2 = run(opt / "tools/capture.py", "new-project", "--client", "New Client", "--project", "Kickoff")
    check("54 new-project adds a client project that passes lint, and refuses to redo it",
          r.returncode == 0 and r2.returncode != 0
          and (opt / "1-clients/new-client/kickoff/CURRENT.md").is_file()
          and run(opt / "tools/lint.py").returncode == 0, r.stdout + r.stderr)
    typed = "\n".join([
        "Interview Person", "Synthetic work", "Weekly review", "email, calls",
        "Client Gamma", "Launch Plan", "",            # one client, then no more
        "y", "Before sending", "Plain words", "No next step",
        "password: " + CANARIES["passphrase"],       # a secret typed by mistake at question 10
        "client secrets I was told not to store",     # the retry
        "n", "not sure", "not sure", "nothing"]) + "\n"
    out = scratch / "interview.json"
    r = run(SCRIPTS / "intake.py", "--out", out, stdin=typed)
    r2 = run(SCRIPTS / "setup.py", "--answers", out, "--target", scratch / "from interview")
    r3 = run(SCRIPTS / "intake.py", "--out", out, stdin=typed)
    check("55 the interview writes an answers file the installer accepts, drops a typed secret, never overwrites",
          r.returncode == 0 and r2.returncode == 0 and r3.returncode != 0
          and CANARIES["passphrase"] not in out.read_text()
          and (scratch / "from interview/1-clients/client-gamma/launch-plan/CURRENT.md").is_file(),
          r.stdout[-300:] + r.stderr + r2.stderr)

    # ---- 16b. A tampered install record cannot make uninstall touch anything outside --
    tamper = scratch / "tamper-home"
    tamper.mkdir()
    outside = tamper / "outside-empty-folder"
    outside.mkdir()
    tree = tamper / "system"
    rs = run(SCRIPTS / "setup.py", "--answers", KIT / "intake-answers.example.json", "--target", tree)
    install_json = tree / ".install" / "install.json"
    data = json.loads(install_json.read_text())
    data["dirs"] = list(data["dirs"]) + ["../outside-empty-folder", ".."]
    data["files"]["../outside-file.txt"] = "0" * 64
    (tamper / "outside-file.txt").write_text("keep me", encoding="utf-8")
    install_json.write_text(json.dumps(data), encoding="utf-8")
    ru = run(tree / "tools" / "uninstall.py", "--yes")
    check("62 uninstall with a tampered install record never removes anything outside the system folder",
          rs.returncode == 0 and ru.returncode == 0 and outside.is_dir()
          and (tamper / "outside-file.txt").read_text() == "keep me",
          rs.stdout[-200:] + rs.stderr + ru.stdout + ru.stderr)

    # ---- 17. The kit's own text ------------------------------------------------------
    sys.path.insert(0, str(SCRIPTS))
    import common
    dashes, secrets = [], []
    for folder, dirs, names in os.walk(KIT):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        for name in names:
            path = Path(folder) / name
            body = path.read_text(encoding="utf-8")
            if chr(0x2014) in body or chr(0x2013) in body:
                dashes.append(name)
            if path.parent.name != "tests" and common.find_secret(body):
                secrets.append(name)
    check("56 no em dashes or en dashes anywhere in the kit text", not dashes, str(dashes))
    check("57 no secret-like text in the kit files (tests hold only the fake canaries)",
          not secrets, str(secrets))
    check("58 the kit folder itself is unchanged by the whole test run", snapshot(KIT) == before_kit)
    leaks = [name for name, value in CANARIES.items() if value in "\n".join(TRANSCRIPT)]
    check("59 no canary secret in anything printed during the whole run", not leaks, str(leaks))

    if not args.keep:
        shutil.rmtree(scratch)
    counts = {s: RESULTS.count(s) for s in ("PASS", "FAIL", "SKIP")}
    print("\nRESULT: %(PASS)d passed, %(FAIL)d failed, %(SKIP)d skipped" % counts)
    sys.exit(1 if counts["FAIL"] else 0)


if __name__ == "__main__":
    main()
