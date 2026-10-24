# AI news — 2026-09-16

- Executed: 2026-09-17T21:41:28Z.
- Window: previous calendar day in America/New_York, as clarified by the user.
- Date convention: match the publisher’s displayed date. Exact publication times and publisher time zones were unavailable; these are not verified Eastern-time publication instants.
- Coverage: the retrieved Anthropic News and OpenAI News indexes and linked matching articles.

## Reimagining advertising with AI

- **Reported:** OpenAI says it is testing Sponsored Agents with selected US advertisers and adding ad creation tools plus HubSpot and Shopify integrations. Sponsored conversations are labeled and separate from the original ChatGPT conversation. [Original post](https://openai.com/index/reimagining-advertising-with-ai/).
- **Product takeaway (inference):** Existing merchant tools provide distribution; separating sponsored interactions helps users understand whose interests the agent represents.
- **Engineering takeaway (inference):** Test conversation isolation and advertiser permissions before measuring conversion.

## How to connect AI usage to business value

- **Reported:** OpenAI describes Admin Console analytics combining usage, cost, task insights, and outcomes for ChatGPT Work and Codex. Insights classifies sampled messages; Outcomes tracks contributions to merged code. [Original post](https://openai.com/index/how-to-connect-ai-usage-to-business-value/).
- **Product takeaway (inference):** Adoption metrics need quality and business-outcome baselines before they support expansion decisions.
- **Engineering takeaway (inference):** Compare coding activity with defects, review time, and rework; contribution counts alone do not establish productivity gains.

## Our framework for reporting model misalignment

- **Reported:** OpenAI announces a disclosure framework and six reports on concerning model behavior observed over the preceding six months. It cautions that individual cases do not establish how frequently misalignment occurs. [Original post](https://openai.com/index/model-misalignment-reporting-framework/).
- **Product takeaway (inference):** Incident disclosure can become part of product trust even while causes and mitigations remain uncertain.
- **Engineering takeaway (inference):** Use disclosed failure modes to design regression evaluations, while avoiding prevalence estimates from selected incidents.

- **Anthropic:** no September 16 entries appeared in the retrieved news index. This is a coverage observation, not proof that no update existed anywhere on its sites.

## Two questions

1. For Sponsored Agents, which trust metric would you track alongside conversion, and what result would make you pause the rollout?
2. If Codex’s share of merged code rose while rework also increased, what experiment would distinguish useful assistance from added review burden?
