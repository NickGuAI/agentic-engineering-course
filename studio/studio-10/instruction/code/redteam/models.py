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
    """An explicit dated model id overrides the selected alias."""
    return model_id or MODELS[alias]
