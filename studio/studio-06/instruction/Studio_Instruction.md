# Studio 06: Wide Research

Build a deep research agent with at least five research sub-agents searching in parallel. Use any architecture, framework, language, or SDK.

Run a single-agent version and a multi-agent version on the [three selected tasks](TASKS.md). Produce one report per task in each mode: six reports in total. Repeated runs are optional.

**Total: 10 points. Due Friday, October 23, 2026, 13:10 ET, before class.**

## What earns the 10 points?

- **Implementation — 8 points:** Your deep research agent actually runs at least five research sub-agents searching in parallel.
- **Comparison — 2 points:** Run both modes on all three tasks, score the six reports with RACE, and compare the results.

There are no additional checkpoints or explanation points. There is no minimum RACE score or class ranking.

## What should you run?

Use these exact [task prompts](TASKS.md):

| Task | Domain | Research topic |
|---|---|---|
| 99 | Fashion & Beauty | Light-based therapies in aesthetic medicine |
| 93 | Software | The global video-editing and creation software market |
| 100 | Social Life | AI interaction and interpersonal relations |

In single-agent mode, one agent does the research without delegating to sub-agents. In multi-agent mode, your research sub-agents work in parallel.

For a useful comparison, use the same model and search tools in both modes. Record any differences in your comparison.

Use the class-provided API keys. Keep keys in environment variables.

## How do you evaluate the reports?

Follow the [evaluation procedure](EVALUATION.md). It uses the original DeepResearchBench RACE evaluator, criteria, reference reports, and weights.

RACE grades each report against its reference on comprehensiveness, insight, instruction following, and readability. Each criterion receives a score from 0 to 10.

The benchmark applies its original weights to compare your report with its reference. See the [score explanation](EVALUATION.md#4-read-the-six-scores).

The benchmark score describes report quality. The course awards the 2 comparison points for running and comparing the results.

## What do you submit?

Put these files in your team's [submission folder](../submission/README.md):

- Your implementation.
- Six reports and their original RACE outputs.
- `README.md`: setup and run commands.
- `EXPLANATION.md`: answer the questions below and link to your run evidence and results.

Show the parallel research run in `EXPLANATION.md` or link to a compact excerpt elsewhere. Choose the format that fits your framework.

The evaluation helper uses example report paths. You can map your reports to those paths or prepare the evaluator's JSONL yourself.

`comparison.csv` and the separate evidence template are optional conveniences. They are not independent graded files.

A grading agent reads the files at your submitted commit. It does not run your code. See the [two-row rubric](GRADING_RUBRIC.md).

## Explanation

In `EXPLANATION.md`, answer these questions:

1. What did you build?
2. Why did you choose these agent roles and this architecture?
3. How did the single-agent and multi-agent results compare?

## Submit to your team's private repository

Commit and push your work to the private repository created by `bootstrap.sh`. Each member submits the same team pull-request link through CourseWorks by Friday, October 23, 2026, 13:10 ET, before class.

Never commit API keys, credential files, or full raw session logs. Every member should be able to explain the implementation and results.
