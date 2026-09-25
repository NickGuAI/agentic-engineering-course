# Studio 03 Submission

From the course repository root, choose your team slug and copy the complete template folder once:

```bash
TEAM='your-team'
cp -R studio/studio-03/submission/_template "studio/studio-03/submission/$TEAM"
cd "studio/studio-03/submission/$TEAM"
```

This creates `agent.py` and `EXPLANATION.md`. Edit these copies; leave the template unchanged. With the code environment activated and both API keys set, fill the TODOs in `agent.py` and run both modes:

```bash
python agent.py --mode react
python agent.py --mode plan
```

For a human-authored numbered plan, save `human-plan.md` in your current team folder and pass that file in plan mode. This input file is separate from the generated evidence file `evidence/plan/<run_id>/plan.md`.

```bash
python agent.py --mode plan --plan-file human-plan.md
```

Each run creates a unique evidence directory:

```text
submission/<team>/
├── agent.py
├── EXPLANATION.md
└── evidence/
    ├── react/<run_id>/{trace.jsonl,plan.md,report.md,summary.json}
    └── plan/<run_id>/{trace.jsonl,plan.md,report.md,summary.json}
```

Keep both runs, including failures, and refer to their run IDs in your explanation. The structured, redacted course traces are required assignment evidence. Do not submit API keys or raw provider/session logs. Push your completed work to your team's private course repository and follow the existing CourseWorks submission instructions.
