#!/usr/bin/env python3
"""Capture, route, verify and record. The ONLY allowed writer for the inbox.

  add          put one piece of text in the inbox (same text twice = one item)
  route        turn an inbox item into a work order (needs next step + done-when)
  discard      close an inbox item that needs no action (needs a reason)
  next         set a project's next step and done-when in its CURRENT.md
  close        verify a work order with tool evidence (a file check or a command)
  mark         move a verified work order to accepted, delivered or dropped
  fail         record a failure: meant to do, what failed, cause, recovery
  new-project  add a client project folder (additive, never overwrites)
  change       add a line to the change ledger (CHANGELOG.md)

Every command writes a receipt in logs/receipts, including when it fails.
Python 3 standard library only.
"""
import sys
sys.dont_write_bytecode = True
import argparse
from pathlib import Path
import os
import re
import shlex
import subprocess

import common as c

ROOT = None
REG = None


def rel(path):
    return path.relative_to(ROOT).as_posix()


def refuse(meant, failed, cause="unknown", code=1, **details):
    """Record a failure and stop. Messages never include the user's text."""
    path = c.receipt(ROOT, "failure", "failed", meant=meant, failed=failed,
                     cause=cause, recovery="not-tried", **details)
    print("FAILED: " + failed)
    print("Recorded in " + rel(path))
    sys.exit(code)


def done(action, outcome, message, **details):
    path = c.receipt(ROOT, action, outcome, **details)
    print(message)
    print("Receipt: " + rel(path))


def inbox():
    return ROOT / REG["inbox"]["path"]


def find_item(prefix):
    if not re.fullmatch(r"c[0-9a-f]{5,15}", prefix):
        c.die("An item id looks like c1a2b3c4 (at least 6 characters).")
    hits = sorted(inbox().glob("*_" + prefix + "*.md"))
    if len(hits) != 1:
        c.die("Found %d new inbox items starting with %s. Run tools/eod.py to list them."
              % (len(hits), prefix))
    return hits[0]


def find_work_order(work_id):
    if not re.fullmatch(r"WO-c[0-9a-f]{7}", work_id):
        c.die("A work order id looks like WO-c1a2b3c4.")
    hits = [folder / (work_id + ".md") for folder, _, files in c.walk(ROOT)
            if folder.name == "work-orders" and work_id + ".md" in files]
    if len(hits) != 1:
        c.die("Found %d work orders named %s." % (len(hits), work_id))
    return hits[0]


def room(a):
    """The folder a routed item goes to. Folder names come from routing/registry.json."""
    if a.content:
        if not REG["rooms"].get("content"):
            c.die("This system was installed without a content room.")
        folder = ROOT / REG["rooms"]["content"]
    elif a.client and a.project:
        folder = ROOT / REG["rooms"]["clients"] / c.slug(a.client) / c.slug(a.project)
    else:
        c.die("Give --client and --project, or --content.")
    if not (folder / "work-orders").is_dir() or not c.inside(ROOT, folder):
        c.die("No such room: %s. Create a project with: tools/capture.py new-project"
              % folder.name)
    return folder


def append_line(path, line):
    text = c.read_text(path)
    c.replace_text(path, text.rstrip("\n") + "\n- %s %s\n" % (c.today(), c.one_line(line)))


def cmd_add(a):
    text = sys.stdin.read() if a.stdin else (a.text or "")
    if not text.strip():
        c.die("Nothing to capture. Use --text \"...\" or --stdin.")
    hit = c.find_secret(text)
    if hit:
        refuse("capture text to the inbox", "capture refused: the text looks like it "
               "contains a secret (%s). Keep secrets outside this system." % hit,
               cause="secret-like text in input", code=3)
    if a.source not in REG["inbox"]["sources"]:
        c.die("Unknown source. Allowed: " + ", ".join(REG["inbox"]["sources"]))
    item = c.item_id(text)
    if list(inbox().rglob("*_" + item + ".md")):
        return done("capture", "duplicate-skipped",
                    "Already captured as %s. Nothing added." % item, id=item)
    path = inbox() / ("%s_%s.md" % (c.now().strftime("%Y%m%d"), item))
    meta = {"title": c.one_line(text)[:60], "type": "inbox-item", "status": "new",
            "id": item, "source": a.source, "captured": c.iso(), "created": c.today(),
            "writer": REG["inbox"]["writer"]}
    try:
        c.write_new(path, c.write_frontmatter(meta, text.strip() + "\n"))
    except FileExistsError:
        return done("capture", "duplicate-skipped", "Already captured as %s." % item, id=item)
    done("capture", "captured", "Captured %s. Route it with: tools/capture.py route --id %s"
         % (item, item[:8]), id=item, path=rel(path), source=a.source)


def cmd_route(a):
    item = find_item(a.id)
    next_step, done_when = c.one_line(a.next), c.one_line(a.done_when)
    if not next_step or not done_when:
        refuse("route inbox item " + a.id, "route refused: filing is not doing. A next "
               "step and a testable done-when are both required.",
               cause="missing next step or done-when", id=a.id)
    folder = room(a)
    meta, body = c.read_frontmatter(c.read_text(item))
    work_id = "WO-" + meta["id"][:8]
    order = folder / "work-orders" / (work_id + ".md")
    template = c.read_text(ROOT / REG["templates"] / "work-order.template.md")
    text = c.fill(template, work_id=work_id, title=meta["title"], date=c.today(),
                  room=rel(folder), source_item=meta["id"], next_step=next_step,
                  done_when=done_when, request=body.strip())
    try:
        c.write_new(order, text)
    except FileExistsError:
        refuse("route inbox item " + a.id, "route refused: %s already exists" % work_id,
               cause="work order id collision", id=a.id)
    meta.update(status="routed", routed_to=rel(order), routed=c.iso())
    c.write_new(item.parent / "_routed" / item.name, c.write_frontmatter(meta, body))
    item.unlink()
    if (folder / "CURRENT.md").is_file():
        append_line(folder / "CURRENT.md", "Routed %s to %s. Next: %s Done when: %s"
                    % (meta["id"][:8], work_id, next_step, done_when))
    done("route", "routed", "Routed to %s" % rel(order), id=meta["id"],
         work_order=rel(order))


def cmd_discard(a):
    item = find_item(a.id)
    meta, body = c.read_frontmatter(c.read_text(item))
    meta.update(status="discarded", reason=a.reason, discarded=c.iso())
    c.write_new(item.parent / "_discarded" / item.name, c.write_frontmatter(meta, body))
    item.unlink()
    done("discard", "discarded", "Discarded %s (kept in _discarded)." % meta["id"],
         id=meta["id"])


def cmd_next(a):
    current = ROOT / REG["rooms"]["clients"] / c.slug(a.client) / c.slug(a.project) / "CURRENT.md"
    if not current.is_file():
        c.die("No CURRENT.md for that client and project.")
    meta, body = c.read_frontmatter(c.read_text(current))
    meta.update(status=a.status, next_step=a.next, done_when=a.done_when, updated=c.today())
    c.replace_text(current, c.write_frontmatter(meta, body))
    append_line(current, "Next step set: %s Done when: %s" % (a.next, a.done_when))
    done("next", "updated", "Updated " + rel(current), path=rel(current), status=a.status)


def evidence(a, order):
    """Return (passed, description). Evidence comes from a check that runs now,
    never from someone typing that the work is finished.

    --check-file: the file must sit inside this work order's own project folder and
    must not be the work order itself. --check-cmd runs any program you name, with your
    own permissions, and counts exit code 0 as a pass. It proves a check ran, not that
    the check was a good one. Review the command before you let a tool run it."""
    if a.check_file:
        path = ROOT / a.check_file
        project = Path(order).resolve().parent.parent
        if not c.inside(ROOT, path) or path.is_symlink() or not c.inside(project, path):
            return False, "evidence file is not inside this work order's project folder"
        if path.resolve() == Path(order).resolve():
            return False, "the work order cannot be its own evidence"
        if not path.is_file() or path.stat().st_size == 0:
            return False, "evidence file is missing or empty"
        return True, "file %s exists, %d bytes, sha256 %s" % (
            rel(path.resolve()), path.stat().st_size, c.sha256_file(path))
    try:
        run = subprocess.run([t[1:-1] if len(t) > 1 and t[0] == t[-1] == chr(34) else t
                            for t in shlex.split(a.check_cmd, posix=(os.name != "nt"))], cwd=ROOT,
                             capture_output=True, timeout=300)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        return False, "check command could not run (%s)" % type(error).__name__
    return run.returncode == 0, "check command exit code %d, output sha256 %s" % (
        run.returncode, c.sha256_bytes(run.stdout + run.stderr))


def cmd_close(a):
    order = find_work_order(a.work_id)
    meta, body = c.read_frontmatter(c.read_text(order))
    if meta["status"] != "open":
        c.die("%s is %s, not open." % (a.work_id, meta["status"]))
    passed, description = evidence(a, order)
    if not passed:
        refuse("verify %s against its done-when" % a.work_id,
               "not closed: " + description, cause="evidence check did not pass",
               work_id=a.work_id)
    meta.update(status="verified", evidence=description, verified=c.iso())
    c.replace_text(order, c.write_frontmatter(meta, body))
    append_line(order, "VERIFIED. Evidence: " + description)
    done("close", "verified", "%s verified. A person still has to accept it: "
         "tools/capture.py mark --work-id %s --status accepted --by NAME"
         % (a.work_id, a.work_id), work_id=a.work_id, evidence=description)


def cmd_mark(a):
    order = find_work_order(a.work_id)
    meta, body = c.read_frontmatter(c.read_text(order))
    needed = {"accepted": ["verified"], "delivered": ["accepted"],
              "dropped": ["open", "verified", "accepted"]}[a.status]
    if meta["status"] not in needed:
        refuse("mark %s as %s" % (a.work_id, a.status),
               "refused: %s is %s and must be %s first"
               % (a.work_id, meta["status"], " or ".join(needed)),
               cause="state order", work_id=a.work_id)
    if a.status == "dropped" and not a.note.strip():
        c.die("Dropping a work order needs --note with the reason.")
    meta["status"] = a.status
    c.replace_text(order, c.write_frontmatter(meta, body))
    append_line(order, "%s by %s. %s" % (a.status.upper(), a.by, a.note))
    done("mark", a.status, "%s is now %s." % (a.work_id, a.status), work_id=a.work_id,
         by=a.by)


def cmd_fail(a):
    path = c.receipt(ROOT, "failure", "failed", meant=a.meant, failed=a.failed,
                     cause=a.cause, recovery=a.recovery, work_id=a.work_id)
    print("Failure recorded in " + rel(path))


def cmd_new_project(a):
    if not c.slug(a.client) or not c.slug(a.project):
        c.die("Client and project names need at least one letter or number.")
    files = c.project_files(
        c.read_text(ROOT / REG["templates"] / "context.template.md"),
        c.read_text(ROOT / REG["templates"] / "CURRENT.template.md"),
        REG["rooms"]["clients"], a.client, a.project, c.today(),
        "; ".join(REG["review_gates"]))
    created = []
    for name in sorted(files):
        path = ROOT / name
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        c.write_new(path, files[name])
        created.append(name)
    if not created:
        c.die("That project already exists. Nothing was changed.")
    done("new-project", "created", "Created %d file(s) for %s / %s."
         % (len(created), c.slug(a.client), c.slug(a.project)), files=created)


def cmd_change(a):
    with open(ROOT / "CHANGELOG.md", "a", encoding="utf-8", newline="\n") as handle:
        handle.write("- %s [%s] %s Why: %s\n" % (c.iso(), c.SESSION, c.one_line(a.what),
                                                 c.one_line(a.why)))
    done("change", "logged", "Change recorded in CHANGELOG.md.")


def main():
    global ROOT, REG
    ROOT = c.tool_root()
    REG, _ = c.load_rules(ROOT)
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    def command(name, function, *options):
        p = sub.add_parser(name)
        for flags, kwargs in options:
            p.add_argument(*flags, **kwargs)
        p.set_defaults(function=function)

    req = {"required": True}
    client = (["--client"], {}), (["--project"], {})
    command("add", cmd_add, (["--text"], {}), (["--stdin"], {"action": "store_true"}),
            (["--source"], {"default": "manual"}))
    command("route", cmd_route, (["--id"], req), *client,
            (["--content"], {"action": "store_true"}), (["--next"], req),
            (["--done-when"], req))
    command("discard", cmd_discard, (["--id"], req), (["--reason"], req))
    command("next", cmd_next, (["--client"], req), (["--project"], req), (["--next"], req),
            (["--done-when"], req),
            (["--status"], {"default": "active",
                            "choices": ["setup", "active", "waiting", "done", "archived"]}))
    command("close", cmd_close, (["--work-id"], req), (["--check-file"], {}),
            (["--check-cmd"], {}))
    command("mark", cmd_mark, (["--work-id"], req),
            (["--status"], {"required": True, "choices": ["accepted", "delivered", "dropped"]}),
            (["--by"], req), (["--note"], {"default": ""}))
    command("fail", cmd_fail, (["--meant"], req), (["--failed"], req),
            (["--cause"], {"default": "unknown"}),
            (["--recovery"], {"required": True,
                              "choices": ["worked", "did-not-work", "not-tried"]}),
            (["--work-id"], {"default": ""}))
    command("new-project", cmd_new_project, (["--client"], req), (["--project"], req))
    command("change", cmd_change, (["--what"], req), (["--why"], req))
    a = parser.parse_args()

    if a.command == "close" and bool(a.check_file) == bool(a.check_cmd):
        c.die("Give exactly one of --check-file or --check-cmd. A claim without a check "
              "does not close a work order.")
    for value in vars(a).values():
        hit = c.find_secret(value) if isinstance(value, str) else None
        if hit:
            refuse("run tools/capture.py " + a.command, "input refused: it looks like it "
                   "contains a secret (%s). Keep secrets outside this system." % hit,
                   cause="secret-like text in input", code=3)
    a.function(a)


if __name__ == "__main__":
    main()
