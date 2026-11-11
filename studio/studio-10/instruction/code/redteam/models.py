"""Class model aliases, in ladder order."""

MODELS = {
    "warmup": "gpt-4o-mini",
    "luna": "gpt-6-luna",
    "54mini": "gpt-5.4-mini",
    "55": "gpt-5.5",
    "sol": "gpt-6-sol",
    "terra": "gpt-6.1-terra",
}


def resolve_model(alias: str, model_id: str | None = None) -> str:
    """Allow only overrides that start with the alias's canonical model id."""
    canonical = MODELS[alias]
    if model_id is not None and not model_id.startswith(canonical):
        raise ValueError(
            f"--model-id {model_id!r} must start with {canonical!r} for --model {alias}"
        )
    return canonical if model_id is None else model_id
