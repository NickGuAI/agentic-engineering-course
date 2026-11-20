# Studio 11 Grading Rubric

**Total:** 10 points: 2 for each of the four checkpoints and 2 for the explanation. Every line is either met or not met.

| Line | Points | Condition for credit | Read from |
|---|---|---|---|
| 1 | 2 | `tasks.csv` lists at least 10 tasks from your team's project, each with its commit and its full cleaned trace in `traces/`. Each task's three times follow from its trace and `records/` by the rule in `method.md`. `results.md` gives the true time ratio. | `tasks.csv`, `method.md`, `traces/`, `records/`, `results.md` |
| 2 | 2 | `claims.csv` quotes the agent's last message on each task, with its line in the trace, beside what the records show about the result. `results.md` gives the claimed and the verified success rates. | `claims.csv`, `method.md`, `traces/`, `records/`, `results.md` |
| 3 | 2 | `failures.md` gives every failed or fixed task its first failure: a line in its trace and a code. For each code, it gives the count, the layer (spec, harness, model, tool or environment), the probable cause and the trace evidence. | `failures.md`, `traces/` |
| 4 | 2 | At least 3 failed tasks run again in `retest/`, before and after the one change in `retest/change.md`, each run with its trace and result. `results.md` counts the cases that improved, stayed the same and got worse, says what the traces could not show, and claims nothing beyond those cases. | `retest/`, `results.md` |
| 5 | 2 | `EXPLANATION.md` answers the four questions. | `EXPLANATION.md` |

All files are in `studio/studio-11/submission/<team>/` in your team's private repository, at the commit you submit.

- A grading agent reads your repository at that commit and checks each line. It does not run your code. A line the files cannot settle goes to a TA.
- The grading agent checks your numbers against your traces. It applies your rule to tasks it picks, follows claims and first failures to their lines, and recounts your results.
- A late or missing file scores 0 for its lines.
- Your tools and how good your AI is do not affect the grade. Neither do your success rates, your true time ratio or the time AI took or saved.
- Every member must be able to explain the method and the numbers behind every line (merge defense).
