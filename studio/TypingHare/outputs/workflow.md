# Workflow record

## Scope and instructions

1. Read `studio/TypingHare/delegation-card.md`. It requests three news summaries, publication metadata, and public opinions from Reddit, Quora, and X, using a Tavily Python script.
2. Applied the current user instruction to select the **three newest** posts, overriding the card’s one-to-two-week age window and importance-based selection. Applied the stricter current filesystem rule: add new files only within `studio/TypingHare`; preserve existing files.
3. Looked for applicable `AGENTS.md` instructions. The initial search was unnecessarily broad: it listed matching filenames under the repository and `/Users/james`; unrelated instruction files were not opened. A subsequent check of ancestor instruction paths found none. Initial shell startup printed a pyenv rehash warning because its shims directory was not writable; subsequent shell calls disabled login startup. Searches of missing `.agents` and `.codex` directories reported that they did not exist.
4. Inspected the target file listing and `git status --short`. The target directory was already untracked. Later, an additional empty `explanation-TypingHare.md` appeared; it was preserved along with `prompt.md` and the delegation card. Recorded SHA-256 hashes of those existing files before writing outputs.

## Approval boundary and tools

5. Asked the user whether Tavily and an existing credential could be used, citing the card’s requirement: “Ask for my approval before installing packages, using paid or API-based services, or accessing accounts or credentials.” No approval had arrived when the outputs were created. Silence was not treated as approval.
6. Continued independent research through the built-in public-web browsing/search tool. No Tavily API calls, package installations, account logins, credential reads, or external messages were performed. No Python scraping script was created or run; the Tavily-specific part of the card remains unfulfilled pending authorization. A local standard-library Python command was used only to inspect file hashes and write the Markdown files.

## News selection and verification

7. Opened [OpenAI News](https://openai.com/news/) on September 17, 2026. The first four displayed entries were:

   | Display order | Post | Publication date |
   | --- | --- | --- |
   | 1 | Introducing Astra for Law | September 17, 2026 |
   | 2 | Reimagining advertising with AI | September 16, 2026 |
   | 3 | How to connect AI usage to business value | September 16, 2026 |
   | 4 | Our framework for reporting model misalignment | September 16, 2026 |

8. Selected the first three. Because several posts share a date and the extracted listing did not expose publication times, used the site’s displayed order as the tie-breaker. The digest therefore identifies the newest listed posts, without claiming verified intraday timestamps.
9. Opened all three linked article pages and checked titles, dates, and author sections. All list OpenAI as author. Reopened the business-value article to read its body after the initial combined output showed only its opening lines. Sources:

   - [Astra for Law](https://openai.com/index/astra-for-law/)
   - [Advertising](https://openai.com/index/reimagining-advertising-with-ai/)
   - [AI usage and business value](https://openai.com/index/how-to-connect-ai-usage-to-business-value/)

## Public-opinion research

10. Ran these initial public-web search queries:

    - `"Astra for Law" site:reddit.com`
    - `"Reimagining advertising" OpenAI site:reddit.com`
    - `"How to connect AI usage to business value" site:reddit.com`
    - `site:quora.com OpenAI "Astra for Law"`
    - `site:quora.com OpenAI "Sponsored Agents"`
    - `site:quora.com OpenAI "How to connect AI usage to business value"`
    - `site:x.com "Astra for Law"`
    - `site:x.com OpenAI "Sponsored Agents"`
    - `site:x.com OpenAI "How to connect AI usage to business value"`

11. Initial Reddit results included advertising discussions from February 2026 and September 2025, plus an unrelated survey; excluded them as reactions to earlier or different events. Quora reported a non-retryable robots.txt block. X searches returned no results.
12. Broadened Reddit queries to:

    - `site:reddit.com "Astra" "Law" "September" "2026"`
    - `site:reddit.com "Sponsored Agents" "OpenAI"`
    - `site:reddit.com "OpenAI" "analytics" "September 16, 2026"`

13. The broader search found a relevant September 17 Sponsored Agents thread on r/ChatGPT and a second r/Agent_AI post that largely repeated the announcement. It also surfaced an unrelated IPO discussion; excluded it. Opened and read the [r/ChatGPT thread](https://www.reddit.com/r/ChatGPT/comments/1wit0ex/chatgpt_is_testing_sponsored_agents_that_let_you/) directly, including comments by Virtual_Fill_3025 and Seerix. Selected their substantive concern and conditional acceptance as illustrative viewpoints. Excluded the automated moderator message, unrelated material, and non-substantive reactions. Used paraphrases, not direct quotations.
14. Attempted direct access to `https://www.quora.com/search?q=OpenAI%20Sponsored%20Agents` and `https://x.com/search?q=%22Astra%20for%20Law%22&f=live`; both returned internal errors. Did not bypass restrictions or log in. Thus Reddit was successfully read; Quora and X could not be successfully scraped in this run.
15. Kept company-selected partner testimonials separate from independent public opinion. Reported missing evidence explicitly for the other two stories. The research is a limited search sample, not exhaustive or statistically representative.

## Writing and validation

16. Wrote `outputs/digest.md` with three concise summaries, source/date/author metadata, relevant public-opinion evidence or gaps, and clearly labeled student interpretations. Attributed product and benchmark claims to OpenAI; preserved limited rollout details and the hypothetical nature of the ROI example.
17. Created this workflow record alongside the digest. Used exclusive file creation (`open(..., "x")`) so existing output files could not be overwritten. No raw webpage archives were saved; source links and the query record above provide the research trail.
18. Validation checks cover exactly three digest entries, metadata for every entry, required source links, and unchanged hashes for the three existing target files. These checks and a final repository status inspection are performed immediately after file creation. No software test suite is needed for these Markdown additions.

## Remaining limitation

The digest and workflow are available for review. The card’s Tavily scraping method has not been executed because its approval condition remains pending; Quora and X coverage is also incomplete because of the access/search failures described above.
