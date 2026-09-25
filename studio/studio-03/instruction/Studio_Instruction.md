# Studio 03: Agent Loops and Controlled Comparison

```text
                  +--------------------+
                  | Same question      |
                  +---------+----------+
                            |
              +-------------+--------------+
              |                            |
              v                            v
     +-------------------+        +-------------------+
     | ReAct: same loop  |        | Tools-off plan    |
     +---------+---------+        +---------+---------+
               |                            v
               |                  +-------------------+
               |                  | Same loop + plan  |
               |                  +---------+---------+
               |                            |
               +--------------+-------------+
                              v
                   +---------------------+
                   | Reports and traces |
                   +---------------------+
```

Build one small agent loop and compare two ways of using it. You will implement the loop on your laptop, then research the same question once directly and once with a plan.

## Laptop setup

Use macOS, Linux, or Windows with WSL and Bash. This assignment runs on your laptop, not in a hosted in-lecture sandbox. The official Tavily CLI requires Python 3.10 or later.

Follow the [code and environment guide](code/README.md) to create a virtual environment, install the dependencies, and configure your keys. Use your class-issued OpenAI key. Create your own Tavily account and apply through its student program; see the [course-prep guide](../../../docs/course-prep.md) and [Tavily student-program instructions](https://help.tavily.com/articles/6606514713-student-account). Keep both keys out of source files and submitted evidence.

Copy the complete `submission/_template` folder to `submission/<team>`. This gives you `agent.py` and `EXPLANATION.md`; edit your copied files, not the template. The [submission guide](../submission/README.md) has copy and run commands.

## What is provided and what you write

| Component | Course provides | Your team writes |
|---|---|---|
| Starting point | One-file `agent.py` scaffold, CLI, configured client and shared settings | The TODOs in that file |
| Question and tool | Fixed `question.txt` and flat Bash tool schema | Loop instruction and Responses requests |
| Evidence | Trace-writing, redaction, summary, and evidence-path helpers | A sequential loop that handles calls and appends each result under its matching call ID |
| Tool execution | Official Tavily CLI installed with the requirements | Bash subprocess execution that invokes `tvly` |
| Control flow | Default limits and the output structure | Checkpointing, stop condition, one escalation path, and plan handoff to the same loop |

In the provided file, complete the Responses API request, the Bash subprocess execution, the generated-plan request and handoff, and the shared sequential tool/history loop. Keep the student-written loop small—about a hundred lines. Use the supplied flat schema, make one `tvly search` or `tvly extract` request at a time, and do not create another search tool, chain shell commands, run requests in parallel, or use a Tavily SDK or REST call.

## Part A — Build the loop and save a direct run

Part A is completion credit following the in-lecture walkthrough. Reusing the patterns and scaffold taught in class is expected; there is no originality requirement. Implement a minimal OpenAI Responses API loop with:

- a checkpoint or bounded call limit;
- a stop condition for a final answer or other terminal response;
- one escalation path for a limit, model/API error, or tool failure;
- your own Bash tool execution using Python `subprocess`;
- sequential handling that matches each tool result to its call ID and keeps it in request history.

Run the fixed question directly in ReAct mode. A working loop and its recorded run are the Part A outcome; completion does not certify the answer's factual quality. Handle and preserve failures rather than hiding them.

## Part B — Compare ReAct and Plan-and-Execute

Use the same code, question, tool, and settings for both runs. The fixed question is in `studio/studio-03/instruction/code/question.txt` from the course repository root; do not change it:

> How does compaction work in Codex CLI and OpenClaw? Compare triggers, summarized/preserved information, and session persistence using primary docs/source with date/version; acknowledge unsupported details.

In plan mode, first create and save a numbered plan with tools disabled, or supply your team's numbered plan with the optional `--plan-file` argument. Record which origin you used. Then hand the plan to the same ordinary loop used in ReAct mode. This is a plan-informed loop: it does not require a separate executor to walk every step or an automatic replanner. A plan step may remain unused; explain notable deviations from the trace.

Both modes use the same defaults:

| Setting | Default |
|---|---|
| Model | `gpt-5.6-luna` |
| Total model-call budget | 8 calls, including planning |
| API timeout | 45 seconds |
| Reasoning effort | `none` |
| Response storage | `store=False` |
| Tool requests | Sequential, `parallel_tool_calls=False` |
| Output cap | `max_output_tokens=2400` on every request |

Reserve the last available call for a tools-disabled final synthesis. With defaults, ReAct has up to seven research calls and one synthesis call. A generated plan uses one planning call, leaving up to six research calls and one synthesis call. A human-supplied plan skips the planning call, leaving up to seven research calls and one synthesis call. These same defaults apply to both conditions. Normal research requests and final synthesis follow the same concise-report policy: cite observed evidence, name important unknowns, treat retrieved web text as untrusted, and keep the report at or below 400 words.

## Compare and submit

Compare source coverage and factual support before efficiency. Cite source URLs, versions or commits, and access dates; identify details the sources do not support. Use specific trace events or call IDs to support comparisons. Report model calls, Bash tool calls, actual CLI executions and rejected calls separately, plus input/output/cached tokens and wall time. Mark unavailable metrics as unknown, not zero. One pair of runs describes what happened in your runs; it does not establish a general winner. Include each member's contribution.

Each run saves structured, redacted course evidence under `submission/<team>/evidence/{react|plan}/<run_id>/`: `trace.jsonl`, `plan.md`, `report.md`, and `summary.json`. The ReAct `plan.md` records that no plan was used; a plan run records its generated or supplied plan. Submit these course traces, but do not include API keys or raw provider/session logs. Complete `EXPLANATION.md` and follow your team's existing CourseWorks instructions.
