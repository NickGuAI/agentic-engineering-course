# Studio 03: ReAct and Plan-and-Execute

```text
                  +--------------------+
                  | Same question      |
                  +---------+----------+
                            |
              +-------------+--------------+
              |                            |
              v                            v
     +-------------------+        +-------------------+
     | ReAct: same loop  |        | Tools-off plan    |
     +---------+---------+        +---------+---------+
               |                            v
               |                  +-------------------+
               |                  | Same loop + plan  |
               |                  +---------+---------+
               |                            |
               +--------------+-------------+
                              v
                   +---------------------+
                   | Reports and traces |
                   +---------------------+
```

Build one minimal OpenAI Responses loop, then compare a direct/ReAct run with a plan-first run on the same research question. You will write the loop and its Bash tool, which calls the official Tavily CLI. This is a laptop assignment; it does not use a hosted in-lecture sandbox.

- [Assignment instructions](instruction/Studio_Instruction.md)
- [Code setup and Tavily CLI guide](instruction/code/README.md)
- [Completion checklist](instruction/GRADING_RUBRIC.md)
- [Submission folder and explanation template](submission/README.md)
