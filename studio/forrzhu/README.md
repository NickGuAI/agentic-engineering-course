# Studio 01 · Official-source AI research update

Read the [research report](research-report.md), then inspect the [115-source annotated catalog](sources.md). The cutoff is September 11, 2026. Coverage addresses LLMs, agents, systems, companies, capability limits and capital allocation. Twenty-two documents were published September 1–11; earlier documents provide context. The five issuing organizations are OpenAI, Anthropic, Amazon, SoftBank and Sequoia. Multiple documents can concern the same event.

| Artifact | Purpose |
|---|---|
| [Delegation card](delegation-card.md) | Four fields, with the student's specification and minimum count preserved verbatim. |
| [Research report](research-report.md) | Findings, chronology, limitations and distinctions among financing stages. |
| [Source catalog](sources.md) / [JSON](sources.json) | 115 distinct primary documents and agent-written evidence notes. |
| [Fetch receipts](fetch-receipts.jsonl) | Retrieval methods and fingerprints of locally retained source-tool responses. |
| [Run record](run-record.md) | Actual execution, changed retrieval condition and correction. |
| [Prompts and interaction log](interaction-log.md) | Task messages and public assistant messages, with scope of the export stated. |
| [Tool activity](tool-activity.jsonl) | Redacted metadata for logged tool calls and outputs; no source-article body archive. |
| [Retrieval probe](retrieval-probe.py) / [observations](retrieval-experiment.jsonl) | Read-only HTTP acquisition and observed failure/recovery; no automated model grading. |

## Authorship and submission status

The research, annotations and execution documentation were generated with GPT-6 in Codex desktop. The student's original task specification is identified in the delegation card and interaction log. Provider claims and investor forecasts are attributed, and were not independently reproduced.

**The student's personal `explanation-forrzhu.md` is still required.** The course requires this file to be written by the student without AI-generated text. It has intentionally not been ghostwritten. No teammate exchange or personal reflection is claimed here. A draft PR can preserve the completed research while this requirement is pending. CourseWorks remains the official submission channel and has not been submitted by this agent.

The source-response fingerprints identify retrieval records retained locally during the run; they are not publisher-signed archives and cannot independently establish truth. Public logs omit credentials, private paths, internal instructions/reasoning and third-party article bodies. A complete private source archive is not published.
