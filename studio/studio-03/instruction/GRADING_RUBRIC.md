# Studio 03 Completion Checklist

Studio 03 uses completion criteria. This checklist does not assign point values.

- [ ] `submission/<team>/agent.py` contains your team’s implementation of `run_agent(question, context)`.
- [ ] Part A fills the TODOs in `run_research_loop` and `run_bash`, uses the supplied flat Bash schema, writes its own Bash execution, uses the provided client, calls tools one at a time, pairs each result to its call ID, and updates request history.
- [ ] The loop checkpoints work, calls the budget hook before each model request, and has a stop condition and one escalation path.
- [ ] Part A saves a direct/ReAct run. Part B completes the plan branch in `run_agent` and compares that run with the Part A trace on the same fixed question and matching settings.
- [ ] The plan run saves a numbered plan. A model-generated plan is created with tools disabled; a human-supplied plan is identified as human-authored.
- [ ] `EXPLANATION.md` compares concrete trace events from both runs, supports claims with primary sources and their versions/commits and access dates, and reports the required usage and timing metrics.
- [ ] Unsupported details and limits of this one-pair comparison are stated plainly.
- [ ] Required structured course traces are included. API keys and raw provider/session logs are not included.
