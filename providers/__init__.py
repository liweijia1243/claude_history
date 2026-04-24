from .codex import CodexProvider


_PROVIDERS = {
    "codex": CodexProvider(),
}


def get_provider(source: str):
    return _PROVIDERS.get(source)


def list_sources() -> list[dict]:
    return [
        {"id": provider.id, "name": provider.name, "available": provider.available()}
        for provider in _PROVIDERS.values()
    ]
