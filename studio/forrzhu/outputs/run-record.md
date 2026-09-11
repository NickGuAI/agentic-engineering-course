# Studio 01 execution record


This is the agent's execution documentation. It is not the student's personal explanation.


## Task and environment


- Date: September 11, 2026; research cutoff uses the same calendar date.
- Task: official-source AI research covering achievements, boundaries and capital; minimum 100 documents, as specified by the student.
- Harness: Codex desktop, using local shell tools, web retrieval and the authenticated GitHub browser session. Agent attribution: GPT-6 (Codex desktop).
- Upstream: `NickGuAI/agentic-engineering-course`, baseline main commit `474fbf7b7ad1229e90dfc8f54fccb8abe30545a4`.
- Workspace: `studio/forrzhu/`; working branch: `studio01/forrzhu-ai-news-2026-09-11`.
- The student's wording is preserved in [the card](../delegation-card.md). Date window, English presentation and document-count interpretation are disclosed agent choices.


## Observable run


1. Read the repository's Studio 01 instructions and delegation template. Selected the Research Update job requested by the student and created a dedicated local branch from main.
2. Requested a human-authored task specification. The student supplied the exact scope sentence and minimum source count recorded in the card.
3. Discovered articles from the official OpenAI RSS feed and Anthropic news/engineering pages; opened the selected article bodies. Added official Amazon, SoftBank and Sequoia documents, including Amazon's SEC filing, to cover capital.
4. Retained 115 unique document URLs. The catalog records publisher, publication date or unknown date, topical relevance and a limitation. Index snippets were discovery aids; they were not treated as sufficient verification of article claims.
5. Compared release articles with later updates. Separated announcement dates from event dates, older restrictions from later redeployment, and announced commitments from reported executed investments. Produced the report and annotated catalog.
6. Preserved source-retrieval metadata and response fingerprints. S053 could not initially be opened with the web tool; direct HTTPS retrieval of the same Anthropic article and HTML text extraction supplied its body. This actual recovery is separate from the controlled example below.
7. Verified that the browser account used for submission is `forrzhu`, created its course fork and remote working branch. A terminal push dry run failed because its configured credential belonged to a different account. That failure was not represented as a successful push; credentials were not changed. The existing authenticated browser was used for submission preparation.


## Change one condition: restrict the retrieval method


The changed condition was the available retrieval method for one fixed public URL, source S001. The source, research question and content cutoff stayed the same. This was an operational comparison within the same agent session, not an independent rerun of the model or a randomized experiment.


| Stage | Action | Actual observation | Output decision |
|---|---|---|---|
| Baseline | Open the official article with the web-retrieval tool. | The article body was returned and inspected. | The article can support attributed claims within the retrieved evidence. |
| Changed condition | Allow only direct HTTPS acquisition; run `python3 studio/forrzhu/retrieval-probe.py` from the repository root. | At 19:40:23 UTC, curl returned HTTP 403 and a 9,848-byte response. Curl's process exit code was 0. | A successful transport process did not establish successful article retrieval. Record the missing evidence in [interrupted-output.md](interrupted-output.md). |
| Correction | Restore the web-retrieval tool and reopen the same URL. | The article body was returned, including the engineering discussion relevant to the report. | Resume using the restored article evidence; preserve the failed attempt and its different method. |


The machine-readable observations are in [retrieval-experiment.jsonl](retrieval-experiment.jsonl). The probe records acquisition metadata and does not contain a scoring rule, model grader or automated evaluation rubric. It is agent-authored retrieval code; the student's specification remains separately identified.

## Folder-structure update

After the student requested alignment with the course README, the latest upstream `main` was fetched again. It remained at `474fbf7b7ad1229e90dfc8f54fccb8abe30545a4`. The shared Studio README gives an individual-folder example with `code/` and `outputs/`.

The acquisition probe was moved to `code/retrieval-probe.py`; reports, source catalogs and execution evidence were moved together into `outputs/`. The delegation card and workspace README remain at the individual-folder root. Local links were adjusted for the relocation. The earlier command in the run table records the command actually used before this move; the current command from the repository root is `python3 studio/forrzhu/code/retrieval-probe.py`.

This change updates the same working branch and PR #5. It changes organization and documentation paths, not the research claims or original retrieval observations. The student's personal explanation remains pending and must be written at the individual-folder root.
