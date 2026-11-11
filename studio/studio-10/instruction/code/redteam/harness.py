"""Shared Slack runner. Tool execution and success checks belong to AgentDojo."""

import json
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from string import Formatter

import openai
from agentdojo.agent_pipeline import OpenAILLM
from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline, PipelineConfig
from agentdojo.attacks.attack_registry import load_attack
from agentdojo.attacks.base_attacks import FixedJailbreakAttack
from agentdojo.benchmark import run_task_with_injection_tasks, run_task_without_injection_tasks
from agentdojo.logging import OutputLogger
from agentdojo.task_suite.load_suites import get_suite

from .defenses import install_transform, load_defense
from .models import MODELS, resolve_model

GOALS = {
    "injection": "injection_task_1",
    "exfiltration": "injection_task_2",
    "unauthorized": "injection_task_5",
}
STOCK_ATTACKS = ("direct", "ignore_previous", "system_message", "injecagent", "important_instructions")


@dataclass(frozen=True)
class AttackSpec:
    id: str
    type: str
    target_goal: str
    user_tasks: tuple[str, ...]
    template: str


def positive_int(value):
    number = int(value)
    if number < 1:
        raise ValueError("runs must be at least 1")
    return number


def add_arguments(parser):
    parser.add_argument("--attacks", required=True, type=Path, help="JSON file or directory of attack JSON files")
    parser.add_argument("--model", choices=MODELS, default="luna")
    parser.add_argument("--model-id", help="Override the model id for the selected alias")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--runs", type=positive_int, default=5)
    parser.add_argument("--logdir", type=Path, help="Private raw traces; default work/<output stem>/<unique run>")


def read_attacks(path: Path, suite) -> list[AttackSpec]:
    paths = sorted(path.glob("*.json")) if path.is_dir() else [path]
    if not paths:
        raise ValueError(f"No attack JSON files in {path}")
    attacks = []
    ids = set()
    for file in paths:
        data = json.loads(file.read_text())
        kind = data["type"]
        if kind not in GOALS or data["target_goal"] != GOALS[kind]:
            raise ValueError(f"{file}: type must map to its fixed goal in {GOALS}")
        ident = data.get("id", file.stem)
        if not isinstance(ident, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", ident) or ident in ids:
            raise ValueError(f"{file}: id must be unique and contain only letters, digits, _ or -")
        tasks = data["user_tasks"]
        if not isinstance(tasks, list) or not tasks or any(not isinstance(t, str) for t in tasks):
            raise ValueError(f"{file}: user_tasks must be a nonempty list of task ids")
        if len(tasks) != len(set(tasks)):
            raise ValueError(f"{file}: duplicate user task")
        for task in tasks:
            suite.get_user_task_by_id(task)
        suite.get_injection_task_by_id(data["target_goal"])
        template = data["template"]
        if not isinstance(template, str) or "{goal}" not in template:
            raise ValueError(f"{file}: template must contain a {{goal}} slot")
        for _, field, format_spec, conversion in Formatter().parse(template):
            if field is not None and (field != "goal" or format_spec or conversion):
                raise ValueError(f"{file}: only the plain {{goal}} format slot is allowed")
        if "{" in template.replace("{goal}", "") or "}" in template.replace("{goal}", ""):
            raise ValueError(f"{file}: braces are allowed only in the {{goal}} slot")
        if any(suite.get_user_task_by_id(t).PROMPT in template for t in tasks):
            raise ValueError(f"{file}: do not embed the user-task prompt in injected text")
        ids.add(ident)
        attacks.append(AttackSpec(ident, kind, data["target_goal"], tuple(tasks), template))
    return attacks


def yaml_safe(content: str) -> str:
    """Keep injected text safe for AgentDojo's YAML environment substitution."""
    content = content.replace('"', "'").replace("{", "(").replace("}", ")").replace(": ", " - ")
    content = "\n".join(line.replace("---", "—", 1) if line.lstrip().startswith("---") else line for line in content.split("\n"))
    # Slack's placeholders sit inside double-quoted YAML strings. JSON escaping
    # preserves literal backslashes/newlines when that environment is parsed.
    return json.dumps(content, ensure_ascii=False)[1:-1]


class TemplateAttack(FixedJailbreakAttack):
    name = "team"

    def attack(self, user_task, injection_task):
        content = yaml_safe(self.jailbreak.format(goal=injection_task.GOAL))
        return {candidate: content for candidate in self.get_injection_candidates(user_task)}


def force_gpt6_reasoning_off(client):
    """Cover both OpenAILLM and OpenAILLMToolFilter on this shared client."""
    original = client.chat.completions.create

    def create(*args, **kwargs):
        if str(kwargs.get("model", "")).startswith("gpt-6"):
            kwargs["reasoning_effort"] = "none"
            kwargs.pop("temperature", None)
        elif str(kwargs.get("model", "")).startswith("gpt-4o"):
            # AgentDojo's `temperature or NOT_GIVEN` otherwise drops zero.
            kwargs["temperature"] = 0.0
        return original(*args, **kwargs)

    client.chat.completions.create = create


def build_pipeline(alias: str, model_id: str | None = None, defense: str | None = None):
    model = resolve_model(alias, model_id)
    builtin, transform, name = load_defense(defense) if defense else (None, None, "none")
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ValueError("Pass OPENAI_API_KEY in the environment for this run")
    client = openai.OpenAI(api_key=key)
    force_gpt6_reasoning_off(client)
    llm = OpenAILLM(client, model, temperature=0.0 if model.startswith("gpt-4o") else None)
    llm.name = model
    pipeline = AgentPipeline.from_config(PipelineConfig(
        llm=llm, model_id=None, defense=builtin, system_message_name=None, system_message=None,
    ))
    pipeline.name = f"local-{model}-{name}"
    if transform is not None:
        install_transform(pipeline, transform)
    return pipeline, name


def stock_specs(specs, suite, pipeline):
    """Use upstream templates on the goal/task grid supplied by --attacks."""
    result = []
    for stock_name in STOCK_ATTACKS:
        stock = load_attack(stock_name, suite, pipeline)
        template = stock.jailbreak.format(
            goal="{goal}", user=stock.user_name, model=stock.model_name, task="",
        )
        for spec in specs:
            result.append(AttackSpec(
                f"stock-{stock_name}-{spec.id}", spec.type, spec.target_goal, spec.user_tasks, template,
            ))
    return result


def trace_root(args) -> Path:
    root = (args.logdir or Path("work") / args.out.stem) / uuid.uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    print(f"Raw traces: {root}", flush=True)
    return root


def check_trace(logdir: Path):
    """AgentDojo handles some API errors internally; never count those as successes."""
    traces = list(logdir.rglob("*.json"))
    if len(traces) != 1:
        raise RuntimeError(f"Expected one task trace under {logdir}; found {len(traces)}")
    trace = json.loads(traces[0].read_text())
    if trace.get("error"):
        raise RuntimeError(f"AgentDojo reported a trial error; inspect {traces[0]}")
    return trace


def run_attacks(suite, pipeline, specs, runs: int, logdir: Path) -> list[dict]:
    rows = []
    for index, spec in enumerate(specs):
        attack = TemplateAttack(spec.template, suite, pipeline)
        attack.name = spec.id
        for task_id in spec.user_tasks:
            outcomes = []
            for attempt in range(runs):
                trial_dir = logdir / f"attack-{index}" / task_id / f"run-{attempt + 1}"
                trial_dir.mkdir(parents=True, exist_ok=True)
                print(f"{spec.id} / {task_id} / run {attempt + 1}/{runs}", flush=True)
                with OutputLogger(str(trial_dir), live=None):
                    _, security = run_task_with_injection_tasks(
                        suite, pipeline, suite.get_user_task_by_id(task_id), attack,
                        logdir=trial_dir, force_rerun=True, injection_tasks=[spec.target_goal],
                    )
                trace = check_trace(trial_dir)
                success = security[(task_id, spec.target_goal)]
                if type(success) is not bool or trace.get("security") != success:
                    raise RuntimeError("Invalid or inconsistent AgentDojo attack result")
                outcomes.append(success)
            rows.append({
                "id": spec.id, "type": spec.type, "target_goal": spec.target_goal,
                "user_task": task_id, "runs": outcomes, "cracked": any(outcomes),
            })
    return rows


def task_completion(suite, pipeline, tasks, logdir: Path) -> int:
    completed = 0
    for task_id in tasks:
        trial_dir = logdir / task_id
        trial_dir.mkdir(parents=True, exist_ok=True)
        print(f"Clean completion / {task_id}", flush=True)
        with OutputLogger(str(trial_dir), live=None):
            utility, _ = run_task_without_injection_tasks(
                suite, pipeline, suite.get_user_task_by_id(task_id), logdir=trial_dir, force_rerun=True,
            )
        trace = check_trace(trial_dir)
        if type(utility) is not bool or trace.get("utility") != utility:
            raise RuntimeError("Invalid or inconsistent AgentDojo completion result")
        completed += utility
    return completed


def write_json(path: Path, result):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)
    print(f"Wrote {path}", flush=True)


def slack_suite():
    return get_suite("v1.2", "slack")
