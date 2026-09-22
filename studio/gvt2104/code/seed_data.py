"""Bundled fallback articles.

These are used when the live sources cannot be reached (offline, rate limited,
markup changed, etc.) so the webpage always renders something meaningful. The
live fetcher in ``fetcher.py`` overrides these whenever a fetch succeeds.

Data captured on 2026-09-11 from the three configured sources.
"""

SEED_ARTICLES = [
    # ---- Anthropic news -------------------------------------------------
    {
        "source": "Anthropic News",
        "category": "Announcements",
        "title": "Detecting and countering misuse of AI: September 2026",
        "url": "https://www.anthropic.com/threat-intelligence-report-september-2026",
        "date": "Sep 10, 2026",
        "summary": "Report on disrupted malicious activities and evolved threat "
                   "patterns observed against Claude models.",
    },
    {
        "source": "Anthropic News",
        "category": "Product",
        "title": "Introducing Claude Fable 5.1 and Claude Mythos 5.1",
        "url": "https://www.anthropic.com/claude-fable-and-mythos-5-1",
        "date": "Sep 1, 2026",
        "summary": "New advanced models optimized for coding and research work with "
                   "enhanced scientific capabilities.",
    },
    {
        "source": "Anthropic News",
        "category": "Policy",
        "title": "Developing Enterprise Frontier Safeguards with our customers",
        "url": "https://www.anthropic.com/news/enterprise-frontier-safeguards",
        "date": "Sep 1, 2026",
        "summary": "An enterprise-focused safety framework developed collaboratively "
                   "with customers.",
    },
    {
        "source": "Anthropic News",
        "category": "Announcements",
        "title": "Improving our alignment and security efforts",
        "url": "https://www.anthropic.com/news/improving-alignment-security-efforts",
        "date": "Aug 31, 2026",
        "summary": "Security improvements following unauthorized access incidents "
                   "reported in July.",
    },
    {
        "source": "Anthropic News",
        "category": "Announcements",
        "title": "Previewing the Model Hardware Standard",
        "url": "https://www.anthropic.com/news/model-hardware-standard-research-preview",
        "date": "Aug 27, 2026",
        "summary": "A research preview of a shared specification for AI agents to "
                   "safely operate physical devices.",
    },
    {
        "source": "Anthropic News",
        "category": "Product",
        "title": "Introducing Claude Opus 5",
        "url": "https://www.anthropic.com/news/claude-opus-5",
        "date": "Jul 24, 2026",
        "summary": "Latest Opus tier model with improvements for long-running agents "
                   "and professional work.",
    },
    # ---- Anthropic engineering -----------------------------------------
    {
        "source": "Anthropic Engineering",
        "category": "Engineering",
        "title": "How we contain Claude across products",
        "url": "https://www.anthropic.com/engineering/how-we-contain-claude",
        "date": "May 1, 2026",
        "summary": "Containment strategies for keeping increasingly capable AI agents "
                   "safe across products.",
    },
    {
        "source": "Anthropic Engineering",
        "category": "Engineering",
        "title": "An update on recent Claude Code quality reports",
        "url": "https://www.anthropic.com/engineering/april-23-postmortem",
        "date": "Apr 23, 2026",
        "summary": "Postmortem analysis of recent Claude Code quality issues.",
    },
    {
        "source": "Anthropic Engineering",
        "category": "Engineering",
        "title": "Scaling Managed Agents",
        "url": "https://www.anthropic.com/engineering/managed-agents",
        "date": "Apr 8, 2026",
        "summary": "Separating agent reasoning from execution capabilities to scale "
                   "managed agents.",
    },
    {
        "source": "Anthropic Engineering",
        "category": "Engineering",
        "title": "How we built Claude Code auto mode",
        "url": "https://www.anthropic.com/engineering/claude-code-auto-mode",
        "date": "Mar 25, 2026",
        "summary": "A safer way to skip permissions for streamlined agentic coding "
                   "workflows.",
    },
    {
        "source": "Anthropic Engineering",
        "category": "Engineering",
        "title": "Harness design for long-running application development",
        "url": "https://www.anthropic.com/engineering/harness-design-long-running-apps",
        "date": "Mar 24, 2026",
        "summary": "Framework and harness design patterns for sustained, long-running "
                   "agent operations.",
    },
    {
        "source": "Anthropic Engineering",
        "category": "Engineering",
        "title": "Eval awareness in Claude Opus 4.6's BrowseComp performance",
        "url": "https://www.anthropic.com/engineering/eval-awareness-browsecomp",
        "date": "Mar 6, 2026",
        "summary": "Analysis of model evaluation-awareness behavior during browsing "
                   "tasks.",
    },
    {
        "source": "Anthropic Engineering",
        "category": "Engineering",
        "title": "Quantifying infrastructure noise in agentic coding evals",
        "url": "https://www.anthropic.com/engineering/infrastructure-noise",
        "date": "Feb 5, 2026",
        "summary": "Measuring environmental factors that affect the reliability of "
                   "agentic coding evaluations.",
    },
    {
        "source": "Anthropic Engineering",
        "category": "Engineering",
        "title": "Building a C compiler with a team of parallel Claudes",
        "url": "https://www.anthropic.com/engineering/building-c-compiler",
        "date": "Feb 5, 2026",
        "summary": "Multi-agent collaboration between parallel Claude instances on a "
                   "complex software project.",
    },
    # ---- OpenAI news ----------------------------------------------------
    {
        "source": "OpenAI News",
        "category": "News",
        "title": "Rapidly scaling online storage to serve over 1 billion ChatGPT users",
        "url": "https://openai.com/index/scaling-storage-one-billion-users-part-one",
        "date": "Sep 11, 2026",
        "summary": "How OpenAI evolved Habitat from a Python library into a globally "
                   "distributed storage platform serving 22M requests per second.",
    },
    {
        "source": "OpenAI News",
        "category": "News",
        "title": "How a researcher uses Codex and ChatGPT to search for new antimicrobial molecules",
        "url": "https://openai.com/index/using-codex-chatgpt-to-search-for-new-antimicrobials",
        "date": "Sep 10, 2026",
        "summary": "A researcher pairs Codex and ChatGPT to accelerate the search for "
                   "novel antimicrobial molecules.",
    },
    {
        "source": "OpenAI News",
        "category": "News",
        "title": "Now everyone can put data to work",
        "url": "https://openai.com/index/put-data-to-work",
        "date": "Sep 10, 2026",
        "summary": "New capabilities that make it easier for everyone to put their "
                   "data to work.",
    },
]
