# Studio 09 Grading Rubric

**Total:** 10 points: 2 for each of the four checkpoints and 2 for the explanation. Lines 1.1 to 4.2 are worth 1 point each. Every line is either met or not met.

| Line | Points | Condition for credit | Read from |
|---|---|---|---|
| 1.1 | 1 | Your Studio 06 system runs in Harbor as an installed agent: `agent.py` extends `BaseInstalledAgent`, its `install()` and `run()` install and run your own system, and the system writes its answer to `/app/answer.md`. | `agent.py`, `README.md`, one trial's `result.json` |
| 1.2 | 1 | The grader check passes on one of your questions: the oracle trial scores 1 and the wrong-answer trial scores 0. | `eval/oracle/pass/`, `eval/oracle/fail/` |
| 2.1 | 1 | `questions.jsonl` has 10 questions, each with `id`, `question`, `answer`, `pass_rule`, at least one source URL and `written_on`. | `questions.jsonl` |
| 2.2 | 1 | Every question has one answer that its pass rule decides from the answer text: names, numbers or dates, never an opinion, a summary or a recommendation. No two questions share an answer. | `questions.jsonl` |
| 3.1 | 1 | `eval/job/` records 5 trials of every question, run by your agent with the model named in `eval/results.json`, each trial with its `result.json` and `judge.json`. | `eval/job/`, `eval/results.json` |
| 3.2 | 1 | `eval/results.json` lists every question's 5 runs with `pass` equal to the trial's reward, and its `pass_1` and `pass_5` match those runs. | `eval/results.json`, `eval/job/` |
| 4.1 | 1 | Every trial's `judge.json` comes from one judge call with the course rubric: it names the judge model, carries the course rubric's hash, the five criterion scores in 0 to 1, a pass or fail and a reason, and its pass equals the trial's reward. | `eval/job/*/judge.json` |
| 4.2 | 1 | You labeled at least 10 trials by hand, pass or fail, and `eval/hand-labels.jsonl` records each label beside the judge's verdict, with the agreement rate. | `eval/hand-labels.jsonl` |
| 5 | 2 | `EXPLANATION.md` answers the four questions. | `EXPLANATION.md` |

All files are in `studio/studio-09/submission/<team>/` in your team's private repository, at the commit you submit.

- A grading agent reads your repository at that commit and checks each line. It does not run your code. A line the files cannot settle goes to a TA.
- A late or missing file scores 0 for its lines.
- How high pass@1 or pass^5 is does not affect the grade.
- Every member must be able to explain the code and the numbers behind every line (merge defense).
