# Output

## Initial run

**Run time:** September 11, 2026, 3:38 p.m. EDT  
**Selection rule:** Three newest dated posts displayed in each source section. Ties retain display order.

### Anthropic Newsroom

#### [Detecting and countering misuse of AI: September 2026](https://www.anthropic.com/threat-intelligence-report-september-2026)

- **Date:** September 10, 2026
- **Author:** No author listed

Anthropic reports on malicious Claude usage it disrupted between December 2025 and August 2026 across cyber operations, surveillance, influence operations, weapons-related misuse, scams, biological misuse, and model distillation. A key agentic-engineering finding is the shift from chatbot assistance toward orchestration: some threat actors used multi-agent systems to automate reconnaissance, exploitation, persistence, and exfiltration while humans selected targets and reviewed results.

#### [Claude Fable 5.1 and Claude Mythos 5.1](https://www.anthropic.com/claude-fable-and-mythos-5-1)

- **Date:** September 1, 2026 (Newsroom index; the article page displays “September 2026”)
- **Author:** No author listed

Anthropic presents Fable 5.1 and Mythos 5.1 as the same underlying model with different safeguard and access regimes: Fable is generally available, while Mythos is limited to trusted-access programs for advanced cybersecurity and life-science work. The post emphasizes stronger coding, knowledge-work, long-horizon, and scientific capabilities alongside lower cache-read costs, more precise safeguards, and evaluations covering cyber, biological, agentic-safety, and alignment risks.

#### [Developing Enterprise Frontier Safeguards with our customers](https://www.anthropic.com/news/enterprise-frontier-safeguards)

- **Date:** September 1, 2026
- **Author:** No author listed

Enterprise Frontier Safeguards combines misuse monitoring with a zero-data-retention-like architecture by keeping activity data in customer-controlled cloud infrastructure. Automated systems analyze a rolling activity window and send flags to the customer for review, allowing regulated organizations to retain their own encryption, access-control, audit, and human-review boundaries.

### Anthropic Engineering

#### [How we contain Claude across products](https://www.anthropic.com/engineering/how-we-contain-claude)

- **Date:** May 25, 2026
- **Author:** No author listed

Anthropic argues that capable agents require limits on potential damage in addition to behavioral supervision, because frequent permission prompts create approval fatigue and probabilistic defenses retain a nonzero miss rate. It describes overlapping defenses across the execution environment, model layer, and external content, using sandboxes, virtual machines, egress controls, scoped permissions, and product-specific isolation patterns to cap blast radius.

#### [An update on recent Claude Code quality reports](https://www.anthropic.com/engineering/april-23-postmortem)

- **Date:** April 23, 2026
- **Author:** No author listed

Anthropic traces reported Claude Code degradation to three separate changes: a lower default reasoning effort, a cache-related bug that repeatedly removed prior reasoning, and a system-prompt change intended to reduce verbosity. All three were reverted or fixed by April 20; the post shows how individually scoped changes with different rollout schedules can resemble broad model regression when aggregate feedback and evaluations do not reproduce the failures promptly.

#### [Scaling Managed Agents: Decoupling the brain from the hands](https://www.anthropic.com/engineering/managed-agents)

- **Date:** April 8, 2026
- **Author:** No author listed

Managed Agents separates the “brain” (model and harness), “hands” (sandbox and tools), and durable session log behind stable interfaces so each component can fail or evolve independently. The architecture supports crash recovery from an append-only event stream and keeps credentials outside the code-execution sandbox, with dedicated proxies supplying narrowly scoped authorization to external tools.

### OpenAI News

#### [Rapidly scaling online storage to serve over 1 billion ChatGPT users](https://openai.com/index/scaling-storage-one-billion-users-part-one/)

- **Date:** September 11, 2026
- **Authors:** Jon Lee, Chaomin Yu, and Ben Ries

OpenAI describes Habitat, an online storage layer handling more than 70 million requests per second and over 500 petabytes across nearly 40 regions. The system evolved from a Python client library into a centralized service for routing, authorization, observability, and operational control; the article also covers asyncio latency, load-balancing feedback loops, constrained APIs, and a Rust rewrite reported as substantially more CPU- and memory-efficient.

#### [How a researcher uses Codex and ChatGPT to search for new antimicrobial molecules](https://openai.com/index/using-codex-chatgpt-to-search-for-new-antimicrobials/)

- **Date:** September 10, 2026
- **Author:** OpenAI

César de la Fuente’s lab combines domain-specific deep-learning models with Codex and ChatGPT to search genome and protein datasets, formulate hypotheses, write code, process data, and connect biological and computational expertise. The article stresses that AI can prioritize candidate molecules rapidly but cannot replace experimental validation, toxicity testing, manufacturing work, clinical trials, or human accuracy checks.

#### [Now everyone can put data to work](https://openai.com/index/put-data-to-work/)

- **Date:** September 10, 2026
- **Author:** No author listed

OpenAI introduces a Data agent for ChatGPT Work that connects to approved enterprise data sources, applies organizational definitions and existing access controls, and produces analyses and interactive dashboards from natural-language requests. Users can inspect evidence and approve downstream actions, while administrators control available connectors and permissions—an example of an agent grounded by governed semantic context and bounded tool access.

### Five most referenced technical terms

| Rank | Normalized term | Posts containing term | Total occurrences |
|---:|---|---:|---:|
| 1 | model / models | 9 of 9 | 307 |
| 2 | system / systems | 9 of 9 | 123 |
| 3 | agent / agents / agentic | 8 of 9 | 201 |
| 4 | code / coding | 8 of 9 | 134 |
| 5 | tool / tools | 8 of 9 | 95 |

Terms were matched case-insensitively within each page’s first `<article>` element. Singular and plural forms were combined, `agentic` was grouped with `agent`, and `coding` was grouped with `code`; scripts, styles, SVG text, navigation, and footers were excluded. Ranking uses distinct-post coverage first and total occurrences second.

## Superseded audience experiment

**Run time:** September 11, 2026, 3:44 p.m. EDT  
**Changed condition:** The audience is now high-school computer-science students. Sources, selected posts, metadata, evidence, and term-counting rules are unchanged.

### Anthropic Newsroom

#### [Detecting and countering misuse of AI: September 2026](https://www.anthropic.com/threat-intelligence-report-september-2026)

- **Date:** September 10, 2026
- **Author:** No author listed

Anthropic describes real cases in which people tried to use Claude for cyberattacks, scams, surveillance, propaganda, weapons-related work, and copying other AI models. In some cyberattacks, AI agents—programs that can plan and use tools—automated steps such as finding targets, exploiting weaknesses, and stealing data while humans chose the goals and checked the results. The main lesson is that giving an AI more independence also requires stronger limits, monitoring, and human oversight.

#### [Claude Fable 5.1 and Claude Mythos 5.1](https://www.anthropic.com/claude-fable-and-mythos-5-1)

- **Date:** September 1, 2026 (Newsroom index; the article page displays “September 2026”)
- **Author:** No author listed

Fable 5.1 and Mythos 5.1 use the same underlying AI model, but Anthropic gives them different safety controls and access rules. Fable is generally available, while Mythos is restricted to approved users because it can perform more advanced cybersecurity and life-science tasks. Anthropic reports improvements in coding, research, long-running tasks, cost, and safety testing, though the published benchmark results should still be understood as the company’s own evaluations.

#### [Developing Enterprise Frontier Safeguards with our customers](https://www.anthropic.com/news/enterprise-frontier-safeguards)

- **Date:** September 1, 2026
- **Author:** No author listed

Enterprise Frontier Safeguards is a monitoring system designed for organizations using powerful AI. Activity records stay in cloud storage controlled by the customer, while automated checks look for dangerous patterns across multiple sessions. If the system finds something suspicious, the customer’s own staff review the alert instead of automatically sending private data to an Anthropic employee.

### Anthropic Engineering

#### [How we contain Claude across products](https://www.anthropic.com/engineering/how-we-contain-claude)

- **Date:** May 25, 2026
- **Author:** No author listed

Anthropic argues that asking users to approve every AI action is not enough because people tend to click “approve” repeatedly without checking carefully. Its alternative is containment: placing the agent inside controlled environments such as sandboxes or virtual machines and limiting its files, network connections, and permissions. These boundaries reduce the “blast radius,” meaning the maximum damage a mistake or attack could cause.

#### [An update on recent Claude Code quality reports](https://www.anthropic.com/engineering/april-23-postmortem)

- **Date:** April 23, 2026
- **Author:** No author listed

Anthropic found that three product changes made Claude Code seem worse even though the underlying API and model-serving system had not changed. One lowered the default reasoning effort, one bug repeatedly deleted older reasoning from long sessions, and one prompt made answers shorter at the cost of coding quality. The incident shows why engineers must test configuration, memory, and prompts—not only the model itself—when an AI product’s behavior changes.

#### [Scaling Managed Agents: Decoupling the brain from the hands](https://www.anthropic.com/engineering/managed-agents)

- **Date:** April 8, 2026
- **Author:** No author listed

Managed Agents divides an AI system into a “brain” that decides what to do, “hands” that run tools in a sandbox, and a session log that records events. Because these parts are separate, a crashed component can be replaced and continue from the log. Passwords and access tokens are kept outside the code-running sandbox, which makes them harder for faulty or malicious generated code to steal.

### OpenAI News

#### [Rapidly scaling online storage to serve over 1 billion ChatGPT users](https://openai.com/index/scaling-storage-one-billion-users-part-one/)

- **Date:** September 11, 2026
- **Authors:** Jon Lee, Chaomin Yu, and Ben Ries

OpenAI explains Habitat, the system that quickly retrieves data needed by products such as ChatGPT and Codex. It handles more than 70 million requests per second and over 500 petabytes of data, so engineers had to solve problems involving overloaded servers, network connections, and traffic distribution. Habitat grew from a Python library into a central service, and OpenAI later rewrote much of it in Rust to use less computing power and memory.

#### [How a researcher uses Codex and ChatGPT to search for new antimicrobial molecules](https://openai.com/index/using-codex-chatgpt-to-search-for-new-antimicrobials/)

- **Date:** September 10, 2026
- **Author:** OpenAI

César de la Fuente’s research group searches DNA and protein data for molecules that might fight infections that resist existing drugs. Deep-learning programs find promising patterns, while Codex and ChatGPT help the team write code, organize data, and develop ideas across biology and computer science. A computer prediction is only a starting point: scientists must still test whether a molecule works, whether it is safe, and whether it can become an actual medicine.

#### [Now everyone can put data to work](https://openai.com/index/put-data-to-work/)

- **Date:** September 10, 2026
- **Author:** No author listed

OpenAI’s Data agent lets workers ask questions about approved company databases in ordinary language and turn the answers into charts and dashboards. It uses the organization’s existing definitions and access rules so users should see only data they already have permission to view. People can inspect the evidence and approve actions, while administrators choose which data connections and tools are available.

### Five most referenced technical terms

| Rank | Normalized term | Posts | Occurrences | Plain-language meaning |
|---:|---|---:|---:|---|
| 1 | model / models | 9 of 9 | 307 | A trained computational system that recognizes patterns or produces outputs. |
| 2 | system / systems | 9 of 9 | 123 | A group of connected parts working together. |
| 3 | agent / agents / agentic | 8 of 9 | 201 | AI-driven software that can plan steps and use tools toward a goal. |
| 4 | code / coding | 8 of 9 | 134 | Instructions written for a computer to execute. |
| 5 | tool / tools | 8 of 9 | 95 | A capability an agent or programmer can use to perform a specific action. |

The counts are unchanged from the initial run. Matching was case-insensitive within each page’s first `<article>` element; singular and plural forms were combined, `agentic` was grouped with `agent`, and `coding` was grouped with `code`.

This audience-only experiment was completed but superseded by the bounded-correction run below.

## Changed-condition run

**Run time:** September 11, 2026, 3:48 p.m. EDT  
**Changed condition:** The Anthropic Engineering input was changed from `https://www.anthropic.com/engineering` to the malformed `https://www.anthropic.com/engineerin`.

### Failed check

The malformed source returned HTTP `404`. Its response was rejected, and no article selection or summary was produced from it.

### Bounded correction

The failed URL was compared only with the three source URLs already authorized in `delegation-card.md`. It had one unambiguous canonical match—`https://www.anthropic.com/engineering`—so exactly one corrected retry was made; that request returned HTTP `200`. No search, alternate domain, or further retry was used.

### Corrected result

After the source check passed, the run reproduced the verified initial research update above: three posts from each of the three approved sections, nine posts total, with the same titles, dates, author fields, summaries, source links, and technical-term counts. The recovered top-five ranking remained `model`, `system`, `agent/agentic`, `code/coding`, and `tool`, with counts of 307, 123, 201, 134, and 95 respectively.

**Outcome:** Accepted after one bounded correction. Had the corrected request failed, the run would have stopped without claiming a complete research update.
