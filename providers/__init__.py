from typing import Any, Dict, List

from .claude import ClaudeProvider
from .codex import CodexProvider


_PROVIDERS = {
    "claude": ClaudeProvider(),
    "codex": CodexProvider(),
}


def get_provider(source: str):
    return _PROVIDERS.get(source)


def list_sources() -> List[Dict[str, Any]]:
    return [
        {"id": provider.id, "name": provider.name, "available": provider.available()}
        for provider in _PROVIDERS.values()
    ]
