# Second research — AI news for engineers

**Run date:** September 11, 2026  
**Coverage:** September 5–11, 2026, inclusive  
**Task card:** `studio/hj2713/delegation-card-2.md`

Five selected updates for ML engineers, researchers, software developers, and backend engineers. Dates refer to publication, not necessarily when the underlying work happened. Engineering takeaways are my interpretation; reported results come from the publishers and were not independently tested.

## 1. OpenAI shares lessons from scaling its storage service

**September 11 — OpenAI Engineering**

- **What happened:** OpenAI described how Habitat evolved from a shared Python library into a separate storage service. Centralizing it made updates easier to coordinate across products.
- **What engineers can learn:** A fast database can still produce a slow application. Python tasks sometimes waited to resume after database responses arrived. Measuring this scheduling delay helped identify the bottleneck.
- **Practical detail:** Workers also stalled when they refreshed and parsed large configuration files simultaneously. Smaller files and staggered refresh times reduced the problem.
- **Engineering takeaway:** Measure where requests wait inside your application, alongside the time spent in external services.

Source: [Rapidly scaling online storage to serve over 1 billion ChatGPT users](https://openai.com/index/scaling-storage-one-billion-users-part-one/).

## 2. OpenAI introduces a managed Agents API

**September 10 — OpenAI News**

- **What happened:** The Agents API entered public beta. It provides the coordination software and infrastructure behind Codex-style agents, including context management, tool use, and delegation to other agents.
- **What developers control:** The task, model, tools, and execution environment. Agents can use an OpenAI-hosted environment, developers' infrastructure, or supported partners.
- **Why it matters:** Longer tasks require code execution, saved intermediate results, and reliable sessions as well as model responses.
- **Engineering takeaway:** Evaluate a managed agent service on one real workflow. Measure completion quality, failure recovery, and cost per completed task before expanding usage.

Source: [Introducing the Agents API](https://openai.com/index/introducing-the-agents-api/).

## 3. GPT-Live-1 brings simultaneous listening and speaking to the API

**September 10 — OpenAI News**

- **What happened:** OpenAI released a voice model that can listen while speaking, making it easier to handle interruptions and changes of direction.
- **How it works:** The model processes incoming and outgoing audio together. It can delegate deeper reasoning and tool calls to a separate text model, including a third-party model.
- **What developers control:** Instructions can shape tone, pace, and conversational style.
- **Engineering takeaway:** Test voice applications with interruptions, silence, background noise, and slow tool responses. Correct answers alone do not show whether a conversation works well.

Source: [Build more natural voice experiences with GPT-Live-1 in the API](https://openai.com/index/introducing-gpt-live-1-in-the-api/).

## 4. Anthropic documents AI coordinating malicious activity

**September 10 — Anthropic News**

- **What happened:** Anthropic published cases of misuse disrupted between December 2025 and August 2026, covering cyber operations, surveillance, fraud, and other areas.
- **Key observation:** In the cyber cases, AI increasingly carried out or coordinated actions. Humans still chose targets and reviewed results.
- **Evidence limit:** Anthropic selected notable cases. The report does not measure how common misuse is among all users.
- **Engineering takeaway:** Logs for agent applications should capture actions and their sequence, including tool access and data movement. Individual messages provide only part of the picture.

Sources: [September 2026 threat intelligence report](https://www.anthropic.com/threat-intelligence-report-september-2026); publication date from the [Anthropic newsroom](https://www.anthropic.com/news).

## 5. A quantum computing lab uses agents for routine measurements

**September 8 — OpenAI Applied AI**

- **What happened:** OpenAI described MIT researcher Beatriz Yankelevich connecting GPT-5.6 Sol through Codex to laboratory software for measurements on a six-qubit chip. Qubits are the information units used in quantum computers.
- **What made it useful:** The researcher supplied instructions for running and evaluating specific experiments. The agent selected settings, ran measurements, analyzed results, and saved findings for later steps.
- **Where it struggled:** Weak or noisy signals sometimes required an experienced researcher's guidance. The article does not establish reliable autonomy for arbitrary experiments.
- **Engineering takeaway:** Give agents bounded tasks with explicit evaluation instructions. Define when ambiguous results should trigger human review.

Source: [How GPT-5.6 Sol helps run quantum computing experiments](https://openai.com/index/codex-quantum-computing-experiments/).

## Source check

- Rechecked [OpenAI News](https://openai.com/news/), [Anthropic News](https://www.anthropic.com/news), and [Anthropic Engineering](https://www.anthropic.com/engineering) for this run. Summaries use the linked official articles read during this session.
- All five selected articles fall within the publication window. This is a curated digest, not an exhaustive list.
- No in-window Anthropic Engineering article was identified on the retrieved listing. Its featured [containment article](https://www.anthropic.com/engineering/how-we-contain-claude) is dated May 25, 2026 and was excluded.
