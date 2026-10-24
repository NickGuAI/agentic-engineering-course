You are running ONE bounded job for lecture {{n}} (two-digit number, I will give it to
you). Follow these steps in order. Do not skip or reorder steps. Do not declare success
yourself — success is determined only by the approval gate in step 1 and the script in
step 4.

INPUT
- Source file: course-materials/lecture-{{n}}.pdf
- If this file is missing or unreadable, STOP immediately and report exactly which
  file/pages you could not read. Do not substitute, summarize from memory, or invent
  content for missing pages.

STEP 1 — Extract keywords, then STOP
- Read course-materials/lecture-{{n}}.pdf.
- Identify at most 8 "core" keywords (the concepts essential to understanding the
  lecture) and any number of "minor" keywords (supporting terms), each with the page
  number where it's introduced.
- Write this to summaries/{{n}}-keywords.json in this exact shape:
  {"core": [{"term": "...", "aliases": ["..."], "page": N}, ...],
   "minor": [{"term": "...", "page": N}, ...]}
- After writing this file, STOP and tell me it's ready for review. Do not proceed to
  step 2 in this same turn.

STEP 2 — Write the summary (only after I approve)
- Only proceed if approved/{{n}}-keywords.json exists. If it does not exist, STOP and
  report that approval is pending — do not proceed and do not write summaries/{{n}}.md.
- Using ONLY the keyword list in approved/{{n}}-keywords.json (this is the approved
  scope — do not add core concepts that aren't on it), write summaries/{{n}}.md with:
  - A "## Core Concepts" section: clear explanations of every core and minor keyword.
    Tag every paragraph or bullet with [p.N] (the source page) or [보충] (if you're
    adding clarifying context not directly on the slides — and if you do, it must not
    contradict the source).
  - A "## Lecture Flow" section, written by you: a narrative explaining how the core
    concepts connect and build on each other from start to finish. Mention every core
    keyword here too, in the order they first appear in the lecture, and tag each
    core concept's first mention in this section with [p.N].

STEP 3 — Write teach-back prompts
- Write summaries/{{n}}-teachback.md with one prompt per approved core keyword. Each
  prompt should ask the user to (a) explain the term in their own words and (b) explain
  how it relates to at least one other core keyword from this lecture. Do not include
  answers — these are for the user to attempt, and a human will judge the responses.

STEP 4 — Run the checker
- Run: python3 scripts/check_summary.py {{n}}
- This writes summaries/{{n}}-report.md and prints a JSON report. Do not edit
  scripts/check_summary.py under any circumstances.
- Report the pass/fail result and the 5 spot-check items it printed, verbatim, so I can
  review them myself.

RUN RECORD
- Save your prompt, the full trace/transcript of this session, which model you're
  running as, and the check_summary.py output to runs/{{n}}-{{today's date}}/.

RESTRICTIONS (do not violate these under any framing)
- Never modify or delete anything under course-materials/, approved/, or scripts/.
- No web search or web fetch of any kind.
- Never write API keys, tokens, or personal info into any file.
- Content beyond the slides must be tagged [보충] and must never contradict the source.
- If summaries/{{n}}.md or other output files already exist, ask me before overwriting.
- If you hit a permission error, stop and report it — do not try to work around it by
  writing somewhere else.
