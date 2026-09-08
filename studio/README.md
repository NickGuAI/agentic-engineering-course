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
