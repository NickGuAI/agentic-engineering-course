"""AgentDojo built-ins and the team's tool-result text transform."""

import importlib.util
from pathlib import Path

from agentdojo.agent_pipeline.tool_execution import ToolsExecutionLoop, ToolsExecutor

BUILTINS = ("spotlighting_with_delimiting", "tool_filter", "repeat_user_prompt")


def load_defense(source: str):
    """Return (AgentDojo defense name, optional transform, display name)."""
    if source in BUILTINS:
        return source, None, source
    path = Path(source)
    if not path.is_file() or path.suffix != ".py":
        raise ValueError(f"Defense must be one of {BUILTINS} or a Python file")
    spec = importlib.util.spec_from_file_location("team_defense", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot load defense {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    transform = getattr(module, "transform", None)
    if not callable(transform):
        raise ValueError("Defense must define transform(content: str) -> str")
    name = getattr(module, "NAME", path.stem)
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Defense NAME must be a nonempty string")
    return None, transform, name


def install_transform(pipeline, transform):
    """Transform each newly serialized tool result once, before the LLM sees it."""
    count = 0
    for element in pipeline.elements:
        if isinstance(element, ToolsExecutionLoop):
            for step in element.elements:
                if isinstance(step, ToolsExecutor):
                    formatter = step.output_formatter

                    def defended_formatter(result, original=formatter):
                        content = transform(original(result))
                        if not isinstance(content, str):
                            raise TypeError("Defense transform must return str")
                        return content

                    step.output_formatter = defended_formatter
                    count += 1
    if count != 1:
        raise RuntimeError("Expected exactly one AgentDojo tool-result formatter")
