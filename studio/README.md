# Studio 01: Agent Execution & Delegation

Welcome to your first studio repository. Our workspace structure includes:
* `studio/README.md` & `studio/delegation-card.md` (for your delegation card)
* `studio/first-run.md` (for recording results)
* `code/harness_demo.py` & `code/test_harness.py` (our demo and test suites)
* `code/studio_fixture/*` & `code/README.md` (offline mock files)

In this studio, you will write one bounded [delegation card](delegation-card.md), run a baseline execution keeping the complete trace, change one condition and check the system again, and record what the human accepted or deferred.

To run the offline fallback fixture from the repository root:
```bash
python3 code/harness_demo.py --output /tmp/agentic-first-run.jsonl
(cd code && python3 -m unittest -v test_harness)
```
This code executes local fixtures only. It requires no network calls, LLM access, or package installations. Note that any incorrect installation line in the fixture README is test data, not a command to run. The offline example demonstrates controlled execution and evidence freshness, not model capability. Instructors will select and explain live harness options in class; no paid API setups are needed beforehand.

# Studio 02: Context Window Stress Test & Memory Architecture

Welcome to Studio 02. In this unit, we will look at how agent performance degrades when context windows grow too large, and how to build file-based persistent memory systems to solve this problem.

Here are the files for this studio:
* [studio-02/Studio_Instruction.md](studio-02/Studio_Instruction.md) (what to do)
* [studio-02/studio_setup_for_agent.md](studio-02/studio_setup_for_agent.md) (for your coding agent to follow during setup)
* [studio-02/HANDOFF.md](studio-02/HANDOFF.md) (for Nick and the TAs)
* [studio-02/GRADING_RUBRIC.md](studio-02/GRADING_RUBRIC.md) (for the TAs)
* [studio-02/starter/](studio-02/starter/) (starter files: `AGENTS.md`, `EXPLANATION_TEMPLATE.md`, and `evidence/README.md`)

In this studio, your team will push a coding agent past its useful context length using the open-source terminal coding agent pi. You will watch its answers degrade under stress, then resolve the issue using isolation with sub-agents and targeted summarization. After resolving the context limit issue, you will give your agent a persistent, file-based memory that spans three distinct sessions, and then compare its performance against a memoryless baseline.

The scripts used to generate the graded evidence are located in `code/studio-02/` (see its own README for the exact commands to run).

Unlike Studio 01, this studio does not include an offline mock fixture and requires a working model connection using either a subscription login or an API key.
