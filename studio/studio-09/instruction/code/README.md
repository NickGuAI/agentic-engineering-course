# Studio 09 Harbor kit

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

Copy the submission template into your team folder, then the kit's files.
Your team slug uses letters, digits, `-` and `_`.

```bash
TEAM='your-team'
mkdir -p "studio/studio-09/submission/$TEAM"
cp -R studio/studio-09/submission/_template/. "studio/studio-09/submission/$TEAM/"
cp -R studio/studio-09/instruction/code/make_tasks.py \
  studio/studio-09/instruction/code/metrics.py \
  studio/studio-09/instruction/code/agent_template.py \
  studio/studio-09/instruction/code/requirements.txt \
  studio/studio-09/instruction/code/questions.example.jsonl \
  studio/studio-09/instruction/code/task-template \
  studio/studio-09/instruction/code/example_agent \
  "studio/studio-09/submission/$TEAM/"
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

Keep raw Harbor jobs and generated tasks out of Git. The studio's `.gitignore`
already covers `.venv/` and `.env` files.

```bash
printf '%s\n' 'jobs/' 'tasks*/' >> .gitignore
```

Read your API keys without showing them or writing them to a file. Skip a
`read` command if that variable is already exported in your shell. The Tavily
key is the one your Studio 06 system uses. If your system reads a key under
another name, read it under that name and pass it with `--agent-env` below.

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

Write your own 10 questions, keys, rules and sources into `questions.jsonl`
before you build `tasks`. Each line is a JSON object with these fields:

- `id`: `q01` through `q10`.
- `question`: the question text.
- `answer`: the reference answer.
- `pass_rule`: how the judge decides pass or fail.
- `sources`: a nonempty list of primary-source URLs.
- `written_on`: the date, as YYYY-MM-DD.

To check your setup on the two sample questions first, use a separate file, a
separate tasks folder and separate job names, such as `oracle-sample`. Put
those names into the commands below for that check. The two rows of
`questions.example.jsonl` are the course's sample questions, with answers the
course verified from primary sources on 2026-11-06.

```bash
cp questions.example.jsonl questions.sample.jsonl
python make_tasks.py questions.sample.jsonl --output tasks-sample --team "$TEAM"
```

Build the Harbor tasks. Use a new output directory after editing any question.
The generator refuses to overwrite an existing directory. After a rebuild or a
rerun, put the new folder and job names into the copy commands and the metrics
command below.

```bash
python make_tasks.py questions.jsonl --output tasks --team "$TEAM"
```

For each task, the question goes into `instruction.md`. The key goes into
`tests/answer.json` and the oracle's `solution/answer.md`. Harbor builds only
`environment/`. It uploads `solution/` only for the oracle, and it uploads
`tests/` after the agent finishes. Upload only your system's code in your agent
file. Never upload `questions.jsonl`, `tests/` or `solution/` to your agent.

Run the oracle on every task. Each trial should have reward `1`.

```bash
harbor run -p tasks -a oracle -e docker -n 2 -k 1 -r 0 \
  -o jobs --job-name oracle-check \
  --verifier-env 'OPENAI_API_KEY=${OPENAI_API_KEY}'
```

Run the wrong-answer agent. Each trial should have reward `0`.

```bash
harbor run -p tasks -a example_agent.wrong:WrongAnswerAgent -e docker -n 2 -k 1 -r 0 \
  -o jobs --job-name wrong-check \
  --verifier-env 'OPENAI_API_KEY=${OPENAI_API_KEY}'
```

Inspect the `verifier/reward.txt` and `verifier/judge.json` files under each
trial directory in the two jobs. Check the decisions against your keys. A
Harbor infrastructure error is not a successful negative check. Give reruns
new job names.

Copy one question's two trials into your evidence folder. Each copy keeps the
trial's `result.json` and its `verifier/` folder.

```bash
for pair in oracle-check:pass wrong-check:fail; do
  job="${pair%%:*}"; kind="${pair##*:}"
  t="$(ls -d "jobs/$job"/q01__* | head -1)"
  mkdir -p "eval/oracle/$kind/$(basename "$t")"
  cp "$t/result.json" "eval/oracle/$kind/$(basename "$t")/"
  cp -R "$t/verifier" "eval/oracle/$kind/$(basename "$t")/"
done
```

Check your setup with the example research agent: five attempts per question
and two concurrent trials. This small Tavily-plus-OpenAI agent checks your
setup. It does not replace your Studio 06 system.

```bash
harbor run -p tasks -a example_agent.agent:ExampleAgent -m gpt-5.6-luna \
  -e docker -k 5 -n 2 -r 0 -o jobs --job-name setup-research \
  --agent-env 'OPENAI_API_KEY=${OPENAI_API_KEY}' \
  --agent-env 'TAVILY_KEY=${TAVILY_KEY}' \
  --verifier-env 'OPENAI_API_KEY=${OPENAI_API_KEY}'
```

Copy `agent_template.py` to `agent.py`. Fill in `install()` to upload and
install your Studio 06 system, and change the command in `run()` to call it.
Keep its lead agent and search sub-agents. Harbor creates a new sandbox for
each trial. Your entry point receives the question through `agent.py` and must
write:

- `/app/answer.md`: the answer first, then the source URLs it used.
- `/app/trace.jsonl` (optional): one JSON object per tool call, with the tool
  name, the input or query, and the results or source excerpts. Do not record
  keys or headers.

```bash
cp agent_template.py agent.py
```

`self.model_name` is the model from `-m`. Your agent file can pass it to your
system. Set any other role models in your system's own configuration.
`example_agent/agent.py` shows file upload, command execution and usage
collection. The example runner writes `/app/usage.json` with OpenAI token
usage, Tavily credits and wall time. That file is optional for your system.

Run your system five times per question. Set `MODEL` to the model your system
accepts. Pass each key your system reads with `--agent-env`, under the name
your system reads it by.

```bash
MODEL=gpt-5.6-luna
harbor run -p tasks -a agent:TeamAgent -m "$MODEL" \
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
path. The metrics script checks three things. Each expected question has
exactly five trials. Rewards match the judge decisions. No trial has an
infrastructure error.

Copy the job into your evidence folder. The copy keeps the job's `result.json`
and `config.json` and every trial's `result.json` and `verifier/` folder. It
leaves out each trial's `artifacts/`, `agent/` and logs, which hold prompts,
answers and traces.

```bash
mkdir -p eval/job
cp jobs/studio06-eval/result.json jobs/studio06-eval/config.json eval/job/
for t in jobs/studio06-eval/q*__*/; do
  d="eval/job/$(basename "$t")"
  mkdir -p "$d"
  cp "$t/result.json" "$d/"
  cp -R "$t/verifier" "$d/"
done
```

`pass_1` (pass@1) is passed trials divided by all trials. `pass_5` (pass^5) is
the fraction of questions whose five trials all passed. Harbor's own **pass@5**
means at least one success in five attempts. It does not mean pass^5. The
Harbor mean reward cross-checks pass@1. Its pass@k values stay separate.

`tests/judge.py` makes exactly one OpenAI Responses request per judged trial,
with `gpt-5.5`, structured JSON, no SDK retries, reasoning `none` and
temperature `0`. `tests/rubric.md` holds the five criteria and the answer
check. The pass rule decides pass or fail. The rubric scores are diagnostic. A
missing trace sets tool efficiency to `0.5` and marks it unscored. The judge
reads the excerpts it is given. It cannot open URLs, so inspect source claims
yourself.

A valid judgment writes `reward.txt` with only `0` or `1` and a newline. It
also writes `judge.json` with these fields:

- `status`, `question_id`, boolean `pass`, `scores` (the five 0–1 criteria),
  `reason` and `unscored`.
- `model`, `prompt_hash` and `rubric_sha256` (the SHA-256 of the exact
  `rubric.md` bytes).
- `settings`, `usage`, `response_id` and `wall_time_seconds`.

An error record keeps the
rubric fingerprint when the file was readable. An API failure leaves an error
record and no reward. Fix it before computing metrics.

The results JSON has this core shape. The numbers only show the field types,
and `trial_id` is the trial's folder name.

```json
{
  "setup": {"team": "your-team", "job_name": "studio06-eval", "agent": "studio-06-team", "model": "gpt-5.6-luna", "rubric_sha256": "64-character SHA-256 hex digest"},
  "runs_per_question": 5,
  "questions": [
    {"id": "q01", "runs": [
      {"trial_id": "q01__CqUa5gB", "pass": true,
       "scores": {"factual_accuracy": 1.0, "citation_accuracy": 1.0,
                  "completeness": 1.0, "source_quality": 1.0, "tool_efficiency": 0.5},
       "reason": "Judge's reason", "unscored": ["tool_efficiency"]}
    ]}
  ],
  "pass_1": 1.0,
  "pass_5": 1.0
}
```

Each question has exactly five `runs` in the real report. The compact example
shows one. Keep the question ids and trial ids so a reader can recompute the
metrics. Keep raw Harbor jobs local. `setup` also records the agent version,
the model provider, the judge model and the job UUID. It also records SHA-256
hashes of the configuration, the questions file and the rubric. The rubric
fingerprint must be the same in every trial. The top-level `harbor_pass_at_k` object keeps
Harbor's separate pass@2, pass@4 and pass@5.
