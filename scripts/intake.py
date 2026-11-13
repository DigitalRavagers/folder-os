#!/usr/bin/env python3
"""The intake interview, one question at a time. Writes the answers file that
setup.py reads. The questions and their reasons are explained in INTAKE.md.

  python3 intake.py --out intake-answers.json

It refuses to overwrite an existing answers file. It never asks for a password
or key, and it will not save an answer that looks like one.
Python 3 standard library only.
"""
import sys
sys.dont_write_bytecode = True
import argparse
import json
from pathlib import Path

import common as c


def ask(question, default=""):
    while True:
        print()
        print(question)
        try:
            answer = input("> ").strip() or default
        except EOFError:
            c.die("The interview stopped before the end. Nothing was saved.")
        if c.find_secret(answer):
            print("That looks like a password, key or card number. It was not saved. "
                  "Please answer again without it.")
            continue
        return answer


def ask_list(question):
    return [part.strip() for part in ask(question + " (separate with commas)").split(",")
            if part.strip()]


def ask_yes(question, default):
    return ask(question + (" [Y/n]" if default else " [y/N]"),
               "y" if default else "n").lower().startswith("y")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="intake-answers.json")
    out = Path(parser.parse_args().out).expanduser()
    if out.exists():
        c.die("%s already exists. Choose another name; this script never overwrites." % out)

    print("Intake interview. One question at a time. Press Enter to skip a question.")
    a = {"format_version": 1}
    a["owner_name"] = ask("1. What name should the system use for you or your business?",
                          "Owner")
    a["work_summary"] = ask("2. In one or two sentences, what work do you do?")
    a["weekly_task"] = ask("3. What task do you do at least once a week that you most "
                           "want to stop losing track of?")
    a["arrival_points"] = ask_list("4. Where does new material arrive? For example "
                                   "email, chat, voice notes, calls, downloads")
    a["clients"] = []
    while True:
        name = ask("5. Name one current client (or press Enter when there are no more). "
                   "A nickname is fine.")
        if not c.slug(name):
            break
        projects = [p for p in ask_list("   Which projects are you doing for %s?" % name)
                    if c.slug(p)]
        a["clients"].append({"name": name, "projects": projects or ["general"]})
    a["content_business"] = ask_yes("6. Do you also make training or content?", True)
    a["review_gates"] = ask_list("7. At which moments must a person look before work "
                                 "goes further? For example: before anything is sent to a client")
    a["voice_rules"] = ask_list("8. What rules must your writing follow? For example: "
                                "plain words, short sentences")
    a["failure_definition"] = ask("9. What does a failed or sloppy result look like to you?")
    a["keep_out"] = ask_list("10. Journals, passwords and keys, banking, health and private "
                             "notes about people always stay OUT. What else must stay out?")
    a["modules"] = {"money": ask_yes("11. Do you want an optional folder for invoice "
                                     "status notes? (No bank details, ever.)", False)}
    a["harness"] = ask("12. Which AI tool will work in this folder? "
                       "(Type 'not sure' if you do not know.)", "unconfirmed")
    a["storage"] = ask("13. Where will the folder live and how is it backed up? "
                       "(Type 'not sure' if you do not know.)", "unconfirmed")
    a["include_synthetic_example"] = True

    print("\nHere is what I understood:\n")
    print(json.dumps(a, indent=2))
    a["corrections"] = ask("14. What did I misunderstand, and what did you leave out?")
    c.write_new(out, json.dumps(a, indent=2) + "\n")
    print("\nSaved %s. You can open it in a text editor to fix anything." % out)


if __name__ == "__main__":
    main()
