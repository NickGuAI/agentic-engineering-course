# Weekly AI Research Update — Source-Exclusion Run

Run: `20260911T154303-0400-exclude-anthropic-engineering`  
Started: 2026-09-11T15:43:03-04:00 (America/New_York)  
Publication window: **2026-09-05–2026-09-11, inclusive**  
Studio01 Step 3: the allowed source set now contains Anthropic News and OpenAI News.

**Anthropic Engineering is excluded by policy and was not accessed. Coverage is incomplete and reduced from the baseline.**

## 1. Rapidly scaling online storage to serve over 1 billion ChatGPT users

**Published:** 2026-09-11 · **Source:** OpenAI News  
**Official article:** [Read the source](https://openai.com/index/scaling-storage-one-billion-users-part-one/)

OpenAI describes moving Habitat from a shared Python library to a storage service, then rewriting it in Rust with two engineers, Codex, and GPT-5.5. OpenAI reports sixfold CPU efficiency and fifteenfold memory efficiency for the Rust service. Interpretation: the post is a useful systems case study in deployment coordination, event-loop delays, connection-pool feedback, and deciding when a rewrite becomes worthwhile.

## 2. Introducing the Agents API

**Published:** 2026-09-10 · **Source:** OpenAI News  
**Official article:** [Read the source](https://openai.com/index/introducing-the-agents-api/)

OpenAI announces the Agents API in public beta, exposing the Codex harness for long-running agents. The article describes a managed harness, a choice of compute environments, OpenAI-hosted sandboxes, and automatic context compaction. Interpretation: this shifts some orchestration and session management into platform infrastructure, making environment choice, tool design, and application-specific evaluation useful engineering questions.

## 3. Build more natural voice experiences with GPT-Live-1 in the API

**Published:** 2026-09-10 · **Source:** OpenAI News  
**Official article:** [Read the source](https://openai.com/index/introducing-gpt-live-1-in-the-api/)

OpenAI announces GPT-Live-1 in the API, describing a voice model that listens and speaks simultaneously while delegating deeper reasoning and tool calls to a backend model. Developers can configure speaking style and choose their backend tools. Interpretation: separating conversational timing from deeper computation offers a useful architecture to study for interactive voice agents; capability claims here are company-reported.

## 4. How a researcher uses Codex and ChatGPT to search for new antimicrobial molecules

**Published:** 2026-09-10 · **Source:** OpenAI News  
**Official article:** [Read the source](https://openai.com/index/using-codex-chatgpt-to-search-for-new-antimicrobials/)

OpenAI profiles César de la Fuente’s lab, which combines its own biological sequence models with ChatGPT and Codex for hypotheses, code, data processing, and analysis. The article distinguishes computational candidate discovery from experimental and clinical validation. Interpretation: this is a concrete example of general-purpose assistants supporting a specialist research pipeline, where laboratory evidence remains necessary.

## 5. Detecting and countering misuse of AI: September 2026

**Published:** 2026-09-10 · **Source:** Anthropic News  
**Official article:** [Read the source](https://www.anthropic.com/threat-intelligence-report-september-2026)

Anthropic reports disrupting Claude misuse across seven areas, including cyber operations, surveillance, fraud, and biological misuse. Its case studies cover December 2025–August 2026, while this report was published during the current window. The company describes cyber misuse shifting toward AI execution and orchestration. Relevance (interpretation): agent evaluations should examine multi-step behavior and misuse safeguards alongside task performance. These are Anthropic’s reported observations, not an independent measurement of overall misuse prevalence.

*Date provenance: September 10 is verified on the [official newsroom listing](https://www.anthropic.com/news); the retrieved report text does not display the publication day.*

## Coverage and exclusions

| Source | This run's status | Eligible verified | Selected |
| --- | --- | ---: | ---: |
| [Anthropic News](https://www.anthropic.com/news) | Accessible; freshly inspected listing and article | 1 | 1 |
| [OpenAI News](https://openai.com/news/) | Accessible; freshly inspected listing and five articles | 5 | 4 |
| Anthropic Engineering | Excluded by policy; not requested | Not assessed | 0 |

Both allowed sources were accessible. Only the first listings and selected candidate pages were inspected; archive pagination was not followed. Six distinct article pages were visited, with zero failed URLs or retries. The excluded source was not treated as a network outage and no replacement source was added.

The same-date data-product announcement was omitted under the unchanged five-item selection rule. The five selected articles, their dates, their order, and summary wording match the baseline after fresh source revalidation. The resulting document also has a new run time and explicit exclusion/coverage disclosure.

Fresh tool requests do not guarantee bypassing the web provider's cache. Company claims remain attributed; relevance statements are interpretations.

See [comparison](comparison.md), [run log](run-log.md), [execution trace](execution-trace.jsonl), and [validation](validation.json).
