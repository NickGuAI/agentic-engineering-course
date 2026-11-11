# Studio 10 Submission

Work from the course repository root in your team's private repository. Choose a team slug of letters, digits, `-` and `_`. Copy the template folder once. Then copy the kit's files, as the [kit README](../instruction/code/README.md) shows:

```bash
TEAM='your-team'
mkdir -p "studio/studio-10/submission/$TEAM"
cp -R studio/studio-10/submission/_template/. "studio/studio-10/submission/$TEAM/"
```

Edit your copy, never the template. Put your attacks, your defense and all your evidence in this folder:

```text
studio/studio-10/submission/<team>/
├── README.md                 how to run the kit and the exact commands you ran
├── EXPLANATION.md            from the template
├── attacks/
│   ├── injection.json        your injection attack
│   ├── exfiltration.json     your exfiltration attack
│   └── unauthorized.json     your unauthorized-action attack
├── defense/
│   └── defense.py            your one defense, from defense_template.py
└── eval/
    ├── baseline/             stock attacks on warmup and luna (not graded)
    ├── luna/results.json     your three attacks on luna, 5 runs each
    ├── ladder/results.json   your attacks across 54mini, 55, sol (and optional terra)
    └── defense/results.json  before and after your defense, with task completion
```

Commit and push to your team's private repository (the one `bootstrap.sh` created) before the due date in CourseWorks. Each member submits the same team pull-request link through CourseWorks. The grading agent reads the commit you submit. Do not commit API keys or `.env` files, and do not commit full raw run logs: they hold prompts and traces.
