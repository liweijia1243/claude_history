import os
from pathlib import Path

from .base import HistoryProvider


class CodexProvider(HistoryProvider):
    id = "codex"
    name = "Codex"

    def __init__(self, root: Path | None = None):
        self.root = root or Path(os.path.expanduser("~/.codex"))
        self.state_db = self.root / "state_5.sqlite"

    def available(self) -> bool:
        return self.state_db.exists()

    def get_stats(self) -> dict:
        return {
            "total_commands": 0,
            "total_plans": 0,
            "total_projects": 0,
            "total_sessions": 0,
            "recent_commands_24h": 0,
        }

    def get_dashboard_stats(self, range_str: str) -> dict:
        return {
            "summary": {
                "total_commands": 0,
                "total_sessions": 0,
                "total_projects": 0,
                "total_tokens": {"input": 0, "output": 0},
            },
            "changes": {
                "commands_pct": 0,
                "sessions_pct": 0,
                "projects_new": 0,
                "tokens_pct": 0,
            },
            "daily_series": [],
            "message_types": {},
            "top_projects": [],
            "hourly_distribution": [0] * 24,
            "session_durations": {
                "under_5min": 0,
                "5_to_15min": 0,
                "15_to_30min": 0,
                "30_to_60min": 0,
                "over_60min": 0,
            },
        }

    def get_recent_sessions(self, limit: int) -> list[dict]:
        return []

    def get_history(self, page: int, limit: int, search: str | None, project: str | None) -> dict:
        return {"items": [], "total": 0, "page": page, "limit": limit, "pages": 0}

    def list_projects(self) -> list[dict]:
        return []

    def get_project(self, project_id: str) -> dict:
        raise FileNotFoundError("Project not found")

    def list_sessions(self, project_id: str) -> list[dict]:
        return self.get_project(project_id)["sessions"]

    def get_session(self, project_id: str, session_id: str) -> dict:
        raise FileNotFoundError("Session not found")
