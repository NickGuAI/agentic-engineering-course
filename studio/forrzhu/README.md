# Studio 01 · Official-source AI research update

Read the [research report](outputs/research-report.md), then inspect the [115-source annotated catalog](outputs/sources.md). The cutoff is September 11, 2026. Coverage addresses LLMs, agents, systems, companies, capability limits and capital allocation. Twenty-two documents were published September 1–11; earlier documents provide context. The five issuing organizations are OpenAI, Anthropic, Amazon, SoftBank and Sequoia. Multiple documents can concern the same event.

| Artifact | Purpose |
|---|---|
| [Delegation card](delegation-card.md) | Four fields, with the student's specification and minimum count preserved verbatim. |
| [Research report](outputs/research-report.md) | Findings, chronology, limitations and distinctions among financing stages. |
| [Source catalog](outputs/sources.md) / [JSON](outputs/sources.json) | 115 distinct primary documents and agent-written evidence notes. |
| [Fetch receipts](outputs/fetch-receipts.jsonl) | Retrieval methods and fingerprints of locally retained source-tool responses. |
| [Run record](outputs/run-record.md) | Actual execution, changed retrieval condition and correction. |
| [Prompts and interaction log](outputs/interaction-log.md) | Task messages and public assistant messages, with scope of the export stated. |
| [Tool activity](outputs/tool-activity.jsonl) | Redacted metadata for logged tool calls and outputs; no source-article body archive. |
| [Retrieval probe](code/retrieval-probe.py) / [observations](outputs/retrieval-experiment.jsonl) | Read-only HTTP acquisition and observed failure/recovery; no automated model grading. |

## Folder layout

The workspace follows the example in the current [Studio README](../README.md):

```text
studio/forrzhu/
├── README.md
├── delegation-card.md
├── code/
│   └── retrieval-probe.py
└── outputs/
    ├── research-report.md
    ├── sources.md
    ├── sources.json
    ├── fetch-receipts.jsonl
    ├── interaction-log.md
    ├── interrupted-output.md
    ├── run-record.md
    ├── retrieval-experiment.jsonl
    ├── tool-activity.jsonl
    └── verification.md
```

The student must add `explanation-forrzhu.md` directly in `studio/forrzhu/` after writing the personal explanation. It is still pending.

From the repository root, the relocated acquisition probe runs with:

```bash
python3 studio/forrzhu/code/retrieval-probe.py
```

## Authorship and submission status

The research, annotations and execution documentation were generated with GPT-6 in Codex desktop. The student's original task specification is identified in the delegation card and interaction log. Provider claims and investor forecasts are attributed, and were not independently reproduced.

**The student's personal `explanation-forrzhu.md` is still required.** The course requires this file to be written by the student without AI-generated text. It has intentionally not been ghostwritten. No teammate exchange or personal reflection is claimed here. A draft PR can preserve the completed research while this requirement is pending. CourseWorks remains the official submission channel and has not been submitted by this agent.

The source-response fingerprints identify retrieval records retained locally during the run; they are not publisher-signed archives and cannot independently establish truth. Public logs omit credentials, private paths, internal instructions/reasoning and third-party article bodies. A complete private source archive is not published.
