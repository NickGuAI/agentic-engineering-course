# Studio 09: Build Your Eval

```text
  +--------------------+     +------------------------------+     +---------------------------+
  | 10 questions with  | --> | your Studio 06 system,       | --> | one judge call per trial: |
  | a known answer     |     | 5 trials each in Harbor      |     | pass or fail, rubric 0-1  |
  +--------------------+     +------------------------------+     +---------------------------+
                                                                              |
                                                                              v
                                                                     pass@1 and pass^5
```

Evaluate the deep research system you built in Studio 06. Write 10 research questions that each have one known answer, run every question five times in Harbor, grade every run with one LLM judge call, and report pass@1 and pass^5. The questions, the answers and the harness are yours; the judge and its rubric are fixed. You are graded on four checkpoints and your explanation, 10 points in all.

- [Assignment instructions](instruction/Studio_Instruction.md)
- [Grading rubric](instruction/GRADING_RUBRIC.md)
- [Starter kit: task template, judge, scripts](instruction/code/README.md)
- [Submission folder and explanation template](submission/README.md)
