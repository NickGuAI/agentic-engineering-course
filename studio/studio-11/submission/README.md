# Studio 11 Submission

Work from the course repository root in your team's private repository. Choose a team slug of letters, digits, `-` and `_`. Copy the template folder once:

```bash
TEAM='your-team'
mkdir -p "studio/studio-11/submission/$TEAM"
cp -R studio/studio-11/submission/_template/. "studio/studio-11/submission/$TEAM/"
```

Edit your copy, never the template. Put all your evidence in this folder:

```text
studio/studio-11/submission/<team>/
├── EXPLANATION.md            from the template
├── method.md                 your rule for time with AI, reviewing and fixing
├── tasks.csv                 one row per task: commit, trace, times, tokens
├── claims.csv                one row per task: the agent's claim beside the records
├── failures.md               first failures and their codes
├── results.md                true time ratio, success rates, retest counts, what the traces could not show
├── traces/
│   ├── secret-scan.json      the last gitleaks report: an empty list
│   ├── t01.jsonl.gz          each task's full session log, cleaned and compressed
│   └── …
├── records/                  pull request exports and other records your rule and claims cite
├── retest/
│   ├── change.md             the one change, and the code it addresses
│   ├── cases/                one file per case: prompt, starting commit, check
│   ├── traces/               each run's session log, cleaned and compressed
│   ├── checks/               each run's check output
│   └── results.csv           one row per run
└── work/                     raw and cleaned logs, ignored by Git
```

Commit and push to your team's private repository (the one `bootstrap.sh` created) before the due date in CourseWorks. Each member submits the same team pull-request link through CourseWorks. The grading agent reads the commit you submit. Never commit `work/`, an uncompressed log, an API key or a `.env` file.
