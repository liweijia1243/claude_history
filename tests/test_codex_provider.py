import json
import sqlite3
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

    def test_archived_threads_are_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            conn = create_codex_state(root)
            insert_thread(conn, root, "thread-a", "/repo/alpha", "Alpha title", "build alpha", 1000, 3000)
            insert_thread(conn, root, "thread-b", "/repo/beta", "Beta title", "build beta", 2000, 4000)
            conn.execute("UPDATE threads SET archived = 1 WHERE id = ?", ("thread-b",))
            conn.commit()
            conn.close()

            provider = CodexProvider(root=root)
            projects = provider.list_projects()

            self.assertEqual([p["path"] for p in projects], ["/repo/alpha"])
            self.assertEqual(provider.get_stats()["total_sessions"], 1)

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
                "\n".join(
                    [
                        json.dumps({"session_id": "thread-a", "ts": 1777000000000, "text": "build alpha"}),
                        json.dumps({"session_id": "thread-a", "ts": 1777000001000, "text": "unrelated command"}),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            provider = CodexProvider(root=root)
            history = provider.get_history(page=1, limit=50, search="alpha", project=None)

            self.assertEqual(history["total"], 1)
            item = history["items"][0]
            self.assertEqual(item["sessionId"], "thread-a")
            self.assertEqual(item["timestamp"], 1777000000000)
            self.assertEqual(item["display"], "build alpha")
            self.assertEqual(item["project"], "/repo/alpha")
            self.assertEqual(item["project_id"], provider.list_projects()[0]["id"])
            self.assertEqual(item["source"], "codex")

            missing = provider.get_history(page=1, limit=50, search="missing", project=None)

            self.assertEqual(missing["total"], 0)
            self.assertEqual(missing["items"], [])


if __name__ == "__main__":
    unittest.main()
