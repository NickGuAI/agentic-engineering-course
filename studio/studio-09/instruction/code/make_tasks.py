"""Turn question records into Harbor tasks without putting keys in the image."""

import argparse
import json
import re
import shutil
from datetime import date
from pathlib import Path
from urllib.parse import urlparse


def read_questions(path: Path) -> list[dict]:
    rows = []
    seen = set()
    for line_number, line in enumerate(path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError("each line must be a JSON object")
            if not re.fullmatch(r"q(?:0[1-9]|10)", row.get("id", "")):
                raise ValueError("id must be q01 through q10")
            if row["id"] in seen:
                raise ValueError(f"duplicate id {row['id']}")
            for key in ("question", "answer", "pass_rule", "written_on"):
                if not isinstance(row.get(key), str) or not row[key].strip():
                    raise ValueError(f"{key} must be nonempty text")
            date.fromisoformat(row["written_on"])
            if not isinstance(row.get("sources"), list) or not row["sources"]:
                raise ValueError("sources must be a nonempty list of URLs")
            for source in row["sources"]:
                parsed = urlparse(source)
                if parsed.scheme not in ("http", "https") or not parsed.netloc:
                    raise ValueError("each source must be an HTTP or HTTPS URL")
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError(f"{path.name}:{line_number}: {exc}") from exc
        seen.add(row["id"])
        rows.append(row)
    if not rows:
        raise ValueError("questions file is empty")
    return rows


def make_tasks(questions: Path, output: Path) -> int:
    rows = read_questions(questions)
    # Validate the entire input before writing; never leave stale keys in a task.
    if output.exists():
        raise ValueError(f"{output} already exists; choose a new output directory")
    template = Path(__file__).resolve().parent / "task-template"
    output.mkdir(parents=True)
    for row in rows:
        task = output / row["id"]
        shutil.copytree(template, task, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        instruction = (template / "instruction.md").read_text()
        (task / "instruction.md").write_text(instruction.replace("{{QUESTION}}", row["question"]))
        (task / "tests" / "answer.json").write_text(json.dumps(row, indent=2) + "\n")
        oracle_answer = row["answer"] + "\n\nSources:\n" + "\n".join(row["sources"]) + "\n"
        (task / "solution" / "answer.md").write_text(oracle_answer)
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("questions", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--team", required=True, help="Your team name; run inside its submission folder")
    args = parser.parse_args()
    try:
        count = make_tasks(args.questions, args.output)
    except ValueError as exc:
        parser.error(str(exc))
    print(f"Created {count} tasks in {args.output} for {args.team}.")


if __name__ == "__main__":
    main()
