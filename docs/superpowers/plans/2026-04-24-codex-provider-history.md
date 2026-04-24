# Codex Provider History Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add first-class Codex conversation visualization by introducing backend history providers and source-aware frontend routes while preserving existing Claude behavior.

**Architecture:** The backend gains a `providers/` package with a shared interface, a migrated Claude provider, and a Codex provider that reads `state_5.sqlite` threads plus rollout JSONL files. The frontend keeps the current page structure but routes and API calls become source-aware, so Claude and Codex share the same conversation UI and tool rendering components.

**Tech Stack:** Python 3 standard library (`json`, `sqlite3`, `hashlib`, `tempfile`, `unittest`), FastAPI, Vue 3, Vue Router, Vitest, Vite.

---

## File Structure

Create:

- `providers/__init__.py`: provider registry and `get_provider(source)` helper.
- `providers/base.py`: `HistoryProvider` abstract interface.
- `providers/models.py`: small helpers for normalized conversation, tool use, and tool result dictionaries.
- `providers/claude.py`: Claude provider, migrated from the current `server.py` implementation.
- `providers/codex.py`: Codex provider, including SQLite thread queries and rollout reconstruction.
- `tests/__init__.py`: makes backend tests importable by `python -m unittest`.
- `tests/test_codex_provider.py`: Codex provider unit tests with temporary SQLite and JSONL fixtures.
- `web/src/utils/source.js`: source route/API helpers shared by pages and components.
- `web/src/utils/source.test.js`: source helper tests.
- `web/src/components/ToolCallBlock.test.js`: Codex tool rendering tests.

Modify:

- `server.py`: replace direct Claude-only route bodies with provider dispatch while keeping legacy route compatibility.
- `web/src/router.js`: add `/sources/:source/...` routes and keep existing Claude-default routes.
- `web/src/App.vue`: add source switcher and source-aware navigation.
- `web/src/views/Dashboard.vue`: fetch dashboard stats and recent sessions for the active source.
- `web/src/views/HistoryView.vue`: pass active source into `HistorySearch`.
- `web/src/components/HistorySearch.vue`: fetch and navigate through source-aware URLs.
- `web/src/views/ProjectsView.vue`: fetch source-aware projects and navigate source-aware paths.
- `web/src/views/ProjectDetailView.vue`: fetch source-aware project detail and navigate source-aware sessions.
- `web/src/views/ConversationView.vue`: fetch source-aware session detail and render event messages/session metadata.
- `web/src/components/ToolCallBlock.vue`: display Codex shell/patch/agent tools without breaking Claude tools.
- `README.md` and `README.en.md`: update project description and supported data sources.

---

### Task 1: Backend Provider Scaffolding

**Files:**
- Create: `providers/__init__.py`
- Create: `providers/base.py`
- Create: `providers/models.py`
- Create: `tests/__init__.py`
- Create: `tests/test_codex_provider.py`

- [ ] **Step 1: Write failing tests for normalized model helpers and provider availability**

Create `tests/__init__.py` as an empty file.

Create `tests/test_codex_provider.py`:

```python
import tempfile
import unittest
from pathlib import Path

from providers.codex import CodexProvider
from providers.models import make_message, make_tool_result, make_tool_use


class ProviderModelTests(unittest.TestCase):
    def test_make_message_includes_stable_defaults(self):
        message = make_message(role="assistant", content="hello", timestamp="2026-04-24T10:00:00Z")

        self.assertEqual(message["role"], "assistant")
        self.assertEqual(message["content"], "hello")
        self.assertEqual(message["thinking"], "")
        self.assertEqual(message["tool_uses"], [])
        self.assertEqual(message["tool_results"], [])
        self.assertEqual(message["model"], "")
        self.assertEqual(message["usage"], {})
        self.assertEqual(message["timestamp"], "2026-04-24T10:00:00Z")
        self.assertEqual(message["uuid"], "")
        self.assertEqual(message["metadata"], {})

    def test_tool_helpers_include_metadata(self):
        tool = make_tool_use("call-1", "exec_command", {"command": ["pwd"]}, {"provider": "codex"})
        result = make_tool_result("call-1", "ok", False, {"exit_code": 0})

        self.assertEqual(tool["id"], "call-1")
        self.assertEqual(tool["name"], "exec_command")
        self.assertEqual(tool["input"], {"command": ["pwd"]})
        self.assertEqual(tool["metadata"], {"provider": "codex"})
        self.assertEqual(result["tool_use_id"], "call-1")
        self.assertEqual(result["content"], "ok")
        self.assertFalse(result["is_error"])
        self.assertEqual(result["metadata"], {"exit_code": 0})


class CodexProviderAvailabilityTests(unittest.TestCase):
    def test_provider_unavailable_without_state_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider = CodexProvider(root=Path(tmp))
            self.assertFalse(provider.available())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
python -m unittest tests.test_codex_provider -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'providers'`.

- [ ] **Step 3: Add provider interface and model helper implementation**

Create `providers/models.py`:

```python
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
```

Create `providers/base.py`:

```python
from abc import ABC, abstractmethod
from typing import Optional


class HistoryProvider(ABC):
    id: str
    name: str

    @abstractmethod
    def available(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_stats(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def get_dashboard_stats(self, range_str: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    def get_recent_sessions(self, limit: int) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def get_history(
        self,
        page: int,
        limit: int,
        search: Optional[str],
        project: Optional[str],
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def list_projects(self) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def get_project(self, project_id: str) -> dict:
        raise NotImplementedError

    @abstractmethod
    def list_sessions(self, project_id: str) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def get_session(self, project_id: str, session_id: str) -> dict:
        raise NotImplementedError

    def get_subagent(self, project_id: str, session_id: str, agent_file: str) -> dict:
        raise FileNotFoundError("Subagent not found")
```

Create `providers/codex.py`:

```python
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
```

Create `providers/__init__.py`:

```python
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
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```bash
python -m unittest tests.test_codex_provider -v
```

Expected: PASS for 3 tests.

- [ ] **Step 5: Commit**

```bash
git add providers tests
git commit -m "test: add provider scaffolding"
```

---

### Task 2: Codex Thread Index, Projects, Sessions, and History

**Files:**
- Modify: `providers/codex.py`
- Modify: `tests/test_codex_provider.py`

- [ ] **Step 1: Add failing SQLite-backed tests**

Append this code to `tests/test_codex_provider.py` before the `if __name__ == "__main__"` block:

```python
import json
import sqlite3


def create_codex_state(root: Path):
    db_path = root / "state_5.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE threads (
            id TEXT PRIMARY KEY,
            rollout_path TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            source TEXT NOT NULL,
            model_provider TEXT NOT NULL,
            cwd TEXT NOT NULL,
            title TEXT NOT NULL,
            sandbox_policy TEXT NOT NULL,
            approval_mode TEXT NOT NULL,
            tokens_used INTEGER NOT NULL DEFAULT 0,
            has_user_event INTEGER NOT NULL DEFAULT 0,
            archived INTEGER NOT NULL DEFAULT 0,
            archived_at INTEGER,
            git_sha TEXT,
            git_branch TEXT,
            git_origin_url TEXT,
            cli_version TEXT NOT NULL DEFAULT '',
            first_user_message TEXT NOT NULL DEFAULT '',
            agent_nickname TEXT,
            agent_role TEXT,
            memory_mode TEXT NOT NULL DEFAULT 'enabled',
            model TEXT,
            reasoning_effort TEXT,
            agent_path TEXT,
            created_at_ms INTEGER,
            updated_at_ms INTEGER
        )
        """
    )
    conn.commit()
    return conn


def insert_thread(
    conn,
    root: Path,
    thread_id: str,
    cwd: str,
    title: str,
    first_user_message: str,
    created_ms: int,
    updated_ms: int,
    tokens_used: int = 0,
):
    rollout = root / "sessions" / f"{thread_id}.jsonl"
    rollout.parent.mkdir(parents=True, exist_ok=True)
    rollout.write_text("", encoding="utf-8")
    conn.execute(
        """
        INSERT INTO threads (
            id, rollout_path, created_at, updated_at, source, model_provider, cwd, title,
            sandbox_policy, approval_mode, tokens_used, first_user_message, model,
            reasoning_effort, created_at_ms, updated_at_ms
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            thread_id,
            str(rollout),
            created_ms // 1000,
            updated_ms // 1000,
            "cli",
            "openai",
            cwd,
            title,
            "workspace-write",
            "on-request",
            tokens_used,
            first_user_message,
            "gpt-5.5",
            "medium",
            created_ms,
            updated_ms,
        ),
    )
    conn.commit()
    return rollout


class CodexProviderIndexTests(unittest.TestCase):
    def test_projects_are_grouped_by_thread_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            conn = create_codex_state(root)
            insert_thread(conn, root, "thread-a", "/repo/alpha", "Alpha title", "build alpha", 1000, 3000)
            insert_thread(conn, root, "thread-b", "/repo/alpha", "Second title", "debug alpha", 2000, 4000)
            insert_thread(conn, root, "thread-c", "/repo/beta", "Beta title", "build beta", 5000, 6000)
            conn.close()

            provider = CodexProvider(root=root)
            projects = provider.list_projects()

            self.assertEqual([p["path"] for p in projects], ["/repo/beta", "/repo/alpha"])
            self.assertEqual(projects[0]["display_name"], "beta")
            self.assertEqual(projects[0]["session_count"], 1)
            self.assertEqual(projects[1]["display_name"], "alpha")
            self.assertEqual(projects[1]["session_count"], 2)
            self.assertNotIn("/", projects[0]["id"])

    def test_project_detail_lists_sessions_newest_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            conn = create_codex_state(root)
            insert_thread(conn, root, "thread-a", "/repo/alpha", "Alpha title", "build alpha", 1000, 3000)
            insert_thread(conn, root, "thread-b", "/repo/alpha", "Second title", "debug alpha", 2000, 5000)
            conn.close()

            provider = CodexProvider(root=root)
            project_id = provider.list_projects()[0]["id"]
            detail = provider.get_project(project_id)

            self.assertEqual(detail["path"], "/repo/alpha")
            self.assertEqual([s["id"] for s in detail["sessions"]], ["thread-b", "thread-a"])
            self.assertEqual(detail["sessions"][0]["preview"], "debug alpha")
            self.assertEqual(detail["sessions"][0]["model"], "gpt-5.5")

    def test_history_uses_codex_history_jsonl_and_links_project_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            conn = create_codex_state(root)
            insert_thread(conn, root, "thread-a", "/repo/alpha", "Alpha title", "build alpha", 1000, 3000)
            conn.close()
            (root / "history.jsonl").write_text(
                json.dumps({"session_id": "thread-a", "ts": 1777000000000, "text": "build alpha"}) + "\n",
                encoding="utf-8",
            )

            provider = CodexProvider(root=root)
            history = provider.get_history(page=1, limit=50, search="alpha", project=None)

            self.assertEqual(history["total"], 1)
            item = history["items"][0]
            self.assertEqual(item["sessionId"], "thread-a")
            self.assertEqual(item["display"], "build alpha")
            self.assertEqual(item["project"], "/repo/alpha")
            self.assertEqual(item["project_id"], provider.list_projects()[0]["id"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m unittest tests.test_codex_provider -v
```

Expected: FAIL because `list_projects()`, `get_project()`, and `get_history()` still return empty data.

- [ ] **Step 3: Implement Codex thread query and project/session aggregation**

Replace `providers/codex.py` with:

```python
import hashlib
import json
import os
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from .base import HistoryProvider


class CodexProvider(HistoryProvider):
    id = "codex"
    name = "Codex"

    def __init__(self, root: Path | None = None):
        self.root = root or Path(os.path.expanduser("~/.codex"))
        self.state_db = self.root / "state_5.sqlite"

    def available(self) -> bool:
        return self.state_db.exists()

    def _connect(self):
        conn = sqlite3.connect(self.state_db)
        conn.row_factory = sqlite3.Row
        return conn

    def _read_threads(self) -> list[dict]:
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
    def _thread_preview(thread: dict) -> str:
        return thread.get("first_user_message") or thread.get("title") or ""

    @staticmethod
    def _thread_modified_seconds(thread: dict) -> float:
        value = thread.get("updated_at_ms") or thread.get("updated_at") or 0
        return value / 1000 if value and value > 1_000_000_000_000 else value

    def _project_map(self) -> dict[str, list[dict]]:
        groups: dict[str, list[dict]] = defaultdict(list)
        for thread in self._read_threads():
            groups[thread.get("cwd") or ""].append(thread)
        return dict(groups)

    def list_projects(self) -> list[dict]:
        projects = []
        for cwd, threads in self._project_map().items():
            project_id = self._project_id(cwd)
            size = 0
            for thread in threads:
                rollout = Path(thread.get("rollout_path") or "")
                if rollout.exists():
                    size += rollout.stat().st_size
            projects.append(
                {
                    "id": project_id,
                    "path": cwd,
                    "display_name": self._display_name(cwd),
                    "session_count": len(threads),
                    "size": size,
                    "source": self.id,
                }
            )
        projects.sort(
            key=lambda project: max(
                (thread.get("updated_at_ms") or 0 for thread in self._project_map().get(project["path"], [])),
                default=0,
            ),
            reverse=True,
        )
        return projects

    def _find_project_threads(self, project_id: str) -> tuple[str, list[dict]]:
        for cwd, threads in self._project_map().items():
            if self._project_id(cwd) == project_id:
                return cwd, sorted(threads, key=lambda t: (t.get("updated_at_ms") or 0, t.get("id") or ""), reverse=True)
        raise FileNotFoundError("Project not found")

    def _session_summary(self, thread: dict) -> dict:
        rollout = Path(thread.get("rollout_path") or "")
        size = rollout.stat().st_size if rollout.exists() else 0
        return {
            "id": thread.get("id", ""),
            "preview": self._thread_preview(thread)[:200],
            "message_count": self._count_rollout_lines(rollout),
            "message_types": {},
            "size": size,
            "created": (thread.get("created_at_ms") or thread.get("created_at") or 0) / 1000,
            "modified": self._thread_modified_seconds(thread),
            "first_timestamp": thread.get("created_at_ms") or "",
            "last_timestamp": thread.get("updated_at_ms") or "",
            "title": thread.get("title") or "",
            "model": thread.get("model") or "",
            "reasoning_effort": thread.get("reasoning_effort") or "",
            "source": self.id,
        }

    @staticmethod
    def _count_rollout_lines(path: Path) -> int:
        if not path.exists():
            return 0
        with path.open("r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())

    def get_project(self, project_id: str) -> dict:
        cwd, threads = self._find_project_threads(project_id)
        return {
            "id": project_id,
            "path": cwd,
            "source": self.id,
            "sessions": [self._session_summary(thread) for thread in threads],
        }

    def list_sessions(self, project_id: str) -> list[dict]:
        return self.get_project(project_id)["sessions"]

    def _thread_by_id(self, session_id: str) -> dict | None:
        for thread in self._read_threads():
            if thread.get("id") == session_id:
                return thread
        return None

    def get_history(self, page: int, limit: int, search: Optional[str], project: Optional[str]) -> dict:
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
                    thread = threads.get(raw.get("session_id"), {})
                    cwd = thread.get("cwd", "")
                    display = raw.get("text", "")
                    if search and search.lower() not in display.lower():
                        continue
                    if project and project not in cwd:
                        continue
                    items.append(
                        {
                            "sessionId": raw.get("session_id", ""),
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

    def get_stats(self) -> dict:
        threads = self._read_threads()
        projects = {thread.get("cwd", "") for thread in threads}
        history = self.get_history(page=1, limit=1_000_000, search=None, project=None)["items"]
        now_ms = datetime.now().timestamp() * 1000
        day_ago = now_ms - 86_400_000
        recent = sum(1 for item in history if (item.get("timestamp") or 0) > day_ago)
        return {
            "total_commands": len(history),
            "total_plans": 0,
            "total_projects": len(projects),
            "total_sessions": len(threads),
            "recent_commands_24h": recent,
        }

    def get_dashboard_stats(self, range_str: str) -> dict:
        stats = self.get_stats()
        total_tokens = sum(thread.get("tokens_used") or 0 for thread in self._read_threads())
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

    def get_recent_sessions(self, limit: int) -> list[dict]:
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

    def get_session(self, project_id: str, session_id: str) -> dict:
        raise FileNotFoundError("Session not found")
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m unittest tests.test_codex_provider -v
```

Expected: PASS for all provider model, availability, and index tests.

- [ ] **Step 5: Commit**

```bash
git add providers/codex.py tests/test_codex_provider.py
git commit -m "feat: index codex threads"
```

---

### Task 3: Codex Rollout Conversation Reconstruction

**Files:**
- Modify: `providers/codex.py`
- Modify: `tests/test_codex_provider.py`

- [ ] **Step 1: Add failing rollout reconstruction tests**

Append this test class to `tests/test_codex_provider.py` before the `if __name__ == "__main__"` block:

```python
class CodexProviderConversationTests(unittest.TestCase):
    def test_reconstructs_messages_reasoning_tools_and_exec_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            conn = create_codex_state(root)
            rollout = insert_thread(conn, root, "thread-a", "/repo/alpha", "Alpha", "run pwd", 1000, 4000)
            conn.close()
            events = [
                {
                    "timestamp": "2026-04-24T10:00:00Z",
                    "type": "session_meta",
                    "payload": {"id": "thread-a", "cwd": "/repo/alpha", "source": "cli", "model_provider": "openai"},
                },
                {
                    "timestamp": "2026-04-24T10:00:01Z",
                    "type": "event_msg",
                    "payload": {"type": "user_message", "message": "run pwd", "images": [], "local_images": [], "text_elements": []},
                },
                {
                    "timestamp": "2026-04-24T10:00:02Z",
                    "type": "response_item",
                    "payload": {"type": "reasoning", "summary": [{"text": "Need to inspect cwd"}], "content": None},
                },
                {
                    "timestamp": "2026-04-24T10:00:03Z",
                    "type": "response_item",
                    "payload": {"type": "function_call", "name": "exec_command", "arguments": "{\"cmd\":\"pwd\"}", "call_id": "call-1"},
                },
                {
                    "timestamp": "2026-04-24T10:00:04Z",
                    "type": "response_item",
                    "payload": {
                        "type": "exec_command_end",
                        "call_id": "call-1",
                        "command": ["pwd"],
                        "cwd": "/repo/alpha",
                        "stdout": "/repo/alpha\n",
                        "stderr": "",
                        "aggregated_output": "/repo/alpha\n",
                        "formatted_output": "/repo/alpha\n",
                        "exit_code": 0,
                        "duration": {"secs": 0, "nanos": 1000},
                        "status": "completed",
                    },
                },
                {
                    "timestamp": "2026-04-24T10:00:05Z",
                    "type": "response_item",
                    "payload": {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "The cwd is /repo/alpha."}]},
                },
            ]
            rollout.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

            provider = CodexProvider(root=root)
            project_id = provider.list_projects()[0]["id"]
            session = provider.get_session(project_id, "thread-a")

            self.assertEqual(session["session_id"], "thread-a")
            self.assertEqual(session["project_id"], project_id)
            self.assertEqual(session["total_raw_messages"], len(events))
            self.assertEqual(session["metadata"]["cwd"], "/repo/alpha")
            self.assertEqual([m["role"] for m in session["conversation"]], ["user", "assistant"])
            assistant = session["conversation"][1]
            self.assertEqual(assistant["thinking"], "Need to inspect cwd")
            self.assertEqual(assistant["content"], "The cwd is /repo/alpha.")
            self.assertEqual(assistant["tool_uses"][0]["id"], "call-1")
            self.assertEqual(assistant["tool_uses"][0]["name"], "exec_command")
            self.assertEqual(assistant["tool_results"][0]["tool_use_id"], "call-1")
            self.assertEqual(assistant["tool_results"][0]["metadata"]["exit_code"], 0)

    def test_encrypted_reasoning_does_not_expose_ciphertext(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            conn = create_codex_state(root)
            rollout = insert_thread(conn, root, "thread-a", "/repo/alpha", "Alpha", "hello", 1000, 4000)
            conn.close()
            events = [
                {
                    "timestamp": "2026-04-24T10:00:02Z",
                    "type": "response_item",
                    "payload": {"type": "reasoning", "summary": [], "content": None, "encrypted_content": "secret-ciphertext"},
                },
            ]
            rollout.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

            provider = CodexProvider(root=root)
            project_id = provider.list_projects()[0]["id"]
            session = provider.get_session(project_id, "thread-a")

            self.assertNotIn("secret-ciphertext", json.dumps(session))
            self.assertEqual(session["conversation"][0]["thinking"], "[Encrypted reasoning available]")
            self.assertTrue(session["conversation"][0]["metadata"]["reasoning_encrypted"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m unittest tests.test_codex_provider -v
```

Expected: FAIL because `get_session()` still raises `FileNotFoundError`.

- [ ] **Step 3: Implement rollout parsing and conversation reconstruction**

In `providers/codex.py`, update imports:

```python
from .models import make_message, make_tool_result, make_tool_use
```

Add these methods inside `CodexProvider` before `get_session()`:

```python
    @staticmethod
    def _read_jsonl(path: Path) -> list[dict]:
        items = []
        if not path.exists():
            return items
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return items

    @staticmethod
    def _content_text(content) -> str:
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
    def _parse_arguments(raw: str) -> dict:
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {"arguments": parsed}
        except json.JSONDecodeError:
            return {"arguments": raw}

    @staticmethod
    def _reasoning_text(payload: dict) -> tuple[str, bool]:
        content = payload.get("content")
        if isinstance(content, str) and content:
            return content, False
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
        if payload.get("encrypted_content"):
            return "[Encrypted reasoning available]", True
        return "", False

    @staticmethod
    def _result_content(payload: dict) -> str:
        return (
            payload.get("formatted_output")
            or payload.get("aggregated_output")
            or payload.get("output")
            or "\n".join(part for part in [payload.get("stdout", ""), payload.get("stderr", "")] if part)
        )

    def _reconstruct_rollout(self, events: list[dict], thread: dict) -> tuple[list[dict], dict]:
        conversation = []
        current_assistant = None
        tool_owner: dict[str, dict] = {}
        metadata = {
            "cwd": thread.get("cwd", ""),
            "title": thread.get("title", ""),
            "model": thread.get("model") or "",
            "reasoning_effort": thread.get("reasoning_effort") or "",
            "source": self.id,
        }

        def ensure_assistant(timestamp=""):
            nonlocal current_assistant
            if current_assistant is None:
                current_assistant = make_message(
                    role="assistant",
                    model=thread.get("model") or "",
                    timestamp=timestamp,
                    metadata={"source": self.id},
                )
            return current_assistant

        def flush_assistant():
            nonlocal current_assistant
            if current_assistant is not None:
                conversation.append(current_assistant)
                current_assistant = None

        for event in events:
            timestamp = event.get("timestamp", "")
            payload = event.get("payload") or {}
            payload_type = payload.get("type")

            if event.get("type") == "session_meta":
                metadata.update(
                    {
                        "cwd": payload.get("cwd", metadata.get("cwd", "")),
                        "codex_source": payload.get("source", ""),
                        "model_provider": payload.get("model_provider", ""),
                        "git": payload.get("git", {}),
                        "dynamic_tools": payload.get("dynamic_tools", []),
                    }
                )
                continue

            if event.get("type") == "turn_context":
                metadata.update(
                    {
                        "approval_policy": payload.get("approval_policy", ""),
                        "sandbox_policy": payload.get("sandbox_policy", {}),
                        "current_date": payload.get("current_date", ""),
                        "timezone": payload.get("timezone", ""),
                    }
                )
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
                content = self._content_text(payload.get("content"))
                if role == "user":
                    flush_assistant()
                    conversation.append(make_message(role="user", content=content, timestamp=timestamp, metadata={"source": self.id}))
                else:
                    assistant = ensure_assistant(timestamp)
                    if content:
                        assistant["content"] = "\n".join(part for part in [assistant.get("content", ""), content] if part)
                continue

            if payload_type == "reasoning":
                assistant = ensure_assistant(timestamp)
                text, encrypted = self._reasoning_text(payload)
                if text:
                    assistant["thinking"] = "\n".join(part for part in [assistant.get("thinking", ""), text] if part)
                if encrypted:
                    assistant["metadata"]["reasoning_encrypted"] = True
                continue

            if payload_type == "function_call":
                assistant = ensure_assistant(timestamp)
                tool = make_tool_use(
                    payload.get("call_id", ""),
                    payload.get("name", ""),
                    self._parse_arguments(payload.get("arguments", "")),
                    {"provider": self.id},
                )
                assistant["tool_uses"].append(tool)
                if tool["id"]:
                    tool_owner[tool["id"]] = assistant
                continue

            if payload_type in ("function_call_output", "exec_command_end"):
                call_id = payload.get("call_id", "")
                owner = tool_owner.get(call_id) or ensure_assistant(timestamp)
                if call_id and call_id not in tool_owner:
                    synthetic = make_tool_use(
                        call_id,
                        "exec_command" if payload_type == "exec_command_end" else "function_call_output",
                        {"command": payload.get("command", []), "cwd": payload.get("cwd", "")},
                        {"provider": self.id, "synthetic": True},
                    )
                    owner["tool_uses"].append(synthetic)
                    tool_owner[call_id] = owner
                metadata_result = {
                    "exit_code": payload.get("exit_code"),
                    "duration": payload.get("duration"),
                    "status": payload.get("status"),
                    "stdout": payload.get("stdout", ""),
                    "stderr": payload.get("stderr", ""),
                    "cwd": payload.get("cwd", ""),
                    "command": payload.get("command", []),
                    "parsed_cmd": payload.get("parsed_cmd", []),
                }
                owner["tool_results"].append(
                    make_tool_result(
                        call_id,
                        self._result_content(payload),
                        bool(payload.get("exit_code")),
                        metadata_result,
                    )
                )
                continue

            if payload_type == "agent_message":
                role = "assistant" if payload.get("phase") in ("final", "message", "response") else "event"
                flush_assistant()
                conversation.append(
                    make_message(
                        role=role,
                        content=payload.get("message", ""),
                        timestamp=timestamp,
                        metadata={"phase": payload.get("phase", ""), "source": self.id},
                    )
                )
                continue

            if payload_type == "token_count":
                metadata["last_token_count"] = payload

        flush_assistant()
        return conversation, metadata
```

Replace `get_session()` with:

```python
    def get_session(self, project_id: str, session_id: str) -> dict:
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m unittest tests.test_codex_provider -v
```

Expected: PASS for all Codex tests.

- [ ] **Step 5: Commit**

```bash
git add providers/codex.py tests/test_codex_provider.py
git commit -m "feat: reconstruct codex rollout conversations"
```

---

### Task 4: Claude Provider Migration and Source API Routes

**Files:**
- Create: `providers/claude.py`
- Modify: `providers/__init__.py`
- Modify: `server.py`

- [ ] **Step 1: Add a minimal API compatibility test**

Create `tests/test_provider_registry.py`:

```python
import unittest

from providers import get_provider, list_sources


class ProviderRegistryTests(unittest.TestCase):
    def test_registry_contains_claude_and_codex(self):
        sources = {source["id"]: source for source in list_sources()}

        self.assertIn("claude", sources)
        self.assertIn("codex", sources)
        self.assertEqual(get_provider("claude").id, "claude")
        self.assertEqual(get_provider("codex").id, "codex")
        self.assertIsNone(get_provider("missing"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run registry test to verify it fails**

Run:

```bash
python -m unittest tests.test_provider_registry -v
```

Expected: FAIL because `claude` is not registered yet.

- [ ] **Step 3: Move Claude-specific code into `providers/claude.py`**

Create `providers/claude.py` by moving the current Claude-specific constants and helper functions out of `server.py`:

```python
import glob
import json
import os
import time as _time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from .base import HistoryProvider


class ClaudeProvider(HistoryProvider):
    id = "claude"
    name = "Claude"

    def __init__(self, root: Path | None = None):
        self.root = root or Path(os.path.expanduser("~/.claude"))
        self._dashboard_cache = {}
        self._cache_ttl = 300

    def available(self) -> bool:
        return self.root.exists()

    def read_jsonl(self, path: Path, limit: int = 0):
        items = []
        if not path.exists():
            return items
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
                if limit and len(items) >= limit:
                    break
        return items
```

Then move the existing functions from `server.py` into methods on `ClaudeProvider` using these mechanical rules:

- Convert every top-level function below into an instance method by adding `self` as the first parameter.
- Replace every `CLAUDE_DIR` reference with `self.root`.
- Replace every call to `read_jsonl(...)` with `self.read_jsonl(...)`.
- Replace every call to a moved helper with `self.<helper_name>(...)`.
- Keep returned dictionaries and field names unchanged.
- Raise `FileNotFoundError` instead of `HTTPException` inside provider methods; `server.py` converts provider errors to HTTP responses.

Move these exact functions:

- `find_string_line()`
- `build_file_timeline()`
- `find_state_before()`
- `enrich_tool_uses_with_line_numbers()`
- `reconstruct_conversation()`
- `build_session_project_map()`
- `get_stats()`
- `get_dashboard_stats()`
- `get_recent_sessions()`
- `get_history()`
- `get_plans()`
- `get_plan()`
- `list_projects()`
- `get_project()`
- `list_sessions()`
- `get_session()`
- `get_subagent()`

For `get_plans()` and `get_plan()`, use the existing `/api/plans` and `/api/plans/{name}` route logic from `server.py`, but return provider data directly:

```python
    def get_plans(self):
        plans_dir = self.root / "plans"
        if not plans_dir.exists():
            return []

        plans = []
        for f in sorted(plans_dir.glob("*.md")):
            stat = f.stat()
            plans.append({
                "name": f.stem,
                "filename": f.name,
                "size": stat.st_size,
                "modified": stat.st_mtime,
            })
        return plans

    def get_plan(self, name: str):
        plan_path = self.root / "plans" / f"{name}.md"
        if not plan_path.exists():
            raise FileNotFoundError("Plan not found")
        return {
            "name": name,
            "content": plan_path.read_text(encoding="utf-8"),
        }
```

Keep the dashboard cache as `self._dashboard_cache` and the TTL as `self._cache_ttl`.

- [ ] **Step 4: Register Claude and Codex providers**

Replace `providers/__init__.py` with:

```python
from .claude import ClaudeProvider
from .codex import CodexProvider


_PROVIDERS = {
    "claude": ClaudeProvider(),
    "codex": CodexProvider(),
}


def get_provider(source: str):
    return _PROVIDERS.get(source)


def list_sources() -> list[dict]:
    return [
        {"id": provider.id, "name": provider.name, "available": provider.available()}
        for provider in _PROVIDERS.values()
    ]
```

- [ ] **Step 5: Update `server.py` to dispatch by provider**

In `server.py`, keep `get_base_path()`, FastAPI setup, CORS setup, and SPA serving. Replace Claude route bodies with:

```python
from providers import get_provider, list_sources


def provider_or_404(source: str):
    provider = get_provider(source)
    if not provider:
        raise HTTPException(404, "Source not found")
    if not provider.available():
        raise HTTPException(404, "Source unavailable")
    return provider


@app.get("/api/sources")
def get_sources():
    return list_sources()


@app.get("/api/{source}/stats")
def get_source_stats(source: str):
    return provider_or_404(source).get_stats()


@app.get("/api/{source}/dashboard-stats")
def get_source_dashboard_stats(source: str, range: str = Query("30d", pattern="^(7d|30d|all)$")):
    return provider_or_404(source).get_dashboard_stats(range)


@app.get("/api/{source}/recent-sessions")
def get_source_recent_sessions(source: str, limit: int = Query(5, ge=1, le=20)):
    return provider_or_404(source).get_recent_sessions(limit)


@app.get("/api/{source}/history")
def get_source_history(
    source: str,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None),
    project: Optional[str] = Query(None),
):
    return provider_or_404(source).get_history(page, limit, search, project)


@app.get("/api/{source}/projects")
def get_source_projects(source: str):
    return provider_or_404(source).list_projects()


@app.get("/api/{source}/projects/{project_id}")
def get_source_project_detail(source: str, project_id: str):
    try:
        return provider_or_404(source).get_project(project_id)
    except FileNotFoundError:
        raise HTTPException(404, "Project not found")


@app.get("/api/{source}/projects/{project_id}/sessions")
def get_source_project_sessions(source: str, project_id: str):
    try:
        return provider_or_404(source).list_sessions(project_id)
    except FileNotFoundError:
        raise HTTPException(404, "Project not found")


@app.get("/api/{source}/projects/{project_id}/sessions/{session_id}")
def get_source_session_conversation(source: str, project_id: str, session_id: str):
    try:
        return provider_or_404(source).get_session(project_id, session_id)
    except FileNotFoundError:
        raise HTTPException(404, "Session not found")


@app.get("/api/{source}/projects/{project_id}/sessions/{session_id}/subagents/{agent_file}")
def get_source_subagent_conversation(source: str, project_id: str, session_id: str, agent_file: str):
    try:
        return provider_or_404(source).get_subagent(project_id, session_id, agent_file)
    except FileNotFoundError:
        raise HTTPException(404, "Subagent not found")
```

Add legacy routes that delegate to `claude`:

```python
@app.get("/api/stats")
def get_stats():
    return provider_or_404("claude").get_stats()


@app.get("/api/dashboard-stats")
def get_dashboard_stats(range: str = Query("30d", pattern="^(7d|30d|all)$")):
    return provider_or_404("claude").get_dashboard_stats(range)


@app.get("/api/recent-sessions")
def get_recent_sessions(limit: int = Query(5, ge=1, le=20)):
    return provider_or_404("claude").get_recent_sessions(limit)


@app.get("/api/history")
def get_history(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None),
    project: Optional[str] = Query(None),
):
    return provider_or_404("claude").get_history(page, limit, search, project)


@app.get("/api/plans")
def get_plans():
    return provider_or_404("claude").get_plans()


@app.get("/api/plans/{name}")
def get_plan(name: str):
    try:
        return provider_or_404("claude").get_plan(name)
    except FileNotFoundError:
        raise HTTPException(404, "Plan not found")


@app.get("/api/projects")
def get_projects():
    return provider_or_404("claude").list_projects()


@app.get("/api/projects/{project_id}")
def get_project_detail(project_id: str):
    try:
        return provider_or_404("claude").get_project(project_id)
    except FileNotFoundError:
        raise HTTPException(404, "Project not found")


@app.get("/api/projects/{project_id}/sessions")
def get_project_sessions(project_id: str):
    try:
        return provider_or_404("claude").list_sessions(project_id)
    except FileNotFoundError:
        raise HTTPException(404, "Project not found")


@app.get("/api/projects/{project_id}/sessions/{session_id}")
def get_session_conversation(project_id: str, session_id: str):
    try:
        return provider_or_404("claude").get_session(project_id, session_id)
    except FileNotFoundError:
        raise HTTPException(404, "Session not found")


@app.get("/api/projects/{project_id}/sessions/{session_id}/subagents/{agent_file}")
def get_subagent_conversation(project_id: str, session_id: str, agent_file: str):
    try:
        return provider_or_404("claude").get_subagent(project_id, session_id, agent_file)
    except FileNotFoundError:
        raise HTTPException(404, "Subagent not found")
```

- [ ] **Step 6: Run backend tests**

Run:

```bash
python -m unittest tests.test_codex_provider tests.test_provider_registry -v
```

Expected: PASS.

- [ ] **Step 7: Run frontend build as route smoke test**

Run:

```bash
cd web && npm run build
```

Expected: Vite build succeeds.

- [ ] **Step 8: Commit**

```bash
git add providers/claude.py providers/__init__.py server.py tests/test_provider_registry.py
git commit -m "feat: add history provider api"
```

---

### Task 5: Frontend Source Helpers and Routes

**Files:**
- Create: `web/src/utils/source.js`
- Create: `web/src/utils/source.test.js`
- Modify: `web/src/router.js`

- [ ] **Step 1: Write failing source helper tests**

Create `web/src/utils/source.test.js`:

```javascript
import { describe, expect, it } from 'vitest'

import { apiPath, routePath, sourceFromRoute } from './source.js'

describe('source helpers', () => {
  it('defaults old routes to claude', () => {
    expect(sourceFromRoute({ params: {}, path: '/projects' })).toBe('claude')
  })

  it('reads source from source route params', () => {
    expect(sourceFromRoute({ params: { source: 'codex' }, path: '/sources/codex/projects' })).toBe('codex')
  })

  it('builds source-aware API paths', () => {
    expect(apiPath('claude', '/projects')).toBe('/api/claude/projects')
    expect(apiPath('codex', '/projects/abc')).toBe('/api/codex/projects/abc')
  })

  it('builds legacy and source-aware route paths', () => {
    expect(routePath('claude', '/projects')).toBe('/projects')
    expect(routePath('codex', '/projects')).toBe('/sources/codex/projects')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd web && npm run test:run -- src/utils/source.test.js
```

Expected: FAIL because `source.js` does not exist.

- [ ] **Step 3: Implement source helpers**

Create `web/src/utils/source.js`:

```javascript
export const DEFAULT_SOURCE = 'claude'

export function sourceFromRoute(route) {
  return route?.params?.source || DEFAULT_SOURCE
}

export function apiPath(source, path) {
  const cleanPath = path.startsWith('/') ? path : `/${path}`
  return `/api/${source || DEFAULT_SOURCE}${cleanPath}`
}

export function routePath(source, path) {
  const cleanPath = path.startsWith('/') ? path : `/${path}`
  if (!source || source === DEFAULT_SOURCE) return cleanPath
  return `/sources/${source}${cleanPath}`
}
```

- [ ] **Step 4: Add source routes while preserving old routes**

Replace `web/src/router.js` with:

```javascript
import { createRouter, createWebHistory } from 'vue-router'

import Dashboard from './views/Dashboard.vue'
import HistoryView from './views/HistoryView.vue'
import PlansView from './views/PlansView.vue'
import ProjectsView from './views/ProjectsView.vue'
import ProjectDetailView from './views/ProjectDetailView.vue'
import ConversationView from './views/ConversationView.vue'

const routes = [
  { path: '/', component: Dashboard },
  { path: '/history', component: HistoryView },
  { path: '/plans', component: PlansView },
  { path: '/projects', component: ProjectsView },
  { path: '/projects/:projectId', component: ProjectDetailView, props: true },
  { path: '/projects/:projectId/sessions/:sessionId', component: ConversationView, props: true },
  { path: '/sources/:source', component: Dashboard, props: true },
  { path: '/sources/:source/history', component: HistoryView, props: true },
  { path: '/sources/:source/projects', component: ProjectsView, props: true },
  { path: '/sources/:source/projects/:projectId', component: ProjectDetailView, props: true },
  { path: '/sources/:source/projects/:projectId/sessions/:sessionId', component: ConversationView, props: true },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
```

- [ ] **Step 5: Run helper tests**

Run:

```bash
cd web && npm run test:run -- src/utils/source.test.js
```

Expected: PASS.

- [ ] **Step 6: Run frontend build**

Run:

```bash
cd web && npm run build
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add web/src/utils/source.js web/src/utils/source.test.js web/src/router.js
git commit -m "feat: add source aware routes"
```

---

### Task 6: Source-Aware Frontend Pages and Navigation

**Files:**
- Modify: `web/src/App.vue`
- Modify: `web/src/views/Dashboard.vue`
- Modify: `web/src/views/HistoryView.vue`
- Modify: `web/src/components/HistorySearch.vue`
- Modify: `web/src/views/ProjectsView.vue`
- Modify: `web/src/views/ProjectDetailView.vue`
- Modify: `web/src/views/ConversationView.vue`

- [ ] **Step 1: Update `App.vue` navigation and source switcher**

In `web/src/App.vue`, import `computed`, `watch`, and helpers:

```javascript
import { computed, ref, onMounted, watch } from 'vue'
import { routePath, sourceFromRoute } from './utils/source'
```

Add state:

```javascript
const activeSource = computed(() => sourceFromRoute(route))
const sources = ref([
  { id: 'claude', name: 'Claude', available: true },
  { id: 'codex', name: 'Codex', available: true },
])

onMounted(async () => {
  initTheme()
  try {
    const res = await fetch('/api/sources')
    if (res.ok) sources.value = await res.json()
  } catch {
    sources.value = sources.value
  }
})

watch(activeSource, (source) => {
  localStorage.setItem('history_source', source)
})
```

Replace `go(path)`:

```javascript
function go(path) {
  router.push(routePath(activeSource.value, path))
}
```

Replace `isActive(path)`:

```javascript
function isActive(path) {
  const sourcePrefix = activeSource.value === 'claude' ? '' : `/sources/${activeSource.value}`
  const fullPath = `${sourcePrefix}${path === '/' ? '' : path}` || '/'
  if (path === '/') return route.path === '/' || route.path === `/sources/${activeSource.value}`
  return route.path.startsWith(fullPath)
}
```

Add source switcher above theme toggle:

```vue
<div v-if="sidebarOpen" class="px-3 py-2 border-t border-[var(--border-color)]">
  <div class="grid grid-cols-2 gap-1 rounded-lg bg-[var(--bg-card)] p-1">
    <button
      v-for="source in sources"
      :key="source.id"
      @click="router.push(routePath(source.id, route.path.replace(/^\\/sources\\/[^/]+/, '') || '/'))"
      :disabled="!source.available"
      :class="[
        activeSource === source.id
          ? 'bg-blue-500 text-white'
          : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]',
        !source.available ? 'opacity-40 cursor-not-allowed' : ''
      ]"
      class="rounded-md px-2 py-1.5 text-xs transition-colors"
    >
      {{ source.name }}
    </button>
  </div>
</div>
```

- [ ] **Step 2: Update `Dashboard.vue` fetches and navigation**

Import helpers:

```javascript
import { apiPath, routePath, sourceFromRoute } from '../utils/source'
```

Add route:

```javascript
import { useRoute, useRouter } from 'vue-router'
const route = useRoute()
const source = computed(() => sourceFromRoute(route))
```

Change fetches:

```javascript
const res = await fetch(`${apiPath(source.value, '/dashboard-stats')}?range=${range.value}`)
```

```javascript
const res = await fetch(`${apiPath(source.value, '/recent-sessions')}?limit=4`)
```

Change project navigation:

```javascript
function navigateToProject(projectId) {
  router.push(routePath(source.value, `/projects/${projectId}`))
}
```

Add a watcher so source changes reload:

```javascript
watch(source, async () => {
  loading.value = true
  await Promise.all([fetchDashboardStats(), fetchRecentSessions()])
  loading.value = false
})
```

- [ ] **Step 3: Update `HistoryView.vue`**

Replace script:

```vue
<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import HistorySearch from '../components/HistorySearch.vue'
import { sourceFromRoute } from '../utils/source'

const route = useRoute()
const source = computed(() => sourceFromRoute(route))
</script>
```

Replace component usage:

```vue
<HistorySearch :source="source" :sync-url="true" :show-project="true" :initially-active="true" />
```

- [ ] **Step 4: Update `HistorySearch.vue`**

Add prop:

```javascript
source: { type: String, default: 'claude' },
```

Import helper:

```javascript
import { apiPath, routePath } from '../utils/source'
```

Change fetch:

```javascript
const res = await fetch(`${apiPath(props.source, '/history')}?${params}`)
```

Change URL sync:

```javascript
router.replace({ path: routePath(props.source, '/history'), query: search.value ? { q: search.value } : {} })
```

Change conversation navigation:

```javascript
router.push({
  path: routePath(props.source, `/projects/${projectId}/sessions/${sessionId}`),
  query,
})
```

- [ ] **Step 5: Update `ProjectsView.vue`**

Import helpers and route:

```javascript
import { computed, ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { apiPath, routePath, sourceFromRoute } from '../utils/source'
```

Add:

```javascript
const route = useRoute()
const source = computed(() => sourceFromRoute(route))
```

Replace loading logic with:

```javascript
async function loadProjects() {
  loading.value = true
  const res = await fetch(apiPath(source.value, '/projects'))
  projects.value = await res.json()
  loading.value = false
}

onMounted(loadProjects)
watch(source, loadProjects)
```

Change navigation:

```javascript
function openProject(projectId) {
  router.push(routePath(source.value, `/projects/${projectId}`))
}
```

- [ ] **Step 6: Update `ProjectDetailView.vue`**

Import helpers:

```javascript
import { computed, ref, onMounted, watch } from 'vue'
import { apiPath, routePath, sourceFromRoute } from '../utils/source'
```

Add:

```javascript
const source = computed(() => sourceFromRoute(route))
```

Replace load:

```javascript
async function loadProject() {
  loading.value = true
  const res = await fetch(apiPath(source.value, `/projects/${props.projectId}`))
  if (!res.ok) {
    router.push(routePath(source.value, '/projects'))
    return
  }
  const data = await res.json()
  project.value = data
  sessions.value = data.sessions
  loading.value = false
}

onMounted(loadProject)
watch(() => [source.value, props.projectId], loadProject)
```

Change go back/open session:

```javascript
function goBack() {
  router.push(routePath(source.value, '/projects'))
}

function openSession(sessionId) {
  router.push(routePath(source.value, `/projects/${props.projectId}/sessions/${sessionId}`))
}
```

Pass source to `HistorySearch`:

```vue
<HistorySearch
  :source="source"
  :project-path="project?.path || ''"
  :sync-url="false"
  :show-project="false"
  :initially-active="false"
  @search-active="onSearchActive"
/>
```

- [ ] **Step 7: Update `ConversationView.vue`**

Import helper:

```javascript
import { apiPath, routePath, sourceFromRoute } from '../utils/source'
```

Add source:

```javascript
const source = computed(() => sourceFromRoute(route))
const sessionMetadata = ref({})
```

Replace `onMounted` body with load function:

```javascript
async function loadConversation() {
  loading.value = true
  const res = await fetch(apiPath(source.value, `/projects/${props.projectId}/sessions/${props.sessionId}`))
  const data = await res.json()
  conversation.value = data.conversation
  subagents.value = data.subagents || []
  totalRaw.value = data.total_raw_messages
  sessionMetadata.value = data.metadata || {}
  loading.value = false
  scrollToMessage()
}

onMounted(loadConversation)
watch(() => [source.value, props.projectId, props.sessionId], loadConversation)
```

Change subagent fetch:

```javascript
const res = await fetch(
  apiPath(source.value, `/projects/${props.projectId}/sessions/${props.sessionId}/subagents/${agent.filename}`)
)
```

Change navigation:

```javascript
function goBack() {
  router.push(routePath(source.value, `/projects/${props.projectId}`))
}

function goBackToHistory() {
  const query = route.query.q ? { q: route.query.q } : {}
  router.push({ path: routePath(source.value, '/history'), query })
}

function goBackToProject() {
  const query = route.query.q ? { q: route.query.q } : {}
  router.push({ path: routePath(source.value, `/projects/${props.projectId}`), query })
}
```

Add event message rendering in the conversation loop before user message:

```vue
<div v-if="msg.role === 'event'" class="flex justify-center" :data-msg-timestamp="msg.timestamp">
  <div class="max-w-[85%] rounded-lg border border-[var(--border-color)] bg-[var(--bg-card)] px-4 py-2 text-xs text-[var(--text-secondary)]">
    <div v-if="msg.metadata?.phase" class="mb-1 font-semibold uppercase tracking-wide">{{ msg.metadata.phase }}</div>
    <div class="whitespace-pre-wrap">{{ msg.content }}</div>
  </div>
</div>
```

Change the existing user branch to `v-else-if="msg.role === 'user'"`.

Add session metadata in the header near raw messages:

```vue
<span v-if="sessionMetadata.model" class="text-xs text-[var(--text-secondary)] opacity-70 ml-3">
  {{ sessionMetadata.model }} {{ sessionMetadata.reasoning_effort || '' }}
</span>
```

- [ ] **Step 8: Run frontend tests and build**

Run:

```bash
cd web && npm run test:run
cd web && npm run build
```

Expected: both pass.

- [ ] **Step 9: Commit**

```bash
git add web/src/App.vue web/src/views/Dashboard.vue web/src/views/HistoryView.vue web/src/components/HistorySearch.vue web/src/views/ProjectsView.vue web/src/views/ProjectDetailView.vue web/src/views/ConversationView.vue
git commit -m "feat: make frontend source aware"
```

---

### Task 7: Codex Tool Rendering

**Files:**
- Create: `web/src/components/ToolCallBlock.test.js`
- Modify: `web/src/components/ToolCallBlock.vue`

- [ ] **Step 1: Write failing Codex tool rendering tests**

Create `web/src/components/ToolCallBlock.test.js`:

```javascript
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import ToolCallBlock from './ToolCallBlock.vue'

describe('ToolCallBlock Codex tools', () => {
  it('renders exec_command as terminal output with exit code metadata', async () => {
    const wrapper = mount(ToolCallBlock, {
      props: {
        toolUses: [
          {
            id: 'call-1',
            name: 'exec_command',
            input: { command: ['pwd'], cwd: '/repo/alpha' },
            metadata: { provider: 'codex' },
          },
        ],
        toolResults: [
          {
            tool_use_id: 'call-1',
            content: '/repo/alpha\n',
            is_error: false,
            metadata: { exit_code: 0, cwd: '/repo/alpha', command: ['pwd'] },
          },
        ],
      },
    })

    expect(wrapper.text()).toContain('exec_command')
    expect(wrapper.text()).toContain('pwd')
    await wrapper.get('button').trigger('click')
    expect(wrapper.text()).toContain('exit 0')
    expect(wrapper.text()).toContain('/repo/alpha')
  })

  it('keeps unknown tools visible through fallback json rendering', async () => {
    const wrapper = mount(ToolCallBlock, {
      props: {
        toolUses: [{ id: 'call-2', name: 'mcp_custom_tool', input: { value: 42 } }],
        toolResults: [],
      },
    })

    await wrapper.get('button').trigger('click')
    expect(wrapper.text()).toContain('mcp_custom_tool')
    expect(wrapper.text()).toContain('"value": 42')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd web && npm run test:run -- src/components/ToolCallBlock.test.js
```

Expected: FAIL because `exec_command` has no specialized label or exit metadata rendering.

- [ ] **Step 3: Update tool classifications and labels**

In `ToolCallBlock.vue`, add configs:

```javascript
exec_command: {
  color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
  icon: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"/><line x1="12" x2="20" y1="19" y2="19"/></svg>`,
  label: (inp) => `$ ${Array.isArray(inp.command) ? inp.command.join(' ') : inp.command || inp.cmd || ''}`
},
apply_patch: {
  color: 'text-orange-400 bg-orange-500/10 border-orange-500/20',
  icon: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>`,
  label: (inp) => inp.file || inp.path || 'patch'
},
spawn_agent: {
  color: 'text-purple-400 bg-purple-500/10 border-purple-500/20',
  icon: toolConfig.Agent.icon,
  label: (inp) => inp.agent_type || inp.message?.substring?.(0, 50) || ''
},
wait_agent: {
  color: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20',
  icon: toolConfig.TaskOutput.icon,
  label: (inp) => Array.isArray(inp.targets) ? inp.targets.join(', ') : ''
},
close_agent: {
  color: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20',
  icon: toolConfig.TaskOutput.icon,
  label: (inp) => inp.target || ''
},
```

If referencing `toolConfig.Agent.icon` inside the object is awkward because of declaration timing, duplicate the icon strings from the existing `Agent` and `TaskOutput` configs instead.

- [ ] **Step 4: Add Codex result helpers**

Add methods in `<script setup>`:

```javascript
function commandText(input = {}) {
  const command = input.command || input.cmd || input.shell_command
  return Array.isArray(command) ? command.join(' ') : command || ''
}

function resultExitLabel(result) {
  if (!result?.metadata || result.metadata.exit_code === undefined || result.metadata.exit_code === null) return ''
  return `exit ${result.metadata.exit_code}`
}
```

- [ ] **Step 5: Render `exec_command` results using terminal style**

Change the Bash result branch:

```vue
<div v-if="tool.name === 'Bash' || tool.name === 'exec_command'" class="terminal-output">
  <div class="text-xs text-emerald-400/60 mb-1 flex items-center gap-2">
    <span>$ {{ tool.name === 'exec_command' ? commandText(tool.input) : tool.input?.command }}</span>
    <span v-if="resultExitLabel(toolResultFor(tool.id))" class="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10">
      {{ resultExitLabel(toolResultFor(tool.id)) }}
    </span>
  </div>
  <div v-if="tool.input?.cwd || toolResultFor(tool.id)?.metadata?.cwd" class="text-xs text-[var(--text-secondary)] mb-1">
    {{ tool.input?.cwd || toolResultFor(tool.id)?.metadata?.cwd }}
  </div>
  <pre class="whitespace-pre-wrap break-words max-h-80 overflow-auto">{{ resultPreview(toolResultFor(tool.id), 5000) }}</pre>
</div>
```

- [ ] **Step 6: Run tool tests**

Run:

```bash
cd web && npm run test:run -- src/components/ToolCallBlock.test.js
```

Expected: PASS.

- [ ] **Step 7: Run all frontend tests and build**

Run:

```bash
cd web && npm run test:run
cd web && npm run build
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add web/src/components/ToolCallBlock.vue web/src/components/ToolCallBlock.test.js
git commit -m "feat: render codex tool calls"
```

---

### Task 8: Documentation and End-to-End Verification

**Files:**
- Modify: `README.md`
- Modify: `README.en.md`

- [ ] **Step 1: Update README data source descriptions**

In `README.md`, update the introduction to say the app supports Claude Code and Codex histories. Add a data source section:

```markdown
## 数据来源

| Source | 路径 | 内容 |
|--------|------|------|
| Claude | `~/.claude/history.jsonl` | 用户命令历史 |
| Claude | `~/.claude/plans/*.md` | 实施计划 |
| Claude | `~/.claude/projects/<dir>/*.jsonl` | 项目会话 |
| Codex | `~/.codex/state_5.sqlite` | thread 索引、cwd、模型、rollout 路径 |
| Codex | `~/.codex/sessions/**/rollout-*.jsonl` | 完整会话事件流 |
| Codex | `~/.codex/history.jsonl` | 用户命令历史 |
```

In `README.en.md`, add the equivalent English section:

```markdown
## Data Sources

| Source | Path | Contents |
|--------|------|----------|
| Claude | `~/.claude/history.jsonl` | User command history |
| Claude | `~/.claude/plans/*.md` | Implementation plans |
| Claude | `~/.claude/projects/<dir>/*.jsonl` | Project sessions |
| Codex | `~/.codex/state_5.sqlite` | Thread index, cwd, model, rollout paths |
| Codex | `~/.codex/sessions/**/rollout-*.jsonl` | Full conversation event streams |
| Codex | `~/.codex/history.jsonl` | User command history |
```

- [ ] **Step 2: Run backend tests**

Run:

```bash
python -m unittest tests.test_codex_provider tests.test_provider_registry -v
```

Expected: PASS.

- [ ] **Step 3: Run frontend tests**

Run:

```bash
cd web && npm run test:run
```

Expected: PASS.

- [ ] **Step 4: Run production build**

Run:

```bash
cd web && npm run build
```

Expected: PASS.

- [ ] **Step 5: Run backend smoke checks**

Start server:

```bash
python server.py --no-open --port 8787
```

In a second terminal, run:

```bash
curl -s http://127.0.0.1:8787/api/sources
curl -s http://127.0.0.1:8787/api/claude/projects
curl -s http://127.0.0.1:8787/api/codex/projects
```

Expected:

- `/api/sources` returns `claude` and `codex`.
- `/api/claude/projects` returns the same shape as the old `/api/projects`.
- `/api/codex/projects` returns Codex projects when `~/.codex/state_5.sqlite` exists, or a clear 404 unavailable error when it does not.

Stop the server with `Ctrl-C`.

- [ ] **Step 6: Commit**

```bash
git add README.md README.en.md
git commit -m "docs: describe claude and codex sources"
```

---

## Final Verification

Run all verification commands:

```bash
python -m unittest tests.test_codex_provider tests.test_provider_registry -v
cd web && npm run test:run
cd web && npm run build
```

Expected:

- Python unittest reports all backend tests passing.
- Vitest reports all frontend tests passing.
- Vite build completes successfully.

Then run:

```bash
git status --short
```

Expected: no unstaged or uncommitted implementation changes remain, except intentional local files the user already had before the work.
