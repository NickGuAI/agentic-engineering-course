# Studio 11: Evaluate Your AI Coding Workflow

```text
   your AI coding tools                  tasks.csv                     claims.csv, failures.md          retest/
  +-------------------------+     +----------------------+     +----------------------------+     +----------------------+
  | 10+ real tasks from     | --> | per task: time with  | --> | what the agent claimed vs  | --> | 3 failed tasks run   |
  | your project, each with |     | AI, reviewing and    |     | what the records show;     |     | again, before and    |
  | its full session log    |     | fixing; tokens       |     | where each failure began   |     | after one change     |
  | and its commit          |     |                      |     |                            |     |                      |
  +-------------------------+     +----------------------+     +----------------------------+     +----------------------+
```

The syllabus: "Each team instruments their own development workflow. Track: time with AI, time reviewing AI output, time fixing AI mistakes. Compute true speedup ratio. Present findings."

In this studio you evaluate the AI coding workflow your team already uses on its project, from the traces your tools leave. A trace here is the session log a coding agent writes: every message and tool call, each with a timestamp. You read each task's three times from its trace. You check what the agent said it did against the records. You find where each failure started. Then you change one thing and run three failed tasks again. There is no run without AI. The ratio in this studio compares a task's whole time with its time with AI.

The tools, the tasks and the change are yours. You are graded on four checkpoints and your explanation, 10 points in all.

Teams of up to 3, the same teams as your final project. The due date is in the CourseWorks assignment.

## Setup

- The AI coding tools your team already uses: Claude Code, Codex, Cursor or another. Every task's trace must give a timestamp for each message and tool call.
  - Claude Code writes one session log per session, `~/.claude/projects/<project folder>/<session id>.jsonl`. Subagents write their own logs in `<session id>/subagents/`. Copy those too, as more logs of the task.
  - Codex writes one session log per session in `~/.codex/sessions/<year>/<month>/<day>/`.
  - A tool that keeps no such log needs one added before you start, for example a wrapper that writes each message with its time. Lecture 11 calls this instrumentation (1.1).
- Git and `gzip`.
- gitleaks 8.19 or later, an open-source secret scanner: `brew install gitleaks`, or a release binary from its [GitHub page](https://github.com/gitleaks/gitleaks/releases).
- If a tool needs an API key, use your class key, passed for one run as an environment variable.

## The four checkpoints and the explanation

Every team meets the same four checkpoints and writes the explanation. Each line below is one line of the [grading rubric](GRADING_RUBRIC.md), and each names the file that shows it. Each checkpoint is worth 2 points and the explanation is worth 2, for 10 points in all. Nothing else is graded.

### Checkpoint 1: Task times from the traces

- `tasks.csv` lists at least 10 tasks from your team's project, each with its commit and its full cleaned trace in `traces/`. Each task's three times follow from its trace and `records/` by the rule in `method.md`. `results.md` gives the true time ratio.

### Checkpoint 2: Claims against records

- `claims.csv` quotes the agent's last message on each task, with its line in the trace, beside what the records show about the result. `results.md` gives the claimed and the verified success rates.

### Checkpoint 3: Where failures start

- `failures.md` gives every failed or fixed task its first failure: a line in its trace and a code. For each code, it gives the count, the layer (spec, harness, model, tool or environment), the probable cause and the trace evidence.

### Checkpoint 4: One change, retested

- At least 3 failed tasks run again in `retest/`, before and after the one change in `retest/change.md`, each run with its trace and result. `results.md` counts the cases that improved, stayed the same and got worse, says what the traces could not show, and claims nothing beyond those cases.

### Explanation

- In `EXPLANATION.md`, answer the four questions below.
  1. Times: how did you split each task into time with AI, reviewing and fixing?
  2. Claims: where did the agent's claims and the records disagree, and why?
  3. Failures: where did most failures start, and how do you know?
  4. Retest: why did you choose this change?

## How to record the evidence

Work in `studio/studio-11/submission/<team>/` in your private repository. Keep raw logs in `work/`, which Git ignores. In this order:

1. Copy the template folder, as the [submission guide](../submission/README.md) shows.
2. Write `method.md`: your rule for the three times, in terms of the fields your traces and records hold, and your test for verified success.
3. Work on your project as you normally do, with your AI tools. Give each task an id, `t01` upwards.
4. After each task, copy its session log to `work/raw/<task id>.jsonl`. Find it by its session id: Claude Code names the file `<session id>.jsonl`, and a Codex file name ends with it. A task that took several sessions has several logs: `t01-1.jsonl`, `t01-2.jsonl`.
5. Save the other records your rule or your claims use in `records/`. Time spent reviewing is often not in the agent's log: a pull request's review and merge times are. For example, `gh pr view 12 --json state,createdAt,mergedAt,reviews,statusCheckRollup > records/pr-12.json`.
6. Clean the logs: remove every secret. Copy the raw logs to `work/clean/` and scan them:
   `gitleaks dir work/clean --redact --report-format json --report-path work/secret-scan.json`
   The report gives each secret's file and line. Replace each one with `[REDACTED]` in `work/clean/`, then scan again. A log is cleaned when the report is an empty list, `[]`.
   gitleaks does not find a password in a sentence, a database URL with a password, or a key quoted inside JSON. Before you commit, search `work/clean/` for your own keys and for `password`, `token`, `secret` and `://` followed by `@`. Remove other people's names and email addresses.
7. Copy the last report and compress each cleaned log into `traces/`:
   `mkdir -p traces && cp work/secret-scan.json traces/`
   `gzip -9 -c work/clean/t01.jsonl > traces/t01.jsonl.gz`
8. Complete `tasks.csv` from the traces and records by your rule.
9. Complete `claims.csv`: for each task, quote the agent's last message on it, and say what the tests, the trace, Git or `records/` show.
10. Write `failures.md`. For each failed or fixed task, read its trace from the start and stop at the first step that went wrong.
11. Pick at least 3 failed tasks for the retest. For each, write a case in `retest/cases/` that the agent can run again from the same starting commit. Run every case once, make the one change, run every case again. Clean and compress each run's log, as in steps 6 and 7, into `retest/traces/`. If fewer than 3 of your tasks failed or needed fixing, add tasks until 3 have.
12. Write `results.md` and `EXPLANATION.md`.

## File formats

`tasks.csv` has one row per task. `commit` is the task's commit on your project's main branch. With squash merges, it is the squash commit (`mergeCommit` in `gh pr view`). If your project is in another repository, name its URL in `method.md` and give the course staff read access. `trace` lists the task's logs in `traces/`, separated by spaces. Times are in minutes, by your rule. `tokens` is the total by the rule in `method.md`, or empty.

```csv
task_id,title,commit,trace,started_at,ended_at,ai_min,review_min,fix_min,tokens
t01,Add retries to the search tool,3f2a9c1,traces/t01.jsonl.gz,2026-11-23T14:02:10Z,2026-11-23T14:41:55Z,12.5,6.0,9.0,184220
```

`claims.csv` has one row per task. `claim` quotes the agent's last message on the task, as it wrote it. `claim_line` is that message's line number in the task's last log, uncompressed. `claimed_success` is `yes` if that message says the task is finished or its checks pass. It is `no` otherwise, also when the message says nothing about the result. `record` says what the tests, the trace, Git or `records/` show about the result, and `record_ref` points to it. `verified_success` is `yes` or `no`, by the test in `method.md`. If your team squash-merges, a task's own commit never reaches the main branch: use the pull request record.

```csv
task_id,claim,claim_line,claimed_success,record,record_ref,verified_success
t01,"<the agent's last message, as written>",412,yes,"the last test run in the session shows 2 failures",traces/t01.jsonl.gz:398,no
```

`records/` holds the records your rule and your claims cite, saved as files: pull request exports, continuous integration (CI) results, review times.

`failures.md` has two tables. The first gives each failed or fixed task its first failure. The second gives each code its count, layer, probable cause and evidence.

```markdown
| task | first failure | code |
|---|---|---|
| t01 | traces/t01.jsonl.gz:233 | tests-run-in-wrong-folder |

| code | tasks | layer | probable cause | evidence |
|---|---|---|---|---|
| tests-run-in-wrong-folder | 3 | harness | the agent starts in the repository root, and the tests need the package folder | traces/t01.jsonl.gz:233, traces/t07.jsonl.gz:88; t04 named the folder in its prompt and passed |
```

`retest/change.md` says what you changed, which code in `failures.md` it addresses, and the change itself (a diff or the setting).

`retest/cases/<case id>.md` gives the prompt the agent receives, the starting commit and the check that decides pass or fail.

`retest/results.csv` has one row per run:

```csv
case_id,from_task,run,trace,result,check_output
c1,t01,before,retest/traces/c1-before.jsonl.gz,fail,retest/checks/c1-before.txt
c1,t01,after,retest/traces/c1-after.jsonl.gz,pass,retest/checks/c1-after.txt
```

`results.md` has four parts:

- **Tasks:** the number of tasks and the true time ratio. The ratio is the sum of `ai_min`, `review_min` and `fix_min` over all tasks, divided by the sum of `ai_min`.
- **Claims:** the claimed success rate and the verified success rate, each the share of `yes` rows in `claims.csv`.
- **Retest:** how many cases improved, stayed the same and got worse.
- **What the traces could not show.**

## Submit

Commit and push to your team's own private repository (the one `bootstrap.sh` created) before the due date in CourseWorks. Each member submits the same team pull-request link through CourseWorks. A grading agent reads your private repository at the commit you submit. It does not run your code. The [submission guide](../submission/README.md) shows the folder layout.

## Rules

- Use real tasks from your team's own project work, not tasks written for this studio.
- Submit each task's full session log, cleaned and compressed. An excerpt or a summary does not count as a trace.
- Never commit a key, a password, a `.env` file or another person's private data. Clean every log before it enters `traces/`.
- Your tools and how good your AI is do not affect the grade. Neither do your success rates, your true time ratio or the time AI took or saved.
- Every member must be able to explain the method and the numbers behind every line (merge defense).

## Optional, not graded

- Export your tool's OpenTelemetry data for the same tasks and compare it with the session logs.
- Retest a second change on the same cases.

## Read

- Lecture 11: 1.1 OpenTelemetry, 1.2 Tracing an agent, 2.1 Failure taxonomy, 2.2 Trajectory-based error analysis, 3.1 Regression evals on every change, 3.4 Production failures back into the eval set, 3B.1 What honest measurement is
- Hamel Husain and Shreya Shankar, [AI Evals: Everything You Need to Know](https://hamel.dev/blog/posts/evals-faq/), on error analysis
- OpenTelemetry, [GenAI semantic conventions](https://github.com/open-telemetry/semantic-conventions-genai)
