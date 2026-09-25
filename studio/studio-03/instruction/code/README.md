# Studio 03 Code and Tavily CLI

Use Python 3.10 or later with Bash on macOS or Linux; Windows users can use WSL. The official Tavily CLI package provides the `tvly` command.

From the course repository root, create the virtual environment in this directory and install the requirements:

```bash
python3 -m venv studio/studio-03/instruction/code/.venv
source studio/studio-03/instruction/code/.venv/bin/activate
python -m pip install -r studio/studio-03/instruction/code/requirements.txt
tvly --version
```

The requirements include the OpenAI client, `python-dotenv`, and `tavily-cli==0.1.8`. Keep the environment activated when running your agent. Set `OPENAI_API_KEY` to your class-issued key and `TAVILY_API_KEY` to a key from your own Tavily account. Create your account and apply through the [Tavily student program](https://help.tavily.com/articles/6606514713-student-account); see also the [course-prep guide](../../../../docs/course-prep.md). Never put key values in source or submitted evidence.

```bash
export OPENAI_API_KEY="your-class-issued-openai-key"
export TAVILY_API_KEY="your-own-tavily-key"
```

## Use the official CLI

Your Bash tool in `agent.py` should run one Tavily CLI command per tool request. Use the official [Tavily CLI documentation](https://docs.tavily.com/documentation/tavily-cli) and [Tavily CLI repository](https://github.com/tavily-ai/tavily-cli) for details.

```bash
tvly search "your query" --max-results 3 --json
tvly extract "https://example.com/page" --extract-depth basic --format markdown --json
```

Write the Bash execution with Python `subprocess`, using the inherited environment and a 30-second timeout for each CLI command. Keep requests sequential: do not run tools in parallel, chain shell commands, call a Tavily SDK, or add a custom search tool. The supplied `agent.py` provides the flat Bash tool schema and trace helpers; you implement execution and add each result to the conversation under its matching call ID.

## Course files

- `studio/studio-03/submission/_template/agent.py`: the runnable one-file scaffold to copy and edit.
- `question.txt`: the fixed research question read by the agent; keep it unchanged.
- `requirements.txt`: Python packages for the assignment.

After copying the template as shown in the [submission guide](../../submission/README.md), run from your team directory:

```bash
python agent.py --mode react
python agent.py --mode plan
python agent.py --mode plan --plan-file human-plan.md
```

The last command is optional and reads your numbered `human-plan.md` from the current team directory. It is separate from the generated `evidence/plan/<run_id>/plan.md`. A model-generated plan is also available in plan mode. Both modes use the same loop and shared default settings. See [the assignment](../Studio_Instruction.md) for the fixed question, comparison requirements, and evidence files.

References: [OpenAI Responses function calling](https://developers.openai.com/api/docs/guides/function-calling) and [Python subprocess](https://docs.python.org/3/library/subprocess.html).
