# Studio 06: Wide Research

Build a deep research agent with at least five research sub-agents searching in parallel. Use any architecture, framework, language, or SDK.

Run a single-agent version and a multi-agent version on the [three selected tasks](TASKS.md). Produce one report per task in each mode: six reports in total. Repeated runs are optional.

**Total: 10 points. Due date: to be announced on CourseWorks.**

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

The benchmark computes weighted totals for your report, `T`, and the reference, `R`. Its overall score is `T / (T + R)`. Higher is better. A score of `0.5` means equal weighted totals. For example, `7 / (7 + 8) = 0.4667`.

The benchmark score describes report quality. The course awards the 2 comparison points for running and comparing the results.

## What do you submit?

Put these files in your team's [submission folder](../submission/README.md):

- Your implementation and a short command that starts each mode.
- `EVIDENCE.md`: a compact run excerpt showing five or more active research sub-agents, their overlapping times, and their searches.
- `reports/single/99.md`, `93.md`, and `100.md`.
- `reports/multi/99.md`, `93.md`, and `100.md`.
- The evaluator's score files and generated `comparison.csv`.
- `EXPLANATION.md`: what you built, why you chose it, and what the single/multi comparison shows.

Use native run events or a short table for `EVIDENCE.md`. Include worker identifiers and start/end times so a reader can see the overlap. Include search activity from those workers. Five workers listed in source code alone do not show that they ran.

A grading agent reads the files at your submitted commit. It does not run your code. See the [two-row rubric](GRADING_RUBRIC.md).

## Submit to your team's private repository

Commit and push your work to the private repository created by `bootstrap.sh`. Each member submits the same team pull-request link through CourseWorks when the assignment is available.

Never commit API keys, credential files, or full raw session logs. Every member should be able to explain the implementation and results.
