# Step 3 — Condition Change: Run Comparison Notes

*These are factual notes on the two runs, for inspection. They are not a substitute for the required hand-written `explanation-rb3736.md` — that reflection is yours to write.*

## Condition changed

**Restriction relaxed:** the delegation card's source-list restriction ("No fetching sites outside the approved source list") was lifted for the second run. The agent was allowed to search and cite any relevant source, instead of only `openai.com/news` and `anthropic.com/news`. All other restrictions (no writing outside `studio/rb3736/`, no credentials, no downloads, no installs, no spending money) stayed in place for both runs.

## What was observed

- **Baseline run** (`research-update-2026-09-22.md`): 4 items, all pulled directly from the two approved newsrooms, each verified by opening the full article (not just the listing card) before writing about it. Coverage was necessarily limited to whatever OpenAI and Anthropic chose to publish about themselves.
- **Broadened run** (`research-update-2026-09-22-broad-sources.md`): a web search surfaced a legitimate story — the Gates Foundation's 60-partner language-data coalition — that neither company's own newsroom would have published, since it's not primarily about either of them. This is the clearest benefit of the wider boundary: it can catch AI news that is *about* the ecosystem rather than self-reported by one lab.
- **The same search also surfaced lower-quality material**: several near-duplicate aggregator posts repeating the same handful of stories, and one item (geopolitical AI-policy coverage involving named government officials) that came back from the search tool in a form I could not confirm was neutrally and accurately characterized. I did not verify it against a primary source I trusted, so it does not appear in the broadened-run article at all.

## Evidence-led correction made

Given that, I applied a rule beyond what the card originally specified: **every claim used in either run still had to be confirmed by opening the actual source article**, even in the broadened run — a search engine's synthesized summary was treated as a lead to verify, not as citable content on its own. This is why the broadened run added exactly one new story rather than several: most of what a wider search returned either duplicated the baseline items or couldn't be independently confirmed in the time available. I judged the geopolitical item unverifiable-enough to leave out, rather than include it and flag the uncertainty — a responsible-stop choice per the studio instructions, rather than a hard failure.

## Net comparison

| | Baseline (2 sources) | Broadened (open web) |
|---|---|---|
| Items included | 4 | 1 new + baseline recap |
| Verification step | Open full article | Open full article (search results alone were not enough) |
| New coverage gained | — | Ecosystem/policy news neither lab self-publishes |
| New risk introduced | — | Noise, duplication, unverifiable/politically-charged items requiring filtering |

The practical takeaway: widening a permission boundary doesn't just add sources, it adds a verification burden that the original two-source restriction had implicitly handled for free (both those sites only publish their own vetted material). If this were a recurring job rather than a one-off comparison, I'd keep the wider boundary but make "confirm every fact against the primary article, not the search summary" an explicit, permanent rule on the card rather than something I applied ad hoc this run.
