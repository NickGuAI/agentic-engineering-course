# Grading Rubric: Studio 02

This guide is for the TAs to grade team submissions. Each team can earn up to 10 points.

## Rubric Table

| Section | Criterion | Points | Grading Standard | What to Watch For |
| :--- | :--- | :--- | :--- | :--- |
| **Completion** | Part A Evidence | 2 points | All three of the following tests must pass:<br>1. **Presence**: The run files and `part_a/summary.md` exist.<br>2. **Internal Consistency**: The numbers in `EXPLANATION.md` section 2 match the numbers in `part_a/summary.md`.<br>3. **Reproducibility**: The exact command and model used are recorded so a TA can re-run it. | Look out for numbers in `EXPLANATION.md` that do not match the evidence files. This indicates the explanation was written from memory rather than from the actual run output. |
| **Completion** | Part B Evidence | 2 points | All three of the following tests must pass:<br>1. **Presence**: The isolate findings files and `part_b/summary.md` exist.<br>2. **Internal Consistency**: The numbers in `EXPLANATION.md` section 3 match the numbers in `part_b/summary.md`.<br>3. **Reproducibility**: The exact command and model used are recorded so a TA can re-run it. | Look out for numbers in `EXPLANATION.md` that do not match the evidence files. Watch for teams reporting a score improvement in Part B without saying whether the isolate or compress operation produced it. |
| **Completion** | Part C Evidence | 2 points | All three of the following tests must pass:<br>1. **Presence**: The file `decisions.md` and both session-three answers (with memory and memoryless baseline) exist.<br>2. **Internal Consistency**: The numbers in `EXPLANATION.md` match the files.<br>3. **Reproducibility**: The exact command and model used are recorded so a TA can re-run it. | Watch out for teams that miss the memoryless baseline entirely, or treat it as optional. |
| **Explanation** | Part A Degradation Account | 1 point | The team provides a correct causal account of what degraded in Part A and specifies the input length where this degradation happened. | Watch out for vague descriptions or missing input lengths. |
| **Explanation** | Part B Fix Attribution | 1 point | The team correctly attributes the Part B improvement to the correct operation (Isolate, Compress, or both) rather than just stating that an improvement occurred. | Watch out for teams that claim improvement without identifying which operation produced it. |
| **Explanation** | Part C Baseline Reflection | 1 point | The team compares their performance against a real baseline and documents honest unknowns rather than just claiming that it worked. | Watch out for teams claiming perfect memory recall in Part C without checking their answer against the actual `decisions.md` entries. |
| **Explanation** | Individual Contribution | 1 point | Every team member writes a specific, unique paragraph describing their own contribution. | Watch out for teams that copy and paste the same contribution paragraph for every member instead of writing individual accounts. |

## Spot-Check Instructions

We follow the syllabus principle that judgment matters and students must be able to explain what they built. TAs must spot-check each team. 

Select one member of each team at random. Do not let the team choose the member. Ask them to explain one run from their evidence. For example, ask them why Part A failed where it did, or what the isolate sub-agents actually returned. 

If their answer is vague or they are clearly unprepared, you should lower the team's completion or explanation score for that section. Use your professional judgment to decide the deduction.

## Late or Missing Submissions

Follow the course syllabus policy for late submissions and missing CourseWorks links. If you do not know the exact policy, do not guess a penalty. Flag the case for Nick, and he will handle it.
