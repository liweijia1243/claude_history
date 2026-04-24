import hashlib
import json
import os
import sqlite3
from collections import defaultdict
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Any, DefaultDict, Dict, List, Optional, Tuple

from .base import HistoryProvider
from .models import make_message, make_tool_result, make_tool_use


class CodexProvider(HistoryProvider):
    id = "codex"
    name = "Codex"

    def __init__(self, root: Optional[Path] = None):
        self.root = root or Path(os.path.expanduser("~/.codex"))
        self.state_db = self.root / "state_5.sqlite"

    def available(self) -> bool:
        return self.state_db.exists()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.state_db))
        conn.row_factory = sqlite3.Row
        return conn

    def _read_threads(self) -> List[Dict[str, Any]]:
        if not self.available():
            return []

        with closing(self._connect()) as conn:
            rows = conn.execute(
                """
                SELECT id, rollout_path, created_at, updated_at, source, model_provider, cwd,
                       title, tokens_used, archived, git_sha, git_branch, git_origin_url,
                       first_user_message, model, reasoning_effort, created_at_ms, updated_at_ms
                FROM threads
                WHERE archived = 0
                ORDER BY COALESCE(updated_at_ms, updated_at * 1000) DESC, id DESC
                """
            ).fetchall()

        return [dict(row) for row in rows]

    @staticmethod
    def _project_id(cwd: str) -> str:
        return hashlib.sha1(cwd.encode("utf-8")).hexdigest()[:12]

    @staticmethod
    def _display_name(cwd: str) -> str:
        clean = cwd.rstrip("/")
        return clean.split("/")[-1] if clean else cwd

    @staticmethod
    def _thread_preview(thread: Dict[str, Any]) -> str:
        return thread.get("first_user_message") or thread.get("title") or ""

    @staticmethod
    def _thread_modified_seconds(thread: Dict[str, Any]) -> float:
        updated_at_ms = thread.get("updated_at_ms")
        if updated_at_ms is not None:
            return updated_at_ms / 1000
        return float(thread.get("updated_at") or 0)

    @staticmethod
    def _thread_created_seconds(thread: Dict[str, Any]) -> float:
        created_at_ms = thread.get("created_at_ms")
        if created_at_ms is not None:
            return created_at_ms / 1000
        return float(thread.get("created_at") or 0)

    def _thread_sort_key(self, thread: Dict[str, Any]) -> Tuple[float, str]:
        return self._thread_modified_seconds(thread), thread.get("id") or ""

    def _project_map(self) -> Dict[str, List[Dict[str, Any]]]:
        groups = defaultdict(list)  # type: DefaultDict[str, List[Dict[str, Any]]]
        for thread in self._read_threads():
            groups[thread.get("cwd") or ""].append(thread)
        return dict(groups)

    @staticmethod
    def _count_rollout_lines(path: Path) -> int:
        if not path.exists():
            return 0

        with path.open("r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())

    def _session_summary(self, thread: Dict[str, Any]) -> Dict[str, Any]:
        rollout = Path(thread.get("rollout_path") or "")
        size = rollout.stat().st_size if rollout.exists() else 0
        return {
            "id": thread.get("id", ""),
            "preview": self._thread_preview(thread)[:200],
            "message_count": self._count_rollout_lines(rollout),
            "message_types": {},
            "size": size,
            "created": self._thread_created_seconds(thread),
            "modified": self._thread_modified_seconds(thread),
            "first_timestamp": thread.get("created_at_ms") or "",
            "last_timestamp": thread.get("updated_at_ms") or "",
            "title": thread.get("title") or "",
            "model": thread.get("model") or "",
            "reasoning_effort": thread.get("reasoning_effort") or "",
            "source": self.id,
        }

    def _find_project_threads(self, project_id: str) -> Tuple[str, List[Dict[str, Any]]]:
        for cwd, threads in self._project_map().items():
            if self._project_id(cwd) == project_id:
                return cwd, sorted(
                    threads,
                    key=self._thread_sort_key,
                    reverse=True,
                )
        raise FileNotFoundError("Project not found")

    def get_stats(self) -> Dict[str, Any]:
        threads = self._read_threads()
        projects = {thread.get("cwd", "") for thread in threads}
        history = self.get_history(page=1, limit=1000000, search=None, project=None)["items"]
        now_ms = datetime.now().timestamp() * 1000
        day_ago = now_ms - 86400000
        recent = sum(1 for item in history if (item.get("timestamp") or 0) > day_ago)
        return {
            "total_commands": len(history),
            "total_plans": 0,
            "total_projects": len(projects),
            "total_sessions": len(threads),
            "recent_commands_24h": recent,
        }

    def get_dashboard_stats(self, range_str: str) -> Dict[str, Any]:
        stats = self.get_stats()
        threads = self._read_threads()
        total_tokens = sum(thread.get("tokens_used") or 0 for thread in threads)
        return {
            "summary": {
                "total_commands": stats["total_commands"],
                "total_sessions": stats["total_sessions"],
                "total_projects": stats["total_projects"],
                "total_tokens": {"input": total_tokens, "output": 0},
            },
            "changes": {
                "commands_pct": 0,
                "sessions_pct": 0,
                "projects_new": 0,
                "tokens_pct": 0,
            },
            "daily_series": [],
            "message_types": {},
            "top_projects": [
                {
                    "project_id": project["id"],
                    "project_name": project["display_name"],
                    "session_count": project["session_count"],
                }
                for project in self.list_projects()[:5]
            ],
            "hourly_distribution": [0] * 24,
            "session_durations": {
                "under_5min": 0,
                "5_to_15min": 0,
                "15_to_30min": 0,
                "30_to_60min": 0,
                "over_60min": 0,
            },
        }

    def get_recent_sessions(self, limit: int) -> List[Dict[str, Any]]:
        sessions = []
        project_ids = {project["path"]: project["id"] for project in self.list_projects()}
        for thread in self._read_threads():
            summary = self._session_summary(thread)
            summary.update(
                {
                    "session_id": thread.get("id", ""),
                    "project_id": project_ids.get(thread.get("cwd", ""), ""),
                    "project_path": thread.get("cwd", ""),
                    "timestamp": self._thread_modified_seconds(thread),
                }
            )
            sessions.append(summary)

        sessions.sort(key=lambda item: item.get("timestamp") or 0, reverse=True)
        return sessions[:limit]

    def get_history(
        self,
        page: int,
        limit: int,
        search: Optional[str],
        project: Optional[str],
    ) -> Dict[str, Any]:
        history_path = self.root / "history.jsonl"
        threads = {thread["id"]: thread for thread in self._read_threads()}
        items = []

        if history_path.exists():
            with history_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        raw = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    session_id = raw.get("session_id", "")
                    thread = threads.get(session_id, {})
                    cwd = thread.get("cwd", "")
                    display = raw.get("text", "")
                    if search and search.lower() not in display.lower():
                        continue
                    if project and project not in cwd and project != self._project_id(cwd):
                        continue

                    items.append(
                        {
                            "sessionId": session_id,
                            "timestamp": raw.get("ts", 0),
                            "display": display,
                            "project": cwd,
                            "project_id": self._project_id(cwd) if cwd else "",
                            "source": self.id,
                        }
                    )

        items.sort(key=lambda item: item.get("timestamp") or 0, reverse=True)
        total = len(items)
        start = (page - 1) * limit
        page_items = items[start : start + limit]
        return {
            "items": page_items,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit,
        }

    def list_projects(self) -> List[Dict[str, Any]]:
        projects = []
        project_map = self._project_map()
        for cwd, threads in project_map.items():
            size = 0
            for thread in threads:
                rollout = Path(thread.get("rollout_path") or "")
                if rollout.exists():
                    size += rollout.stat().st_size

            newest_updated = max((self._thread_modified_seconds(thread) for thread in threads), default=0)
            projects.append(
                {
                    "id": self._project_id(cwd),
                    "path": cwd,
                    "display_name": self._display_name(cwd),
                    "session_count": len(threads),
                    "size": size,
                    "source": self.id,
                    "modified": newest_updated,
                }
            )

        projects.sort(key=lambda project: project.get("modified") or 0, reverse=True)
        return projects

    def get_project(self, project_id: str) -> Dict[str, Any]:
        cwd, threads = self._find_project_threads(project_id)
        return {
            "id": project_id,
            "path": cwd,
            "display_name": self._display_name(cwd),
            "source": self.id,
            "sessions": [self._session_summary(thread) for thread in threads],
        }

    def list_sessions(self, project_id: str) -> List[Dict[str, Any]]:
        return self.get_project(project_id)["sessions"]

    @staticmethod
    def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
        items = []
        if not path.exists():
            return items

        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(raw, dict):
                    items.append(raw)
        return items

    @staticmethod
    def _content_text(content: Any) -> str:
        if isinstance(content, str):
            return content
        if not isinstance(content, list):
            return ""

        parts = []
        for block in content:
            if isinstance(block, dict):
                text = block.get("text")
                if text:
                    parts.append(text)
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)

    @staticmethod
    def _parse_arguments(raw: Any) -> Dict[str, Any]:
        if not raw:
            return {}
        if isinstance(raw, dict):
            return raw
        try:
            parsed = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return {"arguments": raw}
        if isinstance(parsed, dict):
            return parsed
        return {"arguments": parsed}

    @classmethod
    def _reasoning_text(cls, payload: Dict[str, Any]) -> Tuple[str, bool]:
        content = payload.get("content")
        text = cls._content_text(content)
        if text:
            return text, False

        summary = payload.get("summary")
        if isinstance(summary, list):
            parts = []
            for item in summary:
                if isinstance(item, dict) and item.get("text"):
                    parts.append(item["text"])
                elif isinstance(item, str):
                    parts.append(item)
            if parts:
                return "\n".join(parts), False
        elif isinstance(summary, str) and summary:
            return summary, False

        if payload.get("encrypted_content"):
            return "[Encrypted reasoning available]", True
        return "", False

    @staticmethod
    def _result_content(payload: Dict[str, Any]) -> str:
        content = (
            payload.get("formatted_output")
            or payload.get("aggregated_output")
            or payload.get("output")
        )
        if content:
            return content
        return "\n".join(part for part in [payload.get("stdout", ""), payload.get("stderr", "")] if part)

    def _reconstruct_rollout(
        self,
        events: List[Dict[str, Any]],
        thread: Dict[str, Any],
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        conversation = []
        current_assistant = None  # type: Optional[Dict[str, Any]]
        tool_owner = {}  # type: Dict[str, Dict[str, Any]]
        metadata = {
            "cwd": thread.get("cwd", ""),
            "title": thread.get("title", ""),
            "model": thread.get("model") or "",
            "model_provider": thread.get("model_provider") or "",
            "reasoning_effort": thread.get("reasoning_effort") or "",
            "source": thread.get("source") or "",
            "source_provider": self.id,
            "codex_source": thread.get("source") or "",
            "internal_message_counts": {},
        }

        def ensure_assistant(timestamp: Any = "") -> Dict[str, Any]:
            nonlocal current_assistant
            if current_assistant is None:
                current_assistant = make_message(
                    role="assistant",
                    model=thread.get("model") or "",
                    timestamp=timestamp,
                    metadata={"source": self.id},
                )
            return current_assistant

        def flush_assistant() -> None:
            nonlocal current_assistant
            if current_assistant is not None:
                conversation.append(current_assistant)
                current_assistant = None

        def append_assistant_text(assistant: Dict[str, Any], text: str) -> None:
            if text:
                assistant["content"] = "\n".join(part for part in [assistant.get("content", ""), text] if part)

        for event in events:
            timestamp = event.get("timestamp", "")
            payload = event.get("payload") or {}
            if not isinstance(payload, dict):
                payload = {}
            payload_type = payload.get("type")
            event_type = event.get("type")

            if event_type == "session_meta":
                metadata.update(
                    {
                        "cwd": payload.get("cwd", metadata.get("cwd", "")),
                        "source": payload.get("source", metadata.get("source", "")),
                        "source_provider": self.id,
                        "codex_source": payload.get("source", ""),
                        "model_provider": payload.get("model_provider", ""),
                        "git": payload.get("git", {}),
                        "dynamic_tools": payload.get("dynamic_tools", []),
                    }
                )
                continue

            if event_type == "turn_context" or payload_type == "turn_context":
                metadata.update(
                    {
                        "approval_policy": payload.get("approval_policy", ""),
                        "sandbox_policy": payload.get("sandbox_policy", {}),
                        "current_date": payload.get("current_date", ""),
                        "timezone": payload.get("timezone", ""),
                    }
                )
                continue

            if event_type == "token_count" or payload_type == "token_count":
                metadata["last_token_count"] = payload
                continue

            if payload_type == "user_message":
                flush_assistant()
                conversation.append(
                    make_message(
                        role="user",
                        content=payload.get("message", ""),
                        timestamp=timestamp,
                        metadata={
                            "images": payload.get("images", []),
                            "local_images": payload.get("local_images", []),
                            "text_elements": payload.get("text_elements", []),
                            "source": self.id,
                        },
                    )
                )
                continue

            if payload_type == "message":
                role = payload.get("role", "assistant")
                if role == "assistant":
                    append_assistant_text(ensure_assistant(timestamp), self._content_text(payload.get("content")))
                else:
                    counts = metadata["internal_message_counts"]
                    counts[role] = counts.get(role, 0) + 1
                continue

            if payload_type == "reasoning":
                assistant = ensure_assistant(timestamp)
                text, encrypted = self._reasoning_text(payload)
                if text:
                    assistant["thinking"] = "\n".join(
                        part for part in [assistant.get("thinking", ""), text] if part
                    )
                if encrypted:
                    assistant["metadata"]["reasoning_encrypted"] = True
                    metadata["reasoning_encrypted"] = True
                continue

            if payload_type == "function_call":
                assistant = ensure_assistant(timestamp)
                call_id = payload.get("call_id", "")
                assistant["tool_uses"].append(
                    make_tool_use(
                        call_id,
                        payload.get("name", ""),
                        self._parse_arguments(payload.get("arguments", "")),
                        {"provider": self.id},
                    )
                )
                if call_id:
                    tool_owner[call_id] = assistant
                continue

            if payload_type in ("function_call_output", "exec_command_end"):
                call_id = payload.get("call_id", "")
                owner = tool_owner.get(call_id) or ensure_assistant(timestamp)
                if call_id and call_id not in tool_owner:
                    owner["tool_uses"].append(
                        make_tool_use(
                            call_id,
                            "exec_command" if payload_type == "exec_command_end" else "function_call_output",
                            {
                                "command": payload.get("command", []),
                                "cwd": payload.get("cwd", ""),
                            },
                            {"provider": self.id, "synthetic": True},
                        )
                    )
                    tool_owner[call_id] = owner
                owner["tool_results"].append(
                    make_tool_result(
                        call_id,
                        self._result_content(payload),
                        bool(payload.get("exit_code")),
                        {
                            "exit_code": payload.get("exit_code"),
                            "cwd": payload.get("cwd", ""),
                            "command": payload.get("command", []),
                            "stdout": payload.get("stdout", ""),
                            "stderr": payload.get("stderr", ""),
                            "duration": payload.get("duration"),
                            "status": payload.get("status"),
                            "parsed_cmd": payload.get("parsed_cmd", []),
                        },
                    )
                )
                continue

            if payload_type == "agent_message":
                flush_assistant()
                phase = payload.get("phase", "")
                role = "assistant" if phase in ("final", "message", "response") else "event"
                conversation.append(
                    make_message(
                        role=role,
                        content=payload.get("message", ""),
                        timestamp=timestamp,
                        metadata={"phase": phase, "source": self.id},
                    )
                )
                continue

        flush_assistant()
        return conversation, metadata

    def get_session(self, project_id: str, session_id: str) -> Dict[str, Any]:
        cwd, threads = self._find_project_threads(project_id)
        thread = next((item for item in threads if item.get("id") == session_id), None)
        if not thread:
            raise FileNotFoundError("Session not found")

        rollout = Path(thread.get("rollout_path") or "")
        if not rollout.exists():
            raise FileNotFoundError("Session not found")

        events = self._read_jsonl(rollout)
        conversation, metadata = self._reconstruct_rollout(events, thread)
        metadata["cwd"] = cwd
        return {
            "session_id": session_id,
            "project_id": project_id,
            "source": self.id,
            "total_raw_messages": len(events),
            "conversation": conversation,
            "subagents": [],
            "metadata": metadata,
        }
