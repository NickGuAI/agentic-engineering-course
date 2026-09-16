# Studio 01 study digest

Generated from pinned public materials. This is an AI-assisted learning artifact, not the student's personal explanation.

## The workflow

```text
FRAME              RUN & INSPECT        CHANGE & EXPLAIN
four-field card -> bounded local run -> change one condition
                       |                        |
                 output + trace        compare evidence -> correct or stop
```

The workshop follows these three phases. [Studio01.md:7](https://github.com/NickGuAI/agentic-engineering-course/blob/474fbf7b7ad1229e90dfc8f54fccb8abe30545a4/studio/Studio01.md#L7) [Studio01.md:21](https://github.com/NickGuAI/agentic-engineering-course/blob/474fbf7b7ad1229e90dfc8f54fccb8abe30545a4/studio/Studio01.md#L21) [Studio01.md:25](https://github.com/NickGuAI/agentic-engineering-course/blob/474fbf7b7ad1229e90dfc8f54fccb8abe30545a4/studio/Studio01.md#L25)

## What to do

| Step | Concrete action | Evidence to retain |
|---|---|---|
| Define | Choose Research Update or Course Assistant and fill the delegation card | Completed card |
| Execute | Run local Codex or Claude Code using your own account | Output and execution trace |
| Perturb | Change one condition, inspect the result, then correct or stop | Before/after comparison |

Sources: [Studio01.md:11](https://github.com/NickGuAI/agentic-engineering-course/blob/474fbf7b7ad1229e90dfc8f54fccb8abe30545a4/studio/Studio01.md#L11) [Studio01.md:12](https://github.com/NickGuAI/agentic-engineering-course/blob/474fbf7b7ad1229e90dfc8f54fccb8abe30545a4/studio/Studio01.md#L12) [Studio01.md:23](https://github.com/NickGuAI/agentic-engineering-course/blob/474fbf7b7ad1229e90dfc8f54fccb8abe30545a4/studio/Studio01.md#L23) [Studio01.md:27](https://github.com/NickGuAI/agentic-engineering-course/blob/474fbf7b7ad1229e90dfc8f54fccb8abe30545a4/studio/Studio01.md#L27)

### Keep the delegation precise

Use exactly **Task, Context, Success criteria, Restrictions**. [workspace.md:27](https://github.com/NickGuAI/agentic-engineering-course/blob/474fbf7b7ad1229e90dfc8f54fccb8abe30545a4/studio/README.md#L27)

Learning example (assistant-created, not a course requirement): “Turn these three files into a study digest; every requirement needs a source; if one file is missing, report the missing filename and stop.” This is more testable than “help me study” because a reader can check both success and refusal to proceed.

### Submission checklist

- Keep work directly under `studio/<username-or-team>/`, not a `studio-01` subfolder. [workspace.md:7](https://github.com/NickGuAI/agentic-engineering-course/blob/474fbf7b7ad1229e90dfc8f54fccb8abe30545a4/studio/README.md#L7)
- Preserve code, outputs, and the completed card. [Studio01.md:29](https://github.com/NickGuAI/agentic-engineering-course/blob/474fbf7b7ad1229e90dfc8f54fccb8abe30545a4/studio/Studio01.md#L29)
- Each student personally writes a separate `explanation-<username>.md`, without AI-generated text. [workspace.md:31](https://github.com/NickGuAI/agentic-engineering-course/blob/474fbf7b7ad1229e90dfc8f54fccb8abe30545a4/studio/README.md#L31)
- Use a dedicated non-main working branch and a PR to the course repository's `main`. [workspace.md:40](https://github.com/NickGuAI/agentic-engineering-course/blob/474fbf7b7ad1229e90dfc8f54fccb8abe30545a4/studio/README.md#L40) [workspace.md:42](https://github.com/NickGuAI/agentic-engineering-course/blob/474fbf7b7ad1229e90dfc8f54fccb8abe30545a4/studio/README.md#L42)
- Delete the working branch only after confirming a successful merge; preserve unmerged work. [workspace.md:43](https://github.com/NickGuAI/agentic-engineering-course/blob/474fbf7b7ad1229e90dfc8f54fccb8abe30545a4/studio/README.md#L43)
- Check CourseWorks for official submission instructions and deadlines. No deadline is supplied by these inputs. [workspace.md:45](https://github.com/NickGuAI/agentic-engineering-course/blob/474fbf7b7ad1229e90dfc8f54fccb8abe30545a4/studio/README.md#L45)

## Preparation check

The listed accounts are GitHub, ChatGPT, Gemini, and Tavily. [course-prep.md:11](https://github.com/NickGuAI/agentic-engineering-course/blob/474fbf7b7ad1229e90dfc8f54fccb8abe30545a4/docs/course-prep.md#L11) [course-prep.md:12](https://github.com/NickGuAI/agentic-engineering-course/blob/474fbf7b7ad1229e90dfc8f54fccb8abe30545a4/docs/course-prep.md#L12) [course-prep.md:13](https://github.com/NickGuAI/agentic-engineering-course/blob/474fbf7b7ad1229e90dfc8f54fccb8abe30545a4/docs/course-prep.md#L13) [course-prep.md:14](https://github.com/NickGuAI/agentic-engineering-course/blob/474fbf7b7ad1229e90dfc8f54fccb8abe30545a4/docs/course-prep.md#L14)

Python 3.11+ and Git are required; no GPU is required. [course-prep.md:19](https://github.com/NickGuAI/agentic-engineering-course/blob/474fbf7b7ad1229e90dfc8f54fccb8abe30545a4/docs/course-prep.md#L19)
The preparation guide says there is no coding assignment *before the first class*. This does not waive the separate Studio 01 deliverables. [course-prep.md:6](https://github.com/NickGuAI/agentic-engineering-course/blob/474fbf7b7ad1229e90dfc8f54fccb8abe30545a4/docs/course-prep.md#L6)

## Self-check (assistant-created study questions)

1. Why is an output alone insufficient to understand an agent run?
2. What should happen if one required source is missing?
3. Which part of this studio must not be written by the agent?

<details><summary>Check your understanding</summary>

1. The trace shows what inputs and checks produced the output, so a plausible-looking result can be inspected rather than trusted blindly. This is a learning interpretation of Run & Inspect.
2. In this assistant's delegation contract, stop and name the missing input. The workshop itself also allows a responsible stop; this specific behavior is our implementation choice.
3. The student's separate personal explanation. Inspect the evidence and write it yourself.

</details>

## Scope and uncertainty

This small offline renderer is intentionally limited to these pinned Studio 01 materials. It does not claim to summarize lectures not provided, infer grades, discover deadlines, or measure LLM quality. Updating a source requires reviewing the content and its citation phrases before updating the pin; blindly accepting new hashes is not a correction.
