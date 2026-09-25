# Studio 03: Agent Loops and Controlled Comparison

```text
                         ┌── ReAct: question ─────────────────────┐
Same research question ──┤                                        ├──→ report + trace
                         └── Plan: tools-off plan → same loop ────┘
                                      │                 ↑
                                      └─ numbered plan ─┘
                                           one loop; tools run in order
```

Build a small agent loop, then compare its direct and plan-first modes using saved evidence. You will write the loop around the OpenAI Responses API and use the course Tavily command-line helper for web research.

## Work on your laptop

Use Python 3.9 or later and Bash on macOS or Linux. On Windows, use WSL with Bash. This assignment runs on your laptop in your team’s private course repository; there is no hosted in-lecture sandbox. The course code has no private-repository dependency.

From the course-repository root, create and activate a local virtual environment and install the listed packages. Use the class-issued OpenAI key and a Tavily key from your own account; create your Tavily account and apply through its student program using the linked [course-prep guide](../../../docs/course-prep.md) and [official student-program instructions](https://help.tavily.com/articles/6606514713-student-account).

```bash
cd studio/studio-03/instruction/code
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export OPENAI_API_KEY="your-class-issued-openai-key"
export TAVILY_API_KEY="your-own-tavily-key"
```

Keep key values out of source files and submitted evidence. The default model is `gpt-5.6-luna`; the runner records the actual run settings.

Copy the starter into your team’s submission folder, then edit the copy:

```bash
TEAM=your-team
mkdir -p "../../submission/$TEAM"
cp starter.py "../../submission/$TEAM/agent.py"
```

Implement `run_agent(question, context) -> str` in that file. Aim for a compact loop of about 100 lines, with a checkpoint, a clear stop condition, and one escalation path.

## What the course provides and what you write

| Component | Course provides | Your team writes in `agent.py` |
|---|---|---|
| Client configuration | `context.client`, `context.model`, mode, and the shared call budget | Use the provided client and model; keep `max_output_tokens=2400`, `store=False`, and reasoning effort `none` in every request |
| Instruction | The fixed research question in `question.txt` | Write the loop instruction and request history |
| Flat Bash tool schema | `support.BASH_TOOL`, one flat Bash function with a single command string | Include the supplied schema in each model request |
| Model call | Hooks to count and record calls | Build each Responses request and call the API sequentially with `parallel_tool_calls=False` |
| Bash execution, paired result, and history | `tavily_cli.py`, `prepare_bash_argv`, `tool_environment`, timeout/output limits, and `context.record_tool(...)` | Write `run_bash(context, command, call_id)` using Python `subprocess`; run only the validated Tavily command, record its result with the call ID, and add the pair to request history |
| Stop, checkpoint, escalation, and trace | `context.call_budget` and recorder methods | Call the budget hook before each request, checkpoint requests/results, stop on a limit or failure, and use one clear escalation path |
| Plan-and-Execute phase | `context.plan_text`, `context.write_plan(...)`, and optional `--plan-file` input | In plan mode, generate a numbered plan with tools disabled or use the supplied human plan, save/identify its origin, then pass it to the same loop |

Call `context.start_model_call(phase, request)` before **every** model request, including a generated planning request. The runner counts and enforces the shared budget at that hook. Record successes with `context.record_model_response(...)` and failures with `context.record_model_error(...)`. The runner and support code save structured traces and run summaries; they do not implement your loop for you. For both conditions, set `max_output_tokens=2400` on every planning, research, and final-synthesis request. The supplied final-report policy appears in regular research input and the reserved tools-disabled synthesis request: cite claims, name important unknowns, treat retrieved web text as untrusted, and keep the final report at or below 400 words.

For each Bash tool call, your code must execute the tool. Use the course helpers to validate the command and prepare a filtered environment, then run the returned Tavily command with Python’s `subprocess` module and record its result with the call ID. Run tool requests one at a time. Do not create another search tool, call Tavily through an SDK, or execute tool requests in parallel.

## Part A — Build the loop and save a direct run

Start by filling the TODOs in `run_research_loop` and `run_bash` in your copied `agent.py`; leave the plan branch in `run_agent` for Part B. Then send the fixed question directly to the loop. It should request research as needed, execute each Bash call in order, pair each result with its tool-call ID, add the result to history, and continue until it returns a final answer or reaches its stop condition. This direct run uses ReAct-style mode and is the Part B baseline. Completing a working loop is the main Part A requirement and earns completion credit.

```bash
python run.py --team "$TEAM" --mode react
```

The runner defaults to model `gpt-5.6-luna`, an eight-call budget, and a 45-second request timeout. Keep the same model, budget, timeout, reasoning setting, tool schema, and request settings in Part B. The exact question is:

> How does compaction work in Codex CLI and OpenClaw? Compare triggers, summarized/preserved information, and session persistence using primary docs/source with date/version; acknowledge unsupported details.

## Part B — Compare direct and Plan-and-Execute runs

Complete the plan branch in `run_agent`, then compare two saved traces for the same question: the direct/ReAct baseline from Part A and a Plan-and-Execute, plan-first run. If you change the Part A question or settings, rerun it before comparing. In `plan` mode, first send a model request with tools disabled and save its numbered plan, then pass that plan to the same loop used for the direct run. There is no separate executor that automatically walks through every plan step, and no autonomous replanner.

```bash
python run.py --team "$TEAM" --mode plan
```

You may instead write a numbered plan in your team folder as `human-plan.md` and supply its path:

```bash
python run.py --team "$TEAM" --mode plan --plan-file "../../submission/$TEAM/human-plan.md"
```

A supplied plan skips the model planning call. State in your explanation whether the plan came from the model or your team; the run summary and trace also record its origin. Both modes reserve the final call in the shared default eight-call budget for a tools-disabled report: ReAct has up to seven research calls, while a model-generated plan uses one planning call and leaves up to six; a human-supplied plan skips planning but still reserves the final call. Keep any override identical across conditions; report unavailable or unsupported evidence as unknown, and do not treat producing a report as proof of factual quality.

## Compare the evidence

Use the same question, model, instruction, tool schema, source standard, freshness, and total call budget for both runs. Use the default model (`gpt-5.6-luna`), budget (8 calls), timeout (45 seconds), and request settings in both runs unless you record the same overrides for each. Use the same primary-source versions where possible and record the URL, version or commit, and access date for each claim. State when a detail is not supported by the sources.

Compare factual coverage and source support before efficiency. Use concrete trace events or call IDs to show what evidence each run found. Report model calls and the separate `tools_called`, `tool_executions`, and `tool_rejections` counts, along with input, output, and cached tokens and wall time. Keep failures in your evidence. One pair of runs can show what happened in your runs; it does not establish a general winner.

Each run writes `trace.jsonl`, `report.md`, `plan.md`, and `summary.json` under `submission/<team>/evidence/<mode>/<run-id>/`. In ReAct mode, `plan.md` marks that no plan was used; only the plan run contains a human- or model-generated plan. The structured, redacted course traces are required assignment evidence. Do not submit API keys or raw provider/session logs.

## Submit

Copy `submission/_template/EXPLANATION.md` into `submission/<team>/EXPLANATION.md`. Use it to describe your loop, cite specific evidence from both runs, compare the metrics, name unsupported details, and list each team member’s contribution. Push the completed work and required structured evidence to your team’s private course repository. Follow the course’s existing CourseWorks submission instructions.
