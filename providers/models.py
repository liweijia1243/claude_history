from typing import Any


def make_message(
    role: str,
    content: str = "",
    thinking: str = "",
    tool_uses: list[dict[str, Any]] | None = None,
    tool_results: list[dict[str, Any]] | None = None,
    model: str = "",
    usage: dict[str, Any] | None = None,
    timestamp: str | int | float = "",
    uuid: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "role": role,
        "content": content,
        "thinking": thinking,
        "tool_uses": tool_uses or [],
        "tool_results": tool_results or [],
        "model": model,
        "usage": usage or {},
        "timestamp": timestamp,
        "uuid": uuid,
        "metadata": metadata or {},
    }


def make_tool_use(
    tool_id: str,
    name: str,
    input_data: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": tool_id,
        "name": name,
        "input": input_data or {},
        "metadata": metadata or {},
    }


def make_tool_result(
    tool_use_id: str,
    content: str = "",
    is_error: bool = False,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "tool_use_id": tool_use_id,
        "content": content,
        "is_error": is_error,
        "metadata": metadata or {},
    }
