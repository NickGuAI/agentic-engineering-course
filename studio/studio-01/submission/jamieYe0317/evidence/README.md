# Execution evidence

This is an index of implementation evidence, not Jamie's personal explanation. `run-index.json` identifies the current recommended artifacts; earlier fixture runs are retained as development history.

## Real research run

`outputs/live-20260918/` contains a real collection and Codex summarization run. Automated verification passed. The result is partial: OpenAI articles returned HTTP 403, the article-fetch cap limited collection, and one long Anthropic article's essential evidence exceeded its allowance. The retained digest has one article from Anthropic, dated September 17, 2026.

The model was `gpt-6-astra` with low reasoning. The run made one model invocation and 13 HTTP attempts. Provider-reported usage was 7,616 input plus 201 output tokens, totaling 7,817. The 22-token reasoning breakdown is already included in output. Application input was separately estimated at 3,077 tokens; these two measurements should not be equated.

`outputs/live-replay-20260918/` replays the frozen source inputs and clock. It retained the validated article summary with zero model calls and passed fresh output verification. It also displays the long-article omission explicitly. This is a snapshot replay, not a second live collection.

The first digest's factual claims were compared by the coding assistant against local source paragraphs p001, p003, p013, p014, p015, p017 and p018. That comparison found support for the announcement, verification, access exclusions, monitoring, and retention statements. This does not replace Jamie's own source review; the artifacts deliberately keep human review and acceptance pending.

## Controlled failure experiment

The final synthetic experiment uses the prefix `fixture-6c174ca4`:

| Run suffix | Condition | Result |
|---|---|---|
| `baseline` | All fixture sources available; conservative stop policy | Complete |
| `failure` | Injected failure for Anthropic News; same stop policy | Blocked, no digest |
| `corrected` | Same injected failure; policy permits verified remaining items | Partial, with fresh passing checks |

This isolates source failure and then the policy correction. The clock and source snapshot remain fixed. All fixture content and responses are synthetic and labeled accordingly; these runs demonstrate control flow, not live model research capability.

## Token optimization experiment

The same fixture prefix includes `full`, `compact` and `warm` runs. Full and compact inputs use the same articles, schema, model double, policy, implementation and validation rules, with cache reads disabled. Compact evidence reduced estimated application input by **75.57%**. Both retained the expected facts and qualifications listed in `fixture-6c174ca4-expected-facts.json`; human review remains pending.

The warm run reused all five validated summaries with zero model calls. Its savings are result-cache reuse, separate from the compression comparison. No real provider tokens were consumed by these fixture runs. Comparison code refuses a savings figure for blocked, stale, empty or otherwise incompatible outputs.

## Codex adapter verification

`model-adapter-spike.json` records a real model invocation rejected because the first parser classified a passive experimental-feature startup notice as an unexpected item. `model-adapter-corrected-spike.json` records the correction and successful structured result. Unexpected tool/error events still fail closed.

A local HTTP request audit independently observed an empty tool list before provider dispatch. It used a no-auth local listener and synthetic input. The adapter preserves the selected model's instructions, removes tool capabilities for the invocation, and retains read-only sandboxing.

The two adapter smoke tests used 6,330 and 6,328 provider tokens respectively. They are separate from the 7,817-token research run; total recorded provider usage for these three development invocations is **20,475 tokens**. Codex overhead means application input limits are not hard provider-token limits.

## Tests and retention

`test-results.json` records **79 passing offline tests**, the command, timestamp and implementation hashes. Tests cover source parsing, dates, network boundaries, limits, stale verification, idempotency, cache invalidation, partial recovery, model restrictions, and valid comparisons. Local server tests also cover host/origin/token checks, file isolation, concurrent jobs, shutdown draining, and withholding changed artifacts.

Only summaries, sanitized trace events and metadata are included here. Downloaded pages, snapshots, transient model files and cache entries remain in ignored `work/`. No student explanation has been generated.

`local-hosting.json` records the localhost and browser smoke check. The browser completed synthetic demo `fixture-4279eebe`, then displayed the saved live run with its 7,817 reported provider tokens. Local hosting validation made no new live model calls.
