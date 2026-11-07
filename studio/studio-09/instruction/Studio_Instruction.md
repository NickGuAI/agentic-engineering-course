# Studio 09: Build Your Eval

```text
   questions.jsonl              Harbor: 5 trials per question          one judge call per trial
  +--------------------+     +------------------------------+     +----------------------------+
  | 10 questions, each | --> | your Studio 06 system runs   | --> | rubric scores, 0 to 1      |
  | with a known answer|     | as an installed agent        |     | pass or fail against the   |
  | and a pass rule    |     | and writes /app/answer.md    |     | answer key                 |
  +--------------------+     +------------------------------+     +----------------------------+
                                           |                                    |
                                           v                                    v
                               eval/job/<trial>/result.json           eval/results.json: pass@1, pass^5
```

The syllabus: "Design an evaluation harness for your multi-agent system. Define 20+ test cases. Measure pass@1 and pass^5. Implement LLM-as-Judge scoring." This studio asks for 10 questions.

Evaluate the deep research system your team built in Studio 06. Write 10 research questions, each with one known answer. Run each question five times in Harbor. Harbor is an open-source framework that runs an agent on a task inside a Docker sandbox. It calls each run a trial. Grade every trial with one call to a large language model (LLM) judge, a model that scores the answer against your key. Then report pass@1, the share of trials that pass, and pass^5, the share of questions whose five trials all pass. The questions, the answers and your agent file are yours. The judge and its rubric are fixed.

Teams of up to 3, the same teams as Studio 06. The due date is in the CourseWorks assignment.

## Setup

- Harbor 0.25.0: `uv tool install --python 3.12 harbor==0.25.0`. Harbor runs each trial in a Docker sandbox, so you need Docker with Docker Compose. The kit's base images are built for x86 and Apple Silicon.
- Python 3.12 and `uv` for the kit's scripts.
- Your Studio 06 system and the keys it uses, plus your class OpenAI key for the judge. Keys are passed for a single run only, as environment variables: `--agent-env` for your system, `--verifier-env` for the judge.
- The starter kit, [instruction/code/](code/README.md). It holds:
  - the task template with the judge and its rubric.
  - `make_tasks.py`, which turns your questions into Harbor tasks.
  - `agent_template.py`, the file you copy to `agent.py`.
  - `metrics.py`, which computes pass@1 and pass^5.
  - an example agent for checking your setup.
  - two sample questions with verified answers.

## The four checkpoints and the explanation

Every team meets the same four checkpoints and writes the explanation. Each line below is one line of the [grading rubric](GRADING_RUBRIC.md), and each names the file that shows it. Each checkpoint is worth 2 points, 1 for each line, and the explanation is worth 2, for 10 points in all. Nothing else is graded.

### Checkpoint 1: Evaluation harness

- `agent.py` runs your own Studio 06 system in Harbor as a `BaseInstalledAgent`. An installed agent is a class that installs and runs your system inside each trial's sandbox. In `agent.py`, `README.md` and one trial's `result.json` in `eval/job/`.
- The grader check passes on one of your questions: the oracle trial scores 1 and the wrong-answer trial scores 0. Harbor's oracle agent copies your key's answer. The kit's wrong-answer agent writes a wrong one. In `eval/oracle/pass/` and `eval/oracle/fail/`.

### Checkpoint 2: Questions

- `questions.jsonl` has 10 questions of your own, each with `id`, `question`, `answer`, `pass_rule`, at least one source URL and `written_on`.
- Every question in `questions.jsonl` has one known answer that its pass rule checks: names, numbers or dates. No two questions share an answer.

### Checkpoint 3: pass@1 and pass^5

- `eval/job/` records 5 trials of every question, run by your agent with the model named in `eval/results.json`, each trial with its `result.json` and `verifier/judge.json`.
- `eval/results.json` lists every question's 5 runs with `pass` equal to the trial's reward, and its `pass_1` and `pass_5` match those runs. The reward is the 1 or 0 the judge writes for a trial.

### Checkpoint 4: LLM judge

- Every trial's `judge.json` records the kit's judge model (`gpt-5.5`), the course rubric's hash, five scores from 0 to 1 and a reason. Its verdict equals the trial's reward.
- You labeled at least 10 trials by hand, pass or fail, and `eval/hand-labels.jsonl` records each label beside the judge's verdict, with the agreement rate.

### Explanation

- In `EXPLANATION.md`, answer the four questions below.
  1. Harness: how did you connect your system to Harbor?
  2. Questions: how did you choose the questions and their answers?
  3. Reliability: what do pass@1 and pass^5 say about your system?
  4. Judge: how well did the judge's verdicts match yours, and why?

## How to record the evidence

The kit's [README](code/README.md) gives every command with its purpose. In this order:

1. Copy the submission template into your team folder, then the kit's files. Install Harbor 0.25.0 and the kit's Python dependency. Read your keys into the shell without echoing them.
2. Write `questions.jsonl`, 10 questions with ids `q01` to `q10`. Build the tasks: `python make_tasks.py questions.jsonl --output tasks --team "$TEAM"`. The question goes into each task's `instruction.md`. The key goes into `tests/answer.json`, which the agent never sees.
3. Run the grader check on the tasks: the oracle (`-a oracle`) and the wrong-answer agent (`-a example_agent.wrong:WrongAnswerAgent`), one attempt each. Copy one question's two trial folders into `eval/oracle/pass/` and `eval/oracle/fail/`.
4. Copy `agent_template.py` to `agent.py` and fill in `install()` and `run()` for your system. Pass each key your system reads with `--agent-env`, under the name your system reads it by.
5. Run your system five times per question: `harbor run -p tasks -a agent:TeamAgent -m "$MODEL" -e docker -k 5 -n 2 -r 0 -o jobs --job-name studio06-eval`, with the `--agent-env` and `--verifier-env` flags from the README.
6. Compute the report: `python metrics.py jobs/studio06-eval --questions questions.jsonl --output eval/results.json --team "$TEAM"`.
7. Copy the job into `eval/job/` with the README's copy commands. They keep the job's `result.json` and `config.json`, and every trial's `result.json` and `verifier/` folder. They drop each trial's `artifacts/` and agent logs, which hold prompts, answers and traces.
8. Read 10 trials' answers yourself, from `jobs/studio06-eval/<trial>/artifacts/app/answer.md`. Label each one pass or fail against your key, and write `eval/hand-labels.jsonl`.

The two sample questions in `questions.example.jsonl` show the form and let you check your setup. They do not count among your 10.

## File formats

`questions.jsonl` has one question per line:

```json
{"id": "q01", "question": "…", "answer": "…", "pass_rule": "…", "sources": ["https://…"], "written_on": "2026-11-09"}
```

`eval/oracle/pass/` and `eval/oracle/fail/` each hold one trial folder with its `result.json` and `verifier/` folder.

`eval/job/<trial>/` holds each trial's `result.json` and `verifier/` folder, with `reward.txt` (`1` or `0`) and `judge.json`. One `judge.json`, shortened:

```json
{"status": "ok", "question_id": "q03", "pass": false, "scores": {"factual_accuracy": 0.6, "citation_accuracy": 0.5, "completeness": 0.4, "source_quality": 0.7, "tool_efficiency": 0.5}, "reason": "…", "unscored": ["tool_efficiency"], "model": "gpt-5.5", "rubric_sha256": "…", "prompt_hash": "…"}
```

`eval/results.json` comes from `metrics.py`. Its fields:
- `setup`: team, agent, model, judge model, job id.
- `runs_per_question`: 5.
- `questions`: each with its `id` and five `runs`, each run with `trial_id`, `pass`, `scores`, `reason` and `unscored`.
- `pass_1`: passed runs divided by all runs.
- `pass_5`: questions whose five runs all pass, divided by all questions.

`eval/hand-labels.jsonl` has one trial per line, then one last line with the agreement over those trials:

```json
{"trial": "q03__abc123", "question": "q03", "hand_pass": true, "judge_pass": false}
{"agreement": 0.8, "n": 10}
```

## Submit

Commit and push to your team's own private repository (the one `bootstrap.sh` created) before the due date in CourseWorks. Each member submits the same team pull-request link through CourseWorks. Nothing is collected from the public course repository. A grading agent reads your private repository at the commit you submit. It does not run your code. The [submission guide](../submission/README.md) shows the folder.

## Rules

- Evaluate your own Studio 06 system. The example agent in the kit is for checking your setup, not for submission.
- Class keys only, passed for one run as environment variables. Never commit a key or a `.env` file.
- Keep the judge, its prompt and the rubric as the kit gives them, so every team's scores mean the same thing.
- Every member must be able to explain the code and the numbers behind every checkpoint (merge defense).

## Optional, not graded

- Run your single-agent mode on the same questions and compare pass^5.
- Try a second judge model on the same trials and compare the verdicts.

## Read

- Anthropic, [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system), "Effective evaluation of agents"
- Harbor docs: [Core concepts](https://docs.harborframework.com/core-concepts), [Custom agents](https://docs.harborframework.com/agents/custom-agents), [Run a job](https://docs.harborframework.com/jobs/run-a-job)
- Lecture 09: 3.2.4 Grader validation, 4.2 pass^k and pass@k, 5.2.4 Build a multi-agent eval
