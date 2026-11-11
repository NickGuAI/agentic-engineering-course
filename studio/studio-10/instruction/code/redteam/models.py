"""Class model aliases, in ladder order."""

MODELS = {
    "warmup": "gpt-4o-mini",
    "luna": "gpt-6-luna",
    "54mini": "gpt-5.4-mini",
    "55": "gpt-5.5",
    "sol": "gpt-6-sol",
    "terra": "gpt-6.1-terra",
}


def valid_model_id(alias: str, model: str) -> bool:
    """Accept the canonical id or a hyphen suffix starting with a date digit."""
    canonical = MODELS.get(alias)
    if canonical is None or not isinstance(model, str):
        return False
    prefix = canonical + "-"
    return model == canonical or (
        model.startswith(prefix) and len(model) > len(prefix) and model[len(prefix)].isdigit()
    )


def resolve_model(alias: str, model_id: str | None = None) -> str:
    """Allow only canonical ids and dated variants for the selected alias."""
    canonical = MODELS[alias]
    if model_id is not None and not valid_model_id(alias, model_id):
        raise ValueError(
            f"--model-id {model_id!r} must equal {canonical!r} or start with "
            f"{canonical + '-'!r} followed by a digit for --model {alias}"
        )
    return canonical if model_id is None else model_id
