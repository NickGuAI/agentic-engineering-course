# AI Research Update: week of 2026-09-24

Run 3 (corrected). Sources: Anthropic News; OpenAI News via its official RSS feed (openai.com/news/rss.xml) because the HTML page returned 403. OpenAI items are summarized from the feed description only.

### Claude discovers a novel enzyme system with CRISPR-like repeats
Date: 2026-09-23
Source: https://www.anthropic.com/news/claude-discovers-novel-enzyme-system

Claude agents searched a sequence database and flagged a previously unknown enzyme family, "array-associated reverse transcriptases" (ART), which pairs a reverse-transcriptase gene with repeating DNA sequences, a layout that looks like CRISPR. The post says the run used about 950 agents and 210 million tokens over 21 hours. Humans wrote the initial prompt and did the lab validation. Anthropic says "we don't yet know its function."

Why it matters: this is a concrete example of many agents running a long, open-ended search, with humans checking the results. It's the same delegate-then-verify loop this course teaches.

### Partnering with Accenture on embedded evaluation
Date: 2026-09-18
Source: https://www.anthropic.com/news/accenture-embedded-evaluation

Anthropic is partnering with Accenture's Faculty division on independent evaluation of frontier models, covering "evaluating and red-teaming models, conducting alignment assessments, and testing model safeguards." Evaluators will be embedded inside Anthropic. Both companies "expect to invest at least $1 billion" over five years. The deal is non-exclusive, and Anthropic says more evaluators will be announced.

Why it matters: outside evaluation is being staffed and funded like a real industry, so "who checks the model" is turning into a career path of its own.

### Introducing the Life Sciences Verification Program
Date: 2026-09-17
Source: https://www.anthropic.com/news/life-sciences-verification-program

Verified life-science organizations can apply for access to Mythos, Opus, and Sonnet with "refined safeguards more permissive for biology-related work." There are two tiers: Standard Use, and High-risk Use for vetted projects. Instead of real-time blocking, the program relies on offline monitoring against a "stated safe scope," with 30-day data retention.

Why it matters: it's a different access-control design. Permissions depend on who the user is and are enforced after the fact, instead of one filter applied to everyone.

### OpenAI extends cyber access to Ukraine for civilian defense
Date: 2026-09-23
Source: https://openai.com/index/openai-extends-cyber-access-to-ukraine-for-civilian-defense

According to the feed, OpenAI is "extending access to its Daybreak program to the Government of Ukraine to support the cyber defense of civilian infrastructure." The feed doesn't say what Daybreak includes; that's unverified here.

Why it matters: frontier labs are now giving specific governments access to security-focused programs, which is policy work as much as technical work.

### Harvey turns legal context into stronger drafts with GPT-6 Astra
Date: 2026-09-23
Source: https://openai.com/index/harvey-from-context-to-confidence-with-astra

A customer story. According to the feed, GPT-6 Astra "produces more structured, context-aware legal documents, freeing lawyers to focus on strategy." These are the vendor's claims, with no independent numbers in the feed.

Why it matters: the pitch is context in, structured draft out, with an expert reviewing. That's the delegation pattern from Studio 01 applied to a regulated field.
