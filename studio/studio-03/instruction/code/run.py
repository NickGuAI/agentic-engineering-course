#!/usr/bin/env python3
"""Run one fresh Studio 03 condition for a team."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


CODE_DIR = Path(__file__).resolve().parent
STUDIO_DIR = CODE_DIR.parent.parent
SUBMISSION_ROOT = STUDIO_DIR / "submission"
DEFAULT_QUESTION = CODE_DIR / "question.txt"
DEFAULT_MODEL = "gpt-5.6-luna"
DEFAULT_CALL_BUDGET = 8
DEFAULT_TIMEOUT = 45
REASONING_EFFORT = "none"
TEAM_RE = re.compile(r"^[A-Za-z0-9._-]{1,40}$")

sys.path.insert(0, str(CODE_DIR))
from support import MAX_OUTPUT_TOKENS, RunContext  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--team", required=True)
    parser.add_argument("--mode", choices=("react", "plan"), required=True)
    parser.add_argument("--question-file", type=Path)
    parser.add_argument("--plan-file", type=Path)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--call-budget", type=int, default=DEFAULT_CALL_BUDGET)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    args = parser.parse_args()
    if args.team in {"_template", ".", ".."} or not TEAM_RE.fullmatch(args.team):
        parser.error("--team must be a simple team name, not _template")
    if args.call_budget < 1 or args.timeout < 1:
        parser.error("call budget and timeout must be positive")
    if args.plan_file and args.mode != "plan":
        parser.error("--plan-file is only used in plan mode")
    return args


def load_agent(path, run_id):
    module_name = f"studio03_team_agent_{run_id.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError("Could not load submission agent.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "run_agent", None)):
        raise AttributeError("agent.py must define run_agent(question, context).")
    return module


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    args = parse_args()
    team_dir = SUBMISSION_ROOT / args.team
    agent_path = team_dir / "agent.py"
    if not agent_path.is_file():
        print(f"Missing team agent: {agent_path}", file=sys.stderr)
        return 2
    question_path = args.question_file or DEFAULT_QUESTION
    if not question_path.is_file():
        print(f"Missing question file: {question_path}", file=sys.stderr)
        return 2

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8]
    output_dir = team_dir / "evidence" / args.mode / run_id
    output_dir.mkdir(parents=True, exist_ok=False)
    context = RunContext(None, args.model, args.mode, output_dir, args.call_budget)
    question = question_path.read_text(encoding="utf-8").strip()
    plan_text = args.plan_file.read_text(encoding="utf-8").strip() if args.plan_file else None
    if args.mode == "react":
        context.write_plan("Not used in ReAct mode.", "not_applicable")
    elif plan_text is not None:
        context.plan_text = plan_text
        context.write_plan(plan_text, "human_file")
    else:
        context.plan_origin = "model_pending"
        (output_dir / "plan.md").write_text("Not generated yet.\n", encoding="utf-8")
        context.event("plan_pending", origin=context.plan_origin)

    context.event(
        "run_started",
        team=args.team,
        run_id=run_id,
        mode=args.mode,
        question=question,
        model=args.model,
        reasoning_effort=REASONING_EFFORT,
        store=False,
        parallel_tool_calls=False,
        max_output_tokens=MAX_OUTPUT_TOKENS,
        call_budget=args.call_budget,
        plan_origin=context.plan_origin,
    )
    report = ""
    try:
        from dotenv import load_dotenv

        load_dotenv(CODE_DIR / ".env")
        from openai import OpenAI

        context.client = OpenAI(max_retries=0, timeout=args.timeout)
        agent = load_agent(agent_path, run_id)
        answer = agent.run_agent(question, context)
        if answer is not None and not isinstance(answer, str):
            raise TypeError("run_agent must return text or None.")
        if answer:
            report = context.clean_text(answer)
            if context.status == "running":
                context.status = "completed"
                context.stop_reason = None
        elif context.status == "running":
            context.fail("no_final_answer")
    except Exception as error:
        context.fail("runner_error", error)

    if not report:
        report = f"No final answer. Stop reason: {context.stop_reason or 'unknown'}.\n"
    (output_dir / "report.md").write_text(report.rstrip() + "\n", encoding="utf-8")
    context.event(
        "run_finished",
        status=context.status,
        stop_reason=context.stop_reason,
        escalation_required=context.escalation_required,
    )
    write_json(output_dir / "summary.json", context.summary(args.team, run_id, REASONING_EFFORT))
    print(f"status={context.status} evidence={output_dir}")
    if context.escalation_required:
        print(f"escalation_required=true stop_reason={context.stop_reason}")
    return 0 if context.status == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
