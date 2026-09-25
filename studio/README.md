# Studio README

## Studio 01: Agent Execution & Delegation

Welcome to your first studio repository. Our workspace structure includes:
* [studio-01/instruction/Studio01.md](studio-01/instruction/Studio01.md) (exercise)
* [studio-01/instruction/README.md](studio-01/instruction/README.md) (workspace and PR workflow used for Studio 01)
* [studio-01/instruction/delegation-card.md](studio-01/instruction/delegation-card.md) (template)
* [studio-01/instruction/code/](studio-01/instruction/code/) (offline demo and tests)

During this project, you will draft a bounded delegation card, execute a baseline run to record a complete trace, adjust a single parameter or condition to evaluate the impact, and note whether the human user chooses to accept or defer.

To run the offline fallback fixture:
```bash
python3 studio/studio-01/instruction/code/harness_demo.py --output /tmp/agentic-first-run.jsonl
(cd studio/studio-01/instruction/code && python3 -m unittest -v test_harness)
```

These scripts run purely within a local offline context, requiring no external network requests, active model connections, or package installations. Any erroneous configuration or installation command in the fixture's internal README is intended purely as mock test data, not as a step to execute. This self-contained setup is designed to show how traces are preserved and how validation state is verified, rather than to demonstrate the raw capability of any particular language model. Class sessions will cover options for running the live integration, meaning no paid API configurations are required before you begin.

## Studio 02: Context Window Stress Test & Memory Architecture

In this studio, the team will push a coding agent past its useful context length and watch it degrade. You will fix it with context isolation and targeted summarization. Finally, you will give the agent persistent file-based memory across three sessions and compare it against a memoryless baseline.

* [studio-02/instruction/Studio_Instruction.md](studio-02/instruction/Studio_Instruction.md) (what to do)
* [studio-02/instruction/GRADING_RUBRIC.md](studio-02/instruction/GRADING_RUBRIC.md) (how it's graded)
* [studio-02/instruction/code/](studio-02/instruction/code/) (the scripts)
* [studio-02/instruction/reference-evidence/](studio-02/instruction/reference-evidence/) (reference evidence)
* [studio-02/submission/](studio-02/submission/) (where your team's work goes)

Unlike Studio 01, Studio 02 has no offline mock fixture and requires a working model connection — either a ChatGPT Plus/Pro subscription login or an API key — to run.

## Studio 03: Agent Loops and Controlled Comparison

Build a minimal OpenAI Responses loop and save a direct/ReAct run, then compare it with a plan-first run on the same research question. Students run the assignment on their laptops in their team’s private course repository.

* [studio-03/README.md](studio-03/README.md) (overview)
* [studio-03/instruction/Studio_Instruction.md](studio-03/instruction/Studio_Instruction.md) (assignment and evidence requirements)
* [studio-03/instruction/code/](studio-03/instruction/code/) (starter, runner, support, and fixed question)
* [studio-03/submission/](studio-03/submission/) (team submissions and explanation template)
