# Studio 01 — Change & Explain

AI-generated technical change record. This is supporting evidence, not the personal `explanation-<username>.md` that the current assignment requires the student to write without AI-generated text.

## Planning-stage change

We completed the change-and-explain discussion during planning, before the first news-generation run. This record compares the instructions before and after the user's feedback; it does not claim a before/after comparison of generated news cards.

**Original condition:** Discover research updates from Anthropic News, Anthropic Engineering, and OpenAI News, with known researchers and established blogs as supplementary inputs. Produce a five-minute visual card sequence using verified facts.

**Changed condition:** The user added WSJ technology news, conditional on the writer having verifiable expertise relevant to the subject. This extends the input set beyond AI companies' own publications while preserving a source-quality requirement.

**Observation:** Publisher reputation alone would not satisfy the user's author requirement. Simply adding WSJ to a list would leave the agent without a concrete acceptance check.

**Correction:** Require the agent to inspect the author's biography and supporting work, record evidence links and a qualification rationale, and exclude an item when relevant expertise or the full article cannot be verified. Relevant research/industry experience, technical credentials, or sustained substantive specialist reporting can qualify; a byline or general reporting experience alone cannot.

**Expected difference:** A WSJ article can now be considered, but only after an additional author-expertise check. The original version would not explicitly include WSJ or require this check. No increased coverage or improved output quality has yet been demonstrated by a comparison run.

## Follow-up clarification: Tavily

The user noticed that the research tool was missing from the agent instructions. We added Tavily Search for discovery and author checks, Tavily Extract for article retrieval, and a saved evidence record. Search snippets and scores do not count as proof. Retrieval failures must be recorded.

This is a separate planning clarification, not a second controlled variable in an output experiment. A future comparison can keep Tavily constant and vary only WSJ eligibility.

## Subsequent changes and reasons

| Change | Reason | Observed result / limit |
|---|---|---|
| Explicit recurring execution | User clarified that this should be a bounded recurring job, not just a planning artifact. | An app-managed automation was created. |
| Weekly to monthly | User changed the desired delivery frequency. | Calendar-month coverage, due on the 1st at 9 a.m. New York time; delivery occurs on the first available hourly check after the due time. |
| Hourly breaking-news checks | Monthly delivery could miss urgent incidents. | One combined automation handles monthly cards and hourly checks because the app allows one heartbeat per task. Detection is polling, not instantaneous. |
| Severity and evidence threshold | Avoid treating every announcement or rumor as urgent. | Instructions require material impact, original evidence/corroboration, uncertainty labels, and duplicate suppression. No incident alert has yet tested that threshold. |
| Official incident sources beyond the original publishers | Incidents affecting platforms such as Hugging Face need evidence from the affected provider. | Added official advisories/status pages and verified researcher disclosures for incident checks. The user's example was not assumed to be real news. |
| Gmail delivery | User wanted updates pushed outside Codex and authorized email or SMS. | Connected Gmail was selected; a test message was sent and the user confirmed receipt with “Works!”. No SMS integration was needed. |
| Email content and delivery tracking | Local artifact paths are not usable in an email inbox; retries can duplicate alerts. | Configured HTML cards plus plain text, source links, returned message-ID tracking, and uncertain-send inspection. Full card email delivery remains untested. |
| Local branch | User requested `Elad_Hirsh_Studio01`, with no push or PR. | Branch created; commit `e943efa` saves the recurring and delivery instructions. |
| Student-folder organization | Current assignment requires all work inside a named folder under studio. | Moved artifacts into `studio/Elad_Hirsh/` and updated automation paths without changing its schedule or recipient. |

## Runtime change and comparison

The planning comparison remains as requested above. Separately, the first execution provides observable failed-check evidence: Tavily rejected the raw-content argument; removing it produced a valid response with zero results. This correction fixed the request, not the evidence shortage. A narrower advanced extraction recovered source content; date checks then excluded three candidates. The agent stopped without inventing a briefing. See `runs/2026-09-11/run-record.md` and the saved JSON responses for the before/after outcomes.

## Commit evidence

- The conversation records the initial request, WSJ change, Tavily clarification, and the user's request to document the planning-stage discussion.
- Local commit `c7b3160` contains the first committed card, already including WSJ. The original pre-WSJ version exists in the conversation, not as a separate Git commit.
- Local commit `9bc3c96` adds the Tavily workflow.
- The first execution attempt is recorded in `runs/2026-09-11/`. Its outcome is separate from the planning comparison above.

The [Studio 01 instructions](https://github.com/NickGuAI/agentic-engineering-course/blob/main/studio/Studio01.md) ask for observation, an evidence-led correction, a results comparison, and saved prompt/output/run records; a responsible stop is allowed. This document captures the planning change and explanation. It does not represent instructor confirmation that planning evidence alone fulfills all Part 3 requirements. Classroom sharing and official submission remain the user's decision.
