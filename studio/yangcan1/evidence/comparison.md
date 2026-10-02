# Run comparison and source review

This is an AI-authored experiment record, not `explanation-yangcan1.md`.

## Controlled comparison

| Item | Baseline | Changed condition | Recovery |
|---|---|---|---|
| Shared prompt | `prompts/research-update.md` | Same | Same |
| Input | `runs/baseline-input.json` | `runs/changed-input.json` | Original baseline input restored |
| Source URL | Present | Null | Present |
| Checked-on date | 2026-09-18 | Same | Same |
| Source retrieval | Succeeded | Not attempted | Succeeded |
| Agent result | COMPLETE | BLOCKED_MISSING_INPUT | COMPLETE |
| Artifact | `outputs/baseline.md` | `outputs/changed.md` | `outputs/recovery.md` |
| Article prose words | 160 | No article generated | 145 |
| Interpretation of outcome | Contract met | Safe stop; prerequisite requested | Contract met after correction |

The observed stop directly identified the missing URL. Restoring that input was the correction. The combined verifier confirms that the two JSON files differ on exactly one key, and separately checks all three outputs. It does not manufacture any of those outputs.

This is a small demonstration, not a causal benchmark of model reliability. Each condition uses a separate agent invocation; live source retrieval and stochastic generation can introduce variation. It establishes the behavior observed in these runs, not a universal success rate.

## Editorial review against the source

Source: [Anthropic article](https://www.anthropic.com/news/ust-claude), retrieved on 2026-09-18. Both completed outputs contain the source metadata. Review was performed by agents, not claimed as student review.

| Check | Baseline | Recovery | Review basis |
|---|---|---|---|
| Publication timing preserved; not presented as current-day news | Pass | Pass | Article header and output Limits sections |
| Existing efficiency result assigned to its original reporting organization/system | Pass | Pass | Adjacent iDEC results and integration paragraphs |
| Claude integration not claimed to have caused the existing result | Pass | Pass | Integration paragraph and output attribution language |
| Training commitment distinguished from completed training | Pass | Pass | Partnership/training section |
| Human approval retained in the examples where the article specifies it | Pass | Pass | Industry-platform descriptions |
| Interpretation clearly separated from source facts | Pass | Pass | Explicit Analysis/My analysis labels |
| Source claims not presented as independently established findings | Pass | Pass | Limits sections |

The changed output contains no article-specific facts or invented citation. The mechanical checks cover specific markers and known identifiers; its full text was also read to confirm the stop.

## What remains open

- The human has not yet accepted or deferred the outputs in a personal explanation.
- The human teammate exercise has not been performed in this session.
- The dated article was explicitly selected by the human; this experiment does not establish that it is the latest news.
- This source review checks fidelity to one article, not the truth of the companies' underlying performance claims.
- Official submission destination and eligibility remain governed by CourseWorks.
