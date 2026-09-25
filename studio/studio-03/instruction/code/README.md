# Studio 03 Code

Use these course files to build and run your own agent loop. Run commands from this directory. Python 3.9 or later is required. Create and activate the ignored `.venv` here, then install the dependencies listed in `requirements.txt`; no App monorepo or private package is needed.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

| File | Purpose |
|---|---|
| `run.py` | Loads only `submission/<team>/agent.py`, starts a run, counts calls through the provided hook, and saves the evidence. |
| `starter.py` | Minimal starting point. Copy it to your team’s folder and implement `run_agent(question, context) -> str` there. |
| `support.py` | Provides run context and recorders, the flat `BASH_TOOL` schema, validates allowed Tavily commands, supplies a filtered tool environment, and sets timeout/output limits. Your code implements Bash execution. |
| `tavily_cli.py` | Portable course wrapper for Tavily REST search and extraction; it is not Tavily’s official binary or SDK. |
| `question.txt` | The fixed question shared by both modes. |
| `requirements.txt` | Lists the OpenAI client and dotenv packages used by the runner. |

The `context` passed to your function includes the configured OpenAI client and model, mode, optional human plan, and shared call budget. Call `context.start_model_call(...)` before every model request so the runner can count it and enforce the budget. Record each response or error with the matching context method.

Your loop includes the supplied flat schema and implements `run_bash(context, command, call_id)` using Python `subprocess`. Use `prepare_bash_argv(command)` to validate commands and `tool_environment()` for the process environment; invoke only the provided Tavily wrapper from this directory. Pass each call ID to `context.record_tool(...)` so the trace pairs each command result with the model’s tool request:

```bash
python tavily_cli.py search "<query>" --max-results 3
python tavily_cli.py extract "<url>"
```

Use the class-issued `OPENAI_API_KEY` and your own account’s `TAVILY_API_KEY`. Create your Tavily account and apply through its student program using the [course-prep guide](../../../../docs/course-prep.md) and [official student-program instructions](https://help.tavily.com/articles/6606514713-student-account). Never put key values in code, command output, or submitted files. Use the OpenAI client for Responses calls and the course wrapper for web research; do not replace it with custom search code or a Tavily SDK.

After copying the starter into your team’s folder, use the same team slug in these commands. From this directory:

```bash
TEAM=your-team
python run.py --team "$TEAM" --mode react
python run.py --team "$TEAM" --mode plan
```

The runner also accepts `--question-file <file>`, `--plan-file <file>`, `--model <id>`, `--call-budget <n>`, and `--timeout <seconds>`. Keep the fixed default question and matching settings for the comparison. Defaults are `gpt-5.6-luna`, 8 model calls, and a 45-second request timeout. Every request uses `max_output_tokens=2400`; the shared final-report policy calls for a cited report of at most 400 words that names important unknowns. Every run writes `plan.md`; it contains a plan only in plan mode. State in your explanation whether that plan came from a model or from your team. See [the Studio instructions](../Studio_Instruction.md) for the assignment contract.

## Reference documentation

- [OpenAI Responses function calling](https://developers.openai.com/api/docs/guides/function-calling)
- [Python subprocess](https://docs.python.org/3/library/subprocess.html)
- [Tavily Search API](https://docs.tavily.com/documentation/api-reference/endpoint/search) and [Tavily Extract API](https://docs.tavily.com/documentation/api-reference/endpoint/extract) (reference only; use the course `tavily_cli.py` wrapper for this assignment)
