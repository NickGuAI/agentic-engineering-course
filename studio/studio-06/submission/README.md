# Studio 06 Submission

From your team's private repository root, copy the template once:

```bash
TEAM='your-team'
cp -R studio/studio-06/submission/_template "studio/studio-06/submission/$TEAM"
cd "studio/studio-06/submission/$TEAM"
mkdir -p reports/single reports/multi eval work
```

Put your work in this folder:

```text
studio/studio-06/submission/<team>/
├── README.md                 How to run each mode
├── EXPLANATION.md            Design and comparison
├── EVIDENCE.md               Parallel workers and their searches
├── <your implementation>
├── reports/
│   ├── single/{99,93,100}.md
│   └── multi/{99,93,100}.md
├── eval/race-01/
│   ├── input/{single,multi}.jsonl
│   ├── cleaned/{single,multi}.jsonl
│   ├── single/{raw_results.jsonl,race_result.txt,evaluator.log}
│   ├── multi/{raw_results.jsonl,race_result.txt,evaluator.log}
│   ├── evaluation.json
│   ├── queries.jsonl
│   └── comparison.csv
└── work/                     Ignored local checkout and virtual environment
```

The [evaluation procedure](../instruction/EVALUATION.md) creates the `eval/race-01/` files. Commit the six reports and evaluation results with your code. Keep full raw session logs and credentials out of Git.

Push to your team's private repository. Each member submits the same team pull-request link through CourseWorks when the assignment is available.

Due date: to be announced on CourseWorks.
