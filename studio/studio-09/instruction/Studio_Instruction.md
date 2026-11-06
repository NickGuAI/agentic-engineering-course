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

Evaluate the deep research system your team built in Studio 06. Write 10 research questions that each have one known answer, run every question five times in Harbor, grade every run with one LLM judge call, and report pass@1 and pass^5. The questions, the answers and the harness are yours. The judge and its rubric are fixed.

Teams of up to 3, the same teams as Studio 06. Due Friday, November 13, 2026, 13:10 ET, before class.

## Setup

- Harbor 0.25.0: `uv tool install --python 3.12 harbor==0.25.0`. Harbor runs each trial in a Docker sandbox, so you need Docker with Docker Compose. The kit's image works on x86 and Apple Silicon.
- Python 3.12 and `uv` for the kit's scripts.
- Your Studio 06 system, installable in a fresh sandbox with one command, and the keys it uses. Your class OpenAI key for the judge. Keys are passed for a single run only, as environment variables: `--agent-env` for your system, `--verifier-env` for the judge.
- The starter kit, [instruction/code/](code/README.md): the task template with the judge, `make_tasks.py`, `agent_template.py`, `metrics.py`, an example agent for checking your setup, and two sample questions with verified answers.

## The four checkpoints and the explanation

Every team meets the same four checkpoints and writes the explanation. Each line below is one line of the [grading rubric](GRADING_RUBRIC.md), and each names the file that shows it. Each checkpoint is worth 2 points, 1 for each line, and the explanation is worth 2, for 10 points in all. Nothing else is graded.

### Checkpoint 1: Harness

- Your Studio 06 system runs in Harbor as an installed agent: `agent.py` extends `BaseInstalledAgent`, its `install()` and `run()` install and run your own system, and the system writes its answer to `/app/answer.md`. In `agent.py`, `README.md` and one trial's `result.json`.
- The grader check passes on one of your questions: the oracle trial scores 1 and the wrong-answer trial scores 0. In `eval/oracle/pass/` and `eval/oracle/fail/`.

### Checkpoint 2: Questions

- `questions.jsonl` has 10 questions, each with `id`, `question`, `answer`, `pass_rule`, at least one source URL and `written_on`.
- Every question has one answer that its pass rule decides from the answer text: names, numbers or dates, never an opinion, a summary or a recommendation. No two questions share an answer.

### Checkpoint 3: pass@1 and pass^5

- `eval/job/` records 5 trials of every question, run by your agent with the model named in `eval/results.json`, each trial with its `result.json` and `judge.json`.
- `eval/results.json` lists every question's 5 runs with `pass` equal to the trial's reward, and its `pass_1` and `pass_5` match those runs.

### Checkpoint 4: LLM judge

- Every trial's `judge.json` comes from one judge call with the course rubric: it names the judge model, carries the course rubric's hash, the five criterion scores in 0 to 1, a pass or fail and a reason, and its pass equals the trial's reward.
- You labeled at least 10 trials by hand, pass or fail, and `eval/hand-labels.jsonl` records each label beside the judge's verdict, with the agreement rate.

### Explanation

- In `EXPLANATION.md`, answer the four questions below.
  1. Harness: how did you connect your system to Harbor?
  2. Questions: how did you choose the questions and their answers?
  3. Reliability: what do pass@1 and pass^5 say about your system?
  4. Judge: where did the judge disagree with you, and why?

## How to record the evidence

The kit's [README](code/README.md) has every command with its purpose. In order:

1. Copy the kit into your submission folder, install Harbor 0.25.0 and the kit's Python dependency, and read your keys into the shell without echoing them.
2. Write `questions.jsonl` (10 questions, `q01` to `q10`) and build the tasks: `python make_tasks.py questions.jsonl --output tasks --team "$TEAM"`. The question goes into each task's `instruction.md`; the key goes into `tests/answer.json`, which the agent never sees.
3. Run the grader check on the tasks: the oracle (`-a oracle`) and the wrong-answer agent (`-a example_agent.wrong:WrongAnswerAgent`), one attempt each. Copy one question's two trials into `eval/oracle/pass/` and `eval/oracle/fail/`.
4. Fill in `agent.py` from `agent_template.py`, then run your system five times per question: `harbor run -p tasks -a agent:TeamAgent -m "$MODEL" -e docker -k 5 -n 2 -r 0 -o jobs --job-name studio06-eval` with the `--agent-env` and `--verifier-env` flags the README shows.
5. Compute the report: `python metrics.py jobs/studio06-eval --questions questions.jsonl --output eval/results.json --team "$TEAM"`.
6. Copy the job into `eval/job/`: the job's `result.json` and `config.json`, and for every trial its `result.json` and `verifier/` folder (`reward.txt`, `judge.json`). Leave out `artifacts/` and the agent logs; they hold prompts, answers and traces.
7. Read 10 trials' answers yourself, label each pass or fail against your key, and write `eval/hand-labels.jsonl`.

The two sample questions in `questions.example.jsonl` show the form and let you check your setup. Your 10 questions are your own.

## File formats

`questions.jsonl` has one question per line:

```json
{"id": "q01", "question": "…", "answer": "…", "pass_rule": "…", "sources": ["https://…"], "written_on": "2026-11-09"}
```

`eval/results.json` comes from `metrics.py`: `setup` (team, agent, model, judge model, job id), `runs_per_question` (5), `questions` (each with its `id` and five `runs`, each run with `trial_id`, `pass`, `scores`, `reason` and `unscored`), `pass_1` (passed runs divided by all runs) and `pass_5` (questions whose five runs all pass, divided by all questions). The README shows an example.

Each trial's `verifier/judge.json` has `status`, `question_id`, `pass`, `scores` (the five criteria, 0 to 1), `reason`, `unscored`, `model`, `rubric_sha256` and `prompt_hash`.

`eval/hand-labels.jsonl` has one trial per line, then one last line with the agreement:

```json
{"trial": "q03__abc123", "question": "q03", "hand_pass": true, "judge_pass": false}
{"agreement": 0.8, "n": 10}
```

## Submit

Copy the template folder once, as the [submission guide](../submission/README.md) shows, then commit and push to your team's own private repository before the deadline. Nothing is collected from the public course repository. A grading agent reads your private repository at the commit you submit. It does not run your code.

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
- Harbor docs: [Core concepts](https://harborframework.com/docs/core-concepts), [Custom agents](https://harborframework.com/docs/agents/custom-agents), [Run a job](https://harborframework.com/docs/jobs/run-a-job)
- Lecture 09, sections 3.2.4, 4.2 and 5.2.4
