# Studio Workspace

Welcome to the Studio Workspace. Here you will find the hands-on exercises and delegation tools for the course.

## Studio Index

- [Studio 01: Delegation & the first observable run](Studio01.md)
- [Delegation Card Template](delegation-card.md)

## Offline fallback demo

To run the offline fallback fixture from the repository root:

```bash
python3 code/harness_demo.py --output /tmp/agentic-first-run.jsonl
(cd code && python3 -m unittest -v test_harness)
```

This code executes local fixtures only. It requires no network calls, LLM access, or package installations. Note that any incorrect installation line in the fixture README is test data, not a command to run. The offline example demonstrates controlled execution and evidence freshness, not model capability.
