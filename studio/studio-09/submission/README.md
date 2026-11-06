# Studio 09 Submission

From the course repository root in your team's private repository, choose your team slug and copy the template folder once:

```bash
TEAM='your-team'
cp -R studio/studio-09/submission/_template "studio/studio-09/submission/$TEAM"
cd "studio/studio-09/submission/$TEAM"
mkdir -p eval
```

Edit your copy, never the template. Put your agent file, your questions and all your evidence in this folder:

```text
studio/studio-09/submission/<team>/
├── README.md                 how to install and run your system, and the exact harbor commands you ran
├── EXPLANATION.md            from the template
├── agent.py                  your BaseInstalledAgent subclass
├── questions.jsonl           your 10 questions, answers, pass rules and sources
└── eval/
    ├── oracle/
    │   ├── pass/             the oracle trial on one question [KIT: files]
    │   └── fail/             the wrong-answer trial on the same question [KIT: files]
    ├── job/                  the five-attempt job [KIT: config and per-trial result.json and judge.json]
    ├── results.json          from metrics.py: pass_1, pass_5 and every run
    └── hand-labels.jsonl     your hand labels beside the judge's verdicts
```

Commit and push to your team's private repository before the deadline. The grading agent reads the commit you submit. Do not commit API keys, `.env` files or full trajectories. [KIT: what to leave out of eval/job/.]
