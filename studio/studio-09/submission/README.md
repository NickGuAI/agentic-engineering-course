# Studio 09 Submission

Work from the course repository root in your team's private repository. Choose a team slug of letters, digits, `-` and `_`. Copy the template folder once. Then copy the kit's files, as the [kit README](../instruction/code/README.md) shows:

```bash
TEAM='your-team'
mkdir -p "studio/studio-09/submission/$TEAM"
cp -R studio/studio-09/submission/_template/. "studio/studio-09/submission/$TEAM/"
```

Edit your copy, never the template. Put your agent file, your questions and all your evidence in this folder:

```text
studio/studio-09/submission/<team>/
├── README.md                 how to install and run your system, and the exact harbor commands you ran
├── EXPLANATION.md            from the template
├── agent.py                  your BaseInstalledAgent subclass, from agent_template.py
├── questions.jsonl           your 10 questions, answers, pass rules and sources
└── eval/
    ├── oracle/
    │   ├── pass/<trial>/     the oracle trial on one question: its result.json and verifier/
    │   └── fail/<trial>/     the wrong-answer trial on the same question: its result.json and verifier/
    ├── job/                  the five-attempt job: its result.json and config.json, and each trial's result.json and verifier/
    ├── results.json          from metrics.py: pass_1, pass_5 and every run
    └── hand-labels.jsonl     your hand labels beside the judge's verdicts
```

Commit and push to your team's private repository (the one `bootstrap.sh` created) before the due date in CourseWorks. Each member submits the same team pull-request link through CourseWorks. The grading agent reads the commit you submit. Do not commit API keys, `.env` files, or the job's `artifacts/` and agent logs: they hold prompts, answers and traces.
