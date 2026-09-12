"""
AI Research Brief Generator
Team: shreya-sachi

Fetches recent news from Anthropic and OpenAI, then uses Claude to produce
a student-facing research brief matching the delegation card spec.
"""

import anthropic
from datetime import datetime
from pathlib import Path


SOURCES = [
    "https://www.anthropic.com/news",
    "https://www.anthropic.com/engineering",
    "https://openai.com/news/",
]

PROMPT = f"""You are creating a research brief for students who want a quick overview of recent AI developments.

Step 1 — Fetch each of these pages (and only these):
{chr(10).join(f"  - {url}" for url in SOURCES)}

Step 2 — Select 3–5 of the most important recent stories across these sources.

Step 3 — Write the brief in this exact format:

# AI Research Brief
*Generated: {{date}}*

---

## Story 1: <Headline>
**Summary:** <2–3 sentences on what happened>
**Why it matters:** <1–2 sentences on significance for AI students>
**Source:** <article URL>

## Story 2: <Headline>
...

(repeat for each story)

---
*Sources: Anthropic News · Anthropic Engineering · OpenAI News*

Rules:
- Use ONLY the three sources listed above — no other sites
- Do not invent or speculate; only report what is on the page
- Exclude unrelated or promotional content
- Keep language clear and easy to scan
"""


def main():
    client = anthropic.Anthropic()

    output_dir = Path(__file__).parent.parent / "outputs"
    output_dir.mkdir(exist_ok=True)

    print("Fetching news and generating brief...\n")
    print("=" * 60)

    brief_parts = []

    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=4096,
        tools=[{"type": "web_fetch_20260209", "name": "web_fetch"}],
        messages=[{"role": "user", "content": PROMPT}],
    ) as stream:
        for event in stream:
            if (
                event.type == "content_block_delta"
                and event.delta.type == "text_delta"
            ):
                print(event.delta.text, end="", flush=True)
                brief_parts.append(event.delta.text)

        final_message = stream.get_final_message()

    brief_text = "".join(
        block.text for block in final_message.content if block.type == "text"
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"research-brief-{timestamp}.md"
    output_file.write_text(brief_text, encoding="utf-8")

    print(f"\n{'=' * 60}")
    print(f"Brief saved to: {output_file.relative_to(Path(__file__).parent.parent.parent)}")
    print(f"Stop reason: {final_message.stop_reason}")
    print(f"Input tokens: {final_message.usage.input_tokens}")
    print(f"Output tokens: {final_message.usage.output_tokens}")


if __name__ == "__main__":
    main()
