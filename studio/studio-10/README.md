# Studio 10: Red Team Day

```text
  +--------------------+     +----------------------------+     +---------------------------+
  | your three attacks |     | the course target agent    |     | AgentDojo checks each run |
  | injection,         | --> | a tool-using agent on a    | --> | cracked = the injected    |
  | exfiltration,      |     | class model in a poisoned  |     | goal happened in at least |
  | unauthorized       |     | AgentDojo Slack workspace  |     | 1 of 5 runs (pass@5)      |
  +--------------------+     +----------------------------+     +---------------------------+
                                          |                                   |
                                          v                                   v
                              climb the model ladder               add one defense and
                              luna -> 5.4-mini -> 5.5 -> sol        measure what it costs
```

Attack a target agent the course gives you, not your own system. Write one injection, one
exfiltration and one unauthorized-action attack against an AgentDojo Slack agent, crack it, then
climb a ladder of stronger models. Add one defense and measure what it costs in ordinary work. The
attacks and the defense are yours; the suite, the target and the checks are fixed. You are graded on
three checkpoints and your explanation, 10 points in all.

- [Assignment instructions](instruction/Studio_Instruction.md)
- [Grading rubric](instruction/GRADING_RUBRIC.md)
- [Starter kit: target harness, attack and defense templates, scripts](instruction/code/README.md)
- [Submission folder and explanation template](submission/README.md)
