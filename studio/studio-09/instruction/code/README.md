# Studio 9 Harbor code kit

```text
questions.jsonl → make_tasks.py → tasks/q01 … q10
                                     │
                         Harbor + your Studio 06 system
                                     │
                            /app/answer.md + trace
                                     │
                       tests/test.sh → one judge call
                                     │
                  reward.txt (0/1) + judge.json (scores)
                                     │
                         five trials per question
                                     │
                           metrics.py → results.json
```

Use Python 3.12, Docker with Docker Compose, and `uv`. The commands below use
Bash. Run them from the repository root, then stay in your team's folder.

Copy the kit into your team's submission folder.

```bash
TEAM=my-team
mkdir -p "studio/studio-09/submission/$TEAM"
cp -R studio/studio-09/instruction/code/. "studio/studio-09/submission/$TEAM/"
cd "studio/studio-09/submission/$TEAM"
```

Install the pinned Harbor version and the kit's Python dependency.

```bash
uv tool install --python 3.12 harbor==0.25.0
uv venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
docker compose version
harbor --version
```

Keep local environments and raw Harbor jobs out of Git.

```bash
printf '%s\n' '.venv/' 'jobs/' 'tasks*/' >> .gitignore
```

Read your API keys without showing them or writing them to a file. Skip a
`read` command if that variable is already exported in your shell.

```bash
read -rsp 'OpenAI API key: ' OPENAI_API_KEY; printf '\n'
read -rsp 'Tavily API key: ' TAVILY_KEY; printf '\n'
export OPENAI_API_KEY TAVILY_KEY
```

The single quotes in `--agent-env` and `--verifier-env` below are intentional.
They let Harbor resolve host variables at runtime while saving references,
rather than key values, in its job configuration. Never replace them with a
literal key. The agent and verifier need separate flags even in a shared
sandbox.

Create `questions.jsonl` from the example format, then replace the placeholder
content with your verified questions, keys, rules, and sources.

```bash
cp questions.example.jsonl questions.jsonl
```

Each line is a JSON object with `id` (`q01` through `q10`), `question`, `answer`
(reference text), `pass_rule` (one sentence), `sources` (a nonempty list of
primary-source URLs), and `written_on` (YYYY-MM-DD). The generator also accepts
a smaller file for setup checks. The `questions.example.jsonl` placeholder
rows demonstrate the format; they are not verified research questions.

Build the Harbor tasks. Use a new output directory after editing any question.
The generator refuses to overwrite an existing directory.

```bash
python make_tasks.py questions.jsonl --output tasks --team "$TEAM"
```

For each task, the question goes into `instruction.md`. The key goes into
`tests/answer.json` and the oracle's `solution/answer.md`. Harbor builds only
`environment/`; it uploads `solution/` only for the oracle and uploads `tests/`
after the agent finishes. Upload only your system's code in your adapter;
never upload `questions.jsonl`, `tests/`, or `solution/` to your agent.

Run the oracle on every task. Each trial should have reward `1`.

```bash
harbor run -p tasks -a oracle -e docker -n 2 -k 1 -r 0 \
  -o jobs --job-name oracle-check \
  --verifier-env 'OPENAI_API_KEY=${OPENAI_API_KEY}'
```

Run the deliberately wrong agent. Each trial should have reward `0`.

```bash
harbor run -p tasks -a example_agent.wrong:WrongAnswerAgent -e docker -n 2 -k 1 -r 0 \
  -o jobs --job-name wrong-check \
  --verifier-env 'OPENAI_API_KEY=${OPENAI_API_KEY}'
```

Inspect the `verifier/reward.txt` and `verifier/judge.json` files under each
trial directory in the two jobs. Check the decisions against your keys. A
Harbor infrastructure error is not a successful negative check. Give reruns
new job names.

Check the research-agent plumbing with five attempts per question and two
concurrent trials. This small Tavily-plus-OpenAI agent checks your setup; it
does not replace your Studio 06 system.

```bash
harbor run -p tasks -a example_agent.agent:ExampleAgent -m gpt-5.6-luna \
  -e docker -k 5 -n 2 -r 0 -o jobs --job-name setup-research \
  --agent-env 'OPENAI_API_KEY=${OPENAI_API_KEY}' \
  --agent-env 'TAVILY_KEY=${TAVILY_KEY}' \
  --verifier-env 'OPENAI_API_KEY=${OPENAI_API_KEY}'
```

Edit `agent_template.py`: fill in `install()` to upload and install your Studio
06 system; update the command in `run()` to call it. Keep its lead agent and
search sub-agents. Harbor creates a new sandbox for each trial. Your entry
point receives the question through the adapter and must write:

- `/app/answer.md`: answer first, then the source URLs it used.
- `/app/trace.jsonl` (optional): one JSON object per tool call, with tool name,
  input/query, and results or source excerpts. Do not record keys or headers.

`self.model_name` is the model from `-m`. Your adapter can pass it to your
system; set any additional role models in your system's own configuration.
`example_agent/agent.py` shows file upload, command execution, and usage
collection. The example runner writes `/app/usage.json` with OpenAI token
usage, Tavily credits, and wall time; that file is optional for your system.

Run your system five times per question. Set `MODEL` to the model your system
accepts.

```bash
MODEL=gpt-5.6-luna
harbor run -p tasks -a agent_template:TeamAgent -m "$MODEL" \
  -e docker -k 5 -n 2 -r 0 -o jobs --job-name studio06-eval \
  --agent-env 'OPENAI_API_KEY=${OPENAI_API_KEY}' \
  --agent-env 'TAVILY_KEY=${TAVILY_KEY}' \
  --verifier-env 'OPENAI_API_KEY=${OPENAI_API_KEY}'
```

Compute the report from your system's completed job.

```bash
python metrics.py jobs/studio06-eval --questions questions.jsonl \
  --output eval/results.json --team "$TEAM"
```

For a setup-only report, use `jobs/setup-research` with a different output
path. The metrics script checks that each expected question has exactly five
trials, that rewards match the judge decisions, and that no trial has an
infrastructure error.

`pass_1` (pass@1) is passed trials divided by all trials. `pass_5` (pass^5) is
the fraction of questions whose five trials all passed. Harbor's **pass@5**
means at least one success in five attempts; it does not mean pass^5. The
Harbor mean reward cross-checks pass@1; its pass@k values remain separate.

`tests/judge.py` makes exactly one OpenAI Responses request per judged trial,
using `gpt-5.5`, structured JSON, no SDK retries, reasoning `none`, and
temperature `0`. `tests/rubric.md` contains the five criteria and the answer
check. The pass rule decides pass/fail; rubric scores are diagnostic. A missing
trace sets tool efficiency to `0.5` and marks it unscored. The judge reads
provided excerpts; it cannot open URLs. Inspect source claims yourself.

A valid judgment writes `reward.txt` containing only `0` or `1` and a newline.
It also writes `judge.json` with `status`, `question_id`, boolean `pass`,
`scores` (the five 0–1 criteria), `reason`, `unscored`, `model`, `prompt_hash`,
`settings`, `usage`, `response_id`, and `wall_time_seconds`. API failures leave
an error record and no reward; fix them before computing metrics.

The results JSON has this core shape (the numbers below only illustrate the
field types):

```json
{
  "setup": {"team": "my-team", "job_name": "studio06-eval", "agent": "studio-06-team", "model": "gpt-5.6-luna"},
  "runs_per_question": 5,
  "questions": [
    {"id": "q01", "runs": [
      {"trial_id": "Harbor trial id", "pass": true,
       "scores": {"factual_accuracy": 1.0, "citation_accuracy": 1.0,
                  "completeness": 1.0, "source_quality": 1.0, "tool_efficiency": 0.5},
       "reason": "Judge's reason", "unscored": ["tool_efficiency"]}
    ]}
  ],
  "pass_1": 1.0,
  "pass_5": 1.0
}
```

Each question has exactly five `runs` in the actual report; the compact example
shows one. Retain the question IDs and trial IDs so a reader can recompute the
metrics. Keep raw Harbor jobs local; they contain prompts, answers, and traces.
`setup` also records the agent version, model provider, judge model, job UUID,
and SHA-256 hashes of the configuration and questions file. The top-level
`harbor_pass_at_k` object retains Harbor's separate pass@2, pass@4, and pass@5.
