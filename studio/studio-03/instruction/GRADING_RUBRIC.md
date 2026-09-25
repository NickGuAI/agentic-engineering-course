# Studio 03 Completion Checklist

Studio 03 uses completion criteria; this checklist assigns no points.

- [ ] Part A: Complete the TODOs in your copied `agent.py` to make a minimal OpenAI Responses loop. Use the supplied flat Bash schema and implement your own sequential Bash execution with the official `tvly` CLI.
- [ ] The loop pairs each tool result with its call ID, keeps results in request history, has a checkpoint and stop condition, and provides one escalation path.
- [ ] Save a direct/ReAct run and a plan-first Plan-and-Execute run for the same fixed question and matching settings. The plan is numbered and its origin is identified; a model-generated plan uses tools disabled, while a human plan is also acceptable.
- [ ] Keep the structured course evidence for both runs, including failures. An API or research failure alone does not make a working, recorded loop incomplete.
- [ ] Complete `EXPLANATION.md` with concrete trace references, primary sources and their versions or dates, factual coverage and unknowns, the required usage and wall-time metrics, and team contributions.


**Optional bonus:** Briefly describe orchestration approaches your team explored beyond the required ReAct and plan-first comparison. This is not required for completion.

Producing a report does not by itself establish that its claims are accurate. Review claims against the captured source evidence, and mark unavailable metrics as unknown rather than zero.
