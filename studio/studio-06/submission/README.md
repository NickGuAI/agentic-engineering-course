# Studio 06 Submission

From your team's private repository root, copy the template once:

```bash
TEAM='your-team'
cp -R studio/studio-06/submission/_template "studio/studio-06/submission/$TEAM"
cd "studio/studio-06/submission/$TEAM"
mkdir -p reports/single reports/multi eval work
```

Keep your implementation, six reports, original RACE outputs, `README.md`, and `EXPLANATION.md` in this folder. This example layout matches the evaluation helper:

```text
studio/studio-06/submission/<team>/
├── README.md                 Setup and run commands
├── EXPLANATION.md            What you built, why, and the comparison
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
│   └── comparison.csv         Optional generated comparison table
└── work/                     Ignored local checkout and virtual environment
```

The [evaluation procedure](../instruction/EVALUATION.md) creates the `eval/race-01/` files. Your own report locations are fine. Map them to the helper's paths or prepare native JSONL yourself.

Include parallel-run evidence in `EXPLANATION.md` or link to an excerpt in another file. There is no fixed evidence-file format.

Complete `EXPLANATION.md` from the template. `EVIDENCE.md` is an optional example for a separate run excerpt. `comparison.csv` is convenient output, not a required graded file.

Commit the six reports and original evaluation results with your code. Keep full raw session logs and credentials out of Git.

Push to your team's private repository. Each member submits the same team pull-request link through CourseWorks by Friday, October 23, 2026, 13:10 ET, before class.

Due Friday, October 23, 2026, 13:10 ET, before class.
