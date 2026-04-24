import hashlib
import json
import os
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, DefaultDict, Dict, List, Optional, Tuple

from .base import HistoryProvider


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

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, rollout_path, created_at, updated_at, source, model_provider, cwd,
                       title, tokens_used, archived, git_sha, git_branch, git_origin_url,
                       first_user_message, model, reasoning_effort, created_at_ms, updated_at_ms
                FROM threads
                WHERE archived = 0
                ORDER BY updated_at_ms DESC, id DESC
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
        if updated_at_ms:
            return updated_at_ms / 1000
        return float(thread.get("updated_at") or 0)

    @staticmethod
    def _thread_created_seconds(thread: Dict[str, Any]) -> float:
        created_at_ms = thread.get("created_at_ms")
        if created_at_ms:
            return created_at_ms / 1000
        return float(thread.get("created_at") or 0)

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
                    key=lambda item: (item.get("updated_at_ms") or 0, item.get("id") or ""),
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

            newest_updated = max((thread.get("updated_at_ms") or 0 for thread in threads), default=0)
            projects.append(
                {
                    "id": self._project_id(cwd),
                    "path": cwd,
                    "display_name": self._display_name(cwd),
                    "session_count": len(threads),
                    "size": size,
                    "source": self.id,
                    "modified": newest_updated / 1000 if newest_updated else 0,
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

    def get_session(self, project_id: str, session_id: str) -> Dict[str, Any]:
        raise FileNotFoundError("Session not found")
