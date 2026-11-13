# Intake interview

The intake configures the system for one person. It can be run two ways:

- by the script: `python3 scripts/intake.py --out my-answers.json`
- by a person or an AI tool asking the questions below and writing the answers
  file by hand in the format at the end of this page

Status: the script was RUN-TESTED here with typed-in synthetic answers. The
interview has not been run with a real person, so the wording is UNTESTED.

## Rules for whoever asks the questions

1. One question at a time. Wait for the answer before asking the next.
2. Ask for examples, not opinions. "What arrived yesterday?" beats "How do you work?"
3. Never ask for, accept or write down a password, key, card number or login.
   If one is offered, say so and leave it out.
4. Use nicknames for clients if the person prefers. Real names are not needed.
5. "I do not know" is a valid answer. Write `unconfirmed`.
6. Finish with the review question. Do not skip it.

## The questions

| # | Question | Why it is asked | Answers-file key |
| :--- | :--- | :--- | :--- |
| 1 | What name should the system use for you or your business? | Owner shown on the root map. | `owner_name` |
| 2 | In one or two sentences, what work do you do? | Context for any helper reading BOOT.md. | `work_summary` |
| 3 | What task do you do at least once a week that you most want to stop losing track of? | The first thing the system must make easier. | `weekly_task` |
| 4 | Where does new material arrive? (email, chat, voice notes, calls, downloads) | Becomes the allowed list of capture sources. | `arrival_points` |
| 5 | Name one current client. Which projects are you doing for them? (repeat until done) | Creates one folder per client and project. | `clients` |
| 6 | Do you also make training or content? | Switches the content and offers folders on or off. | `content_business` |
| 7 | At which moments must a person look before work goes further? | Becomes the human check in every folder contract. | `review_gates` |
| 8 | What rules must your writing follow? | Becomes VOICE.md. | `voice_rules` |
| 9 | What does a failed or sloppy result look like to you? | The failure definition, written into BOOT.md. | `failure_definition` |
| 10 | Journals, passwords and keys, banking, health and private notes about people always stay out. What else must stay out? | Added to the keep-out list in registry.json. | `keep_out` |
| 11 | Do you want an optional folder for invoice status notes? (No bank details, ever.) | Money module. Off unless the answer is yes. | `modules.money` |
| 12 | Which AI tool will work in this folder? | Recorded only. The system does not depend on it. | `harness` |
| 13 | Where will the folder live and how is it backed up? | Recorded only. Flags sync risks early. | `storage` |
| 14 | Here is what I understood. What did I misunderstand, and what did you leave out? | The review. Corrections go into BOOT.md. | `corrections` |

Follow-up questions worth asking in person for the weekly task in question 3
(the answers go into the first real project's notes, not the answers file):
what starts it, what files it needs and where they live, the exact steps, the
rules for any choice along the way, and where the person stops to review.

## The answers file

Plain JSON. `setup.py` reads it. A full example is in `intake-answers.example.json`.

```json
{
  "format_version": 1,
  "owner_name": "Pilot Owner",
  "work_summary": "Client projects plus a training and content business.",
  "weekly_task": "Knowing the next step for every client project.",
  "arrival_points": ["email", "voice notes", "downloads"],
  "clients": [
    {"name": "First Real Client", "projects": ["First Project"]}
  ],
  "content_business": true,
  "review_gates": ["Before anything is sent to a client"],
  "voice_rules": ["Plain words", "Short sentences"],
  "failure_definition": "A client project with no written next step.",
  "keep_out": [],
  "modules": {"money": false},
  "harness": "unconfirmed",
  "storage": "unconfirmed",
  "include_synthetic_example": true,
  "corrections": ""
}
```

Rules of the format:

- `format_version` must be `1` and `owner_name` must not be empty. Everything else is optional.
- Each client needs a `name` and at least one project. Names are turned into
  lowercase folder names with hyphens.
- `include_synthetic_example` adds one fake client project to practise on. Leave it on.
- Five things are always on the keep-out list whatever you answer: personal
  journaling, passwords and keys, banking and card details, health information,
  private notes about people.
- The installer refuses the file if any answer looks like a password, key or
  card number, and creates nothing.
- The answers only shape the first install. After that, the living rules are in
  `routing/registry.json` inside the system, and the answers file is not read again.
