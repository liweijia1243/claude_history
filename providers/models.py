from typing import Any, Dict, List, Optional, Union


def make_message(
    role: str,
    content: str = "",
    thinking: str = "",
    tool_uses: Optional[List[Dict[str, Any]]] = None,
    tool_results: Optional[List[Dict[str, Any]]] = None,
    model: str = "",
    usage: Optional[Dict[str, Any]] = None,
    timestamp: Union[str, int, float] = "",
    uuid: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
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
    input_data: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
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
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "tool_use_id": tool_use_id,
        "content": content,
        "is_error": is_error,
        "metadata": metadata or {},
    }
