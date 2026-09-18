# COMS W4995-009: Agentic Engineering

This repository contains course materials for Columbia University, Fall 2026. Do not work directly in this public repository. Create a private repository for your team by cloning this repo and running `bash bootstrap.sh`; it creates `agentic-engineering-private` under your account. The GitHub Action "Sync course materials" merges daily upstream updates automatically. Sync on demand by running `git pull upstream main`.

## Repository Layout

- `studio/studio-0N/instruction/`: Course-owned instructions, rubrics, starter code, and reference evidence.
- `studio/studio-0N/submission/<team>/`: The exclusive directory for all your team's work.
- `studio/studio-0N/submission/_template/`: A template folder to copy for your submission. Do not edit this in place.
- `docs/`: Course preparation guide.
- `.github/workflows/`: Course-owned daily sync and secret-scanning automation workflows.

## Rules for Everyone

1. Do not modify any files under `instruction/`, `docs/`, `.github/`, `bootstrap.sh`, `README.md`, or `AGENTS.md`. To modify a starter script, copy it to your submission folder, change the copy, and explain why in your `EXPLANATION.md`.
2. Run all studio scripts with the `--team <team>` argument so evidence files land automatically in your submission folder.
3. Never commit API keys, `.env` files, `auth.json`, or local agent config/credentials. Use environment variables. The GitHub Action "Check for committed secrets" is a best-effort backstop, not a guarantee.
4. Do not commit raw session logs or downloaded/generated datasets. The `.gitignore` file already excludes patterns like `work/`, `benchmarks/babilong/`, and `*.raw.jsonl`.
5. Do not make your private repository public while it contains graded work unless all team members agree.
6. Do not remove the instructor (NickGuAI) or TAs (arielbenavi, thevoid12) as collaborators from your private repository before the semester ends.
7. If upstream sync fails, run `git pull upstream main` locally, resolve conflicts, commit, and push. Conflicts only occur if course-owned files are modified locally.

## Rules for Coding Agents

- Read the specific studio instruction file (e.g., `studio/studio-0N/instruction/Studio_Instruction.md`) before taking action.
- Write only within the team's `submission/<team>/` folder.
- Obtain explicit human confirmation regarding which model provider (such as OpenAI / ChatGPT / gpt-5.6-luna) to use before executing `setup.sh` or any Part A/B/C scripts, as they execute real API calls.

## Questions

Ask questions on CourseWorks: https://courseworks2.columbia.edu/courses/251648
