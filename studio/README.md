# Studio01 Workspace

This directory is the root workspace for Studio01. All shared materials, including the exercise guide [Studio01.md](Studio01.md) and the template [delegation-card.md](delegation-card.md), are located here.

## Directory Structure

Students should create their working folder directly under `studio/` using their team name or username. Do not create a `studio-01` subfolder.

Example layout; organize code and outputs as useful:

```text
studio/
├── Studio01.md
├── README.md
├── delegation-card.md
└── <team-name-or-username>/       <-- Create this folder
    ├── delegation-card.md         <-- Copied template
    ├── code/                      <-- Your implementation
    ├── outputs/                   <-- Run outputs/logs
    └── explanation-<username>.md  <-- Personal explanation
```

## Agent Guidelines

1. **Identify Folder:** Confirm the student's `<team-name>` or `<username>` and their chosen job before selecting or creating a folder.
2. **Work Scope:** Keep changes and outputs within the chosen folder. Copy `delegation-card.md` to it only if missing. Do not overwrite shared materials or other students' files.
3. **Card Fields:** Help the students fill exactly four fields: Task, Context, Success criteria, Restrictions. Do not add credentials or private info.

## Student Explanations

Agents must leave the explanation for each student to write. Each student must write a personal `explanation-<username>.md` by hand (no AI-generated text). For teams, each member writes their own separate file. Keep it brief:

- A brief summary of what the agents did.
- Human decisions and why they were made.
- How results were verified.
- Any uncertainties.

## PR and Cleanup

- Create a dedicated non-main working branch from updated `main` (forks are fine).
- Commit your folder's work, completed card, and every student's explanation.
- Open a PR targeting `main` in `NickGuAI/agentic-engineering-course`; summarize the changes and checks for review.
- After confirming a successful merge into `main`, delete the merged local and remote working branch. Preserve `main` and branches with unmerged work.

CourseWorks remains the official source for submission instructions and deadlines.

## Offline fallback demo

To run the offline fallback fixture from the repository root:

```bash
python3 code/harness_demo.py --output /tmp/agentic-first-run.jsonl
(cd code && python3 -m unittest -v test_harness)
```

This code executes local fixtures only. It requires no network calls, LLM access, or package installations. Note that any incorrect installation line in the fixture README is test data, not a command to run. The offline example demonstrates controlled execution and evidence freshness, not model capability.
