# AI Research Update: week of 2026-09-24

Run 1 (baseline). Source: Anthropic News only. Window: 2026-09-17 to 2026-09-24.

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
