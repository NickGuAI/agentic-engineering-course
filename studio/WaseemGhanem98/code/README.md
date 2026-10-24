# Research Update agent

A small reusable prompt agent for Studio 01, run by your signed-in Codex CLI.
It uses your existing account; no credentials belong in this folder.

From the repository root:

```bash
bash studio/WaseemGhanem98/code/run-research-update.sh
# Optional: use a 7-day window instead of the default 30 days.
bash studio/WaseemGhanem98/code/run-research-update.sh 7
# Inspect the exact input without calling Codex or accessing the web.
bash studio/WaseemGhanem98/code/run-research-update.sh --dry-run
```

Input: `research-update.md`, `../delegation-card.md`, today's
UTC date, and an optional positive window of 1–9999 days. “Recent” defaults to
30 days because the card does not define a duration. The agent prioritizes
research/model advances, AI tools/capabilities, and safety findings.

Output: a concise Markdown report with the 3 most relevant recent updates,
each including title, short summary, why it matters, publication date, and
source link. Fewer qualifying updates are reported honestly. Each execution
saves its prompt, final report, JSONL trace, diagnostic log, and completion
status under `../outputs/run-<timestamp>-<unique suffix>/`. Dry runs print the
prompt only and create no files. Failed executions save diagnostics and a failed
status, and may have no report. Inspect the trace and report before sharing; a completed
process alone does not establish factual correctness.

Restrictions: start at `https://openai.com/news/` and optionally follow its
direct links to OpenAI-owned articles. The agent allows only HTTPS URLs on
`openai.com` or its subdomains, including redirect targets. It must not use
non-OpenAI domains, search elsewhere, follow additional sources from articles,
use remembered news, or invent facts. Source links are copied from the listing.
Summaries use the listing and permitted article evidence; implications are
labeled as inferences. Unreadable articles and other evidence limitations are
disclosed. It distinguishes no qualifying news from inability to verify news.
The read-only sandbox restricts agent file changes; the source rule is a prompt
instruction, not a network firewall. Verify compliance in the saved trace.

For Studio 01's changed-condition exercise, compare a default run with a
one-day run, or try `--dry-run 0` to observe input rejection. See
`../outputs/verification.md` for the checks performed during implementation.
Earlier run artifacts were moved into `../outputs/`; the historical verification
record is preserved as `../outputs/verification-original.md`.
Those records describe earlier runs under the previous listing-only source
restriction; they do not verify the updated article-link rule.
