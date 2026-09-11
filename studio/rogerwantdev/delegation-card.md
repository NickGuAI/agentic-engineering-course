# Delegation Card

## Task
Create a Course Assistant digest for the Agentic Engineering course materials.

The assistant should help me understand the course knowledge better by producing a concise study artifact for the current module or studio. The artifact should include:

- A short summary of the main ideas.
- A list of key terms or concepts I should know.
- A "what to do next" checklist for the studio work.
- Two or three questions I can use to check whether I actually understood the material.
- Optional visual structure, such as a table or concept map in markdown, when it would make the material easier to digest.

## Context
Primary course source: https://course.nickgu.me/

Local course materials are also available in this repository, especially:

- `README.md`
- `docs/course-prep.md`
- `studio/Studio01.md`
- `studio/delegation-card.md`

Target audience: me, a student in COMS W4995 Agentic Engineering who wants help turning course material into clear, actionable study notes.

Learning preference: explain things plainly, organize the material into steps, and make abstract agentic engineering ideas concrete with examples. If a visual layout helps, use markdown tables or simple diagrams rather than long paragraphs.

## Success criteria
The run is successful if the assistant produces a digest that:

- References the specific course/studio material it used.
- Separates summary, key concepts, action items, and self-check questions.
- Provides one short quiz or two to three self-check questions for each lecture or course section covered.
- Gives me at least one concrete next action for Studio 01.
- Avoids inventing course requirements that are not in the provided course materials.
- Is short enough to review in under 10 minutes.

## Restrictions
Do not use or expose private credentials, API keys, personal account information, or anything that should not be committed to GitHub.

Do not submit anything to CourseWorks or GitHub on my behalf without explicit approval.

If the assistant cannot access the course site, it should use the local repository files and clearly say that it used the local fallback.

If course requirements are ambiguous, the assistant should say what is unclear and suggest a reasonable interpretation instead of pretending to know.
