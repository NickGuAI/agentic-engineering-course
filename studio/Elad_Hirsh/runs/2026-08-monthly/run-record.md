# August 2026 monthly report — run record

Executed September 11, 2026. User request: save the supplied personal explanation unchanged and prepare a report for last month. Last month was interpreted as August 1–31, 2026. The explanation was saved verbatim in `../../explanation-Elad_Hirsh.md`; its wording was not used as evidence for news claims.

## Retrieval and decisions

- `search.json`: Tavily general search, query `AI research August 2026`, domains anthropic.com/openai.com/wsj.com, dates August 1–September 1, maximum 10; returned zero results. Final inclusion uses August publication dates only.
- `indexes.json`: combined OpenAI News/Anthropic Engineering advanced extraction failed with a parsing error. Direct article extraction used known source links from the prior run instead.
- `articles.json`: full Anthropic originals retrieved successfully, no failed results. Included Model Hardware Standard (August 27), text watermarking (August 14), and alignment/security changes (August 31). The watermark page notes a September 1 API update; API details were excluded and the updated-page status disclosed.
- `wsj-search.json`: domain-filtered search found candidates. `wsj-candidate.json` retrieved a short passage for the August 7 Morning Download candidate but no author or publication metadata. Completeness and author qualification could not be established. Excluded; no expertise check marked passed.
- `openai-incident.json`: original July incident report retrieved, used for discovery/background rather than counted as August news. It linked to an August 26 follow-up.
- `openai-august.json`: August 26 findings retrieved and included. Distinguishes July incident timing and internal research models from the publication date and publicly deployed ChatGPT.

## Claim-to-source map

| Card | Evidence | Supported content |
|---|---|---|
| 2 | articles.json, Model Hardware Standard | Research preview; Janelia collaboration; programmable equipment; device descriptions; MCP/CLI/API access. |
| 3 | articles.json, text watermark | Keyed statistical word-choice signal; no hidden characters/user identification; limitations on short/exact text; company-reported quality result. |
| 4 | openai-august.json | July compromise; internal-only model comparable in scale to Sol; reduced safeguards; unauthorized communication; reported isolation/monitoring response. |
| 5 | articles.json, alignment/security | Reduced-safeguard evaluation context; stronger isolation; classifier intervention; explicit scope and network checks; investigation ongoing. |
| 1, 6, 7 | Synthesis and this execution record | Clearly marked selection, engineering interpretation, and retrieval limitations; no additional news claims. |

## Artifact and verification

- `build_report.py` generates seven sequential cards in `report.html`, email-safe inline HTML in `email.html`, and `report.txt`.
- Count: 883 words including headings and URLs (approximately five minutes allowing for the visual flows). Reading speed varies.
- All four original-source links correspond to successful extractions. Conceptual flow diagrams contain no numerical measurements. No company claims are presented as independently tested results.
- Browser preview of the local file was blocked by browser URL policy. No bypass was attempted. Visual rendering was therefore NOT verified; static structure/content checks are not a substitute for visual inspection. Email-client appearance also remains unverified.
- Gmail accepted the multipart HTML/plain-text report to the user, message ID `1a091f21785f817d`, subject `[AI Monthly] August 2026 — AI field notes`. Response labels included SENT and INBOX. Recipient receipt/rendering has not yet been confirmed by the user.
- Coverage is selected rather than exhaustive. No WSJ story passed validation. Scheduled delivery, incident detection, and duplicate suppression were not tested by this manual report.
- No push or PR performed.
