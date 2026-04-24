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
    conn.execute(
        """
        CREATE TABLE thread_spawn_edges (
            parent_thread_id TEXT NOT NULL,
            child_thread_id TEXT NOT NULL PRIMARY KEY,
            status TEXT NOT NULL
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

    def test_source_marked_subagent_threads_are_excluded_without_spawn_edge(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            conn = create_codex_state(root)
            insert_thread(conn, root, "thread-a", "/repo/alpha", "Alpha title", "build alpha", 1000, 3000)
            insert_thread(
                conn,
                root,
                "guardian-thread",
                "/repo/alpha",
                "Guardian title",
                "The following is the Codex agent history whose request action you are assessing.",
                2000,
                4000,
            )
            conn.execute(
                "UPDATE threads SET source = ? WHERE id = ?",
                (json.dumps({"subagent": {"other": "guardian"}}), "guardian-thread"),
            )
            conn.commit()
            conn.close()

            provider = CodexProvider(root=root)
            project_id = provider.list_projects()[0]["id"]
            detail = provider.get_project(project_id)

            self.assertEqual([session["id"] for session in detail["sessions"]], ["thread-a"])
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

    def test_ordering_falls_back_to_updated_at_when_updated_at_ms_is_null(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            conn = create_codex_state(root)
            insert_thread(conn, root, "alpha-old", "/repo/alpha", "Alpha old", "old alpha", 1000, 1000)
            insert_thread(conn, root, "alpha-fallback", "/repo/alpha", "Alpha new", "new alpha", 1000, 1000)
            insert_thread(conn, root, "beta-fallback", "/repo/beta", "Beta new", "new beta", 1000, 1000)
            conn.execute(
                "UPDATE threads SET updated_at_ms = NULL, updated_at = ? WHERE id = ?",
                (10, "alpha-fallback"),
            )
            conn.execute(
                "UPDATE threads SET updated_at_ms = NULL, updated_at = ? WHERE id = ?",
                (20, "beta-fallback"),
            )
            conn.commit()
            conn.close()

            provider = CodexProvider(root=root)
            projects = provider.list_projects()
            alpha_project_id = next(project["id"] for project in projects if project["path"] == "/repo/alpha")
            alpha_detail = provider.get_project(alpha_project_id)

            self.assertEqual([project["path"] for project in projects], ["/repo/beta", "/repo/alpha"])
            self.assertEqual([session["id"] for session in alpha_detail["sessions"]], ["alpha-fallback", "alpha-old"])

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
                    "payload": {
                        "id": "thread-a",
                        "cwd": "/repo/alpha",
                        "source": "cli",
                        "model_provider": "openai",
                    },
                },
                {
                    "timestamp": "2026-04-24T10:00:01Z",
                    "type": "event_msg",
                    "payload": {
                        "type": "user_message",
                        "message": "run pwd",
                        "images": [],
                        "local_images": [],
                        "text_elements": [],
                    },
                },
                {
                    "timestamp": "2026-04-24T10:00:02Z",
                    "type": "response_item",
                    "payload": {"type": "reasoning", "summary": [{"text": "Need to inspect cwd"}], "content": None},
                },
                {
                    "timestamp": "2026-04-24T10:00:03Z",
                    "type": "response_item",
                    "payload": {
                        "type": "function_call",
                        "name": "exec_command",
                        "arguments": "{\"cmd\":\"pwd\"}",
                        "call_id": "call-1",
                    },
                },
                {
                    "timestamp": "2026-04-24T10:00:04Z",
                    "type": "response_item",
                    "payload": {
                        "type": "function_call",
                        "name": "exec_command",
                        "arguments": "{\"cmd\":\"ls\"}",
                        "call_id": "call-2",
                    },
                },
                {
                    "timestamp": "2026-04-24T10:00:05Z",
                    "type": "response_item",
                    "payload": {
                        "type": "exec_command_end",
                        "call_id": "call-2",
                        "command": ["ls"],
                        "cwd": "/repo/alpha",
                        "stdout": "README.md\n",
                        "stderr": "",
                        "aggregated_output": "README.md\n",
                        "formatted_output": "README.md\n",
                        "exit_code": 0,
                        "duration": {"secs": 0, "nanos": 1000},
                        "status": "completed",
                    },
                },
                {
                    "timestamp": "2026-04-24T10:00:06Z",
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": "The repo contains README.md."}],
                    },
                },
            ]
            rollout.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

            provider = CodexProvider(root=root)
            project_id = provider.list_projects()[0]["id"]
            session = provider.get_session(project_id, "thread-a")

            self.assertEqual(session["session_id"], "thread-a")
            self.assertEqual(session["project_id"], project_id)
            self.assertEqual(session["source"], "codex")
            self.assertEqual(session["total_raw_messages"], len(events))
            self.assertEqual(session["subagents"], [])
            self.assertEqual(session["metadata"]["cwd"], "/repo/alpha")
            self.assertEqual(session["metadata"]["source"], "cli")
            self.assertEqual(session["metadata"]["source_provider"], "codex")
            self.assertEqual(session["metadata"]["model_provider"], "openai")

            self.assertEqual([m["role"] for m in session["conversation"]], ["user", "assistant"])
            user = session["conversation"][0]
            self.assertEqual(user["content"], "run pwd")
            self.assertEqual(user["metadata"]["source"], "codex")

            assistant = session["conversation"][1]
            self.assertEqual(assistant["thinking"], "Need to inspect cwd")
            self.assertEqual(assistant["content"], "The repo contains README.md.")
            self.assertEqual(assistant["model"], "gpt-5.5")
            self.assertEqual(assistant["timestamp"], "2026-04-24T10:00:02Z")
            self.assertEqual(assistant["tool_uses"][0]["id"], "call-1")
            self.assertEqual(assistant["tool_uses"][0]["name"], "exec_command")
            self.assertEqual(assistant["tool_uses"][0]["input"], {"cmd": "pwd"})
            self.assertEqual(assistant["tool_uses"][1]["id"], "call-2")
            self.assertEqual(assistant["tool_uses"][1]["input"], {"cmd": "ls"})
            self.assertEqual(assistant["tool_results"][0]["tool_use_id"], "call-2")
            self.assertEqual(assistant["tool_results"][0]["content"], "README.md\n")
            self.assertFalse(assistant["tool_results"][0]["is_error"])
            result_metadata = assistant["tool_results"][0]["metadata"]
            self.assertEqual(result_metadata["exit_code"], 0)
            self.assertEqual(result_metadata["cwd"], "/repo/alpha")
            self.assertEqual(result_metadata["command"], ["ls"])
            self.assertEqual(result_metadata["stdout"], "README.md\n")
            self.assertEqual(result_metadata["stderr"], "")
            self.assertEqual(result_metadata["duration"], {"secs": 0, "nanos": 1000})
            self.assertEqual(result_metadata["status"], "completed")

    def test_rollout_metadata_events_do_not_create_chat_bubbles_and_agent_phase_maps_role(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            conn = create_codex_state(root)
            rollout = insert_thread(conn, root, "thread-a", "/repo/alpha", "Alpha", "check status", 1000, 4000)
            conn.close()
            events = [
                {
                    "timestamp": "2026-04-24T10:00:00Z",
                    "type": "turn_context",
                    "payload": {
                        "type": "turn_context",
                        "approval_policy": "on-request",
                        "sandbox_policy": {"mode": "workspace-write"},
                        "current_date": "2026-04-24",
                        "timezone": "Asia/Shanghai",
                    },
                },
                {
                    "timestamp": "2026-04-24T10:00:01Z",
                    "type": "token_count",
                    "payload": {"type": "token_count", "input_tokens": 12, "output_tokens": 3},
                },
                {
                    "timestamp": "2026-04-24T10:00:02Z",
                    "type": "response_item",
                    "payload": {"type": "agent_message", "phase": "final", "message": "Agent final answer"},
                },
                {
                    "timestamp": "2026-04-24T10:00:03Z",
                    "type": "response_item",
                    "payload": {"type": "agent_message", "phase": "started", "message": "Agent started"},
                },
            ]
            rollout.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

            provider = CodexProvider(root=root)
            project_id = provider.list_projects()[0]["id"]
            session = provider.get_session(project_id, "thread-a")

            self.assertEqual(len(session["conversation"]), 2)
            self.assertEqual([m["role"] for m in session["conversation"]], ["assistant", "event"])
            self.assertEqual(session["conversation"][0]["content"], "Agent final answer")
            self.assertEqual(session["conversation"][0]["metadata"]["phase"], "final")
            self.assertEqual(session["conversation"][1]["content"], "Agent started")
            self.assertEqual(session["conversation"][1]["metadata"]["phase"], "started")
            self.assertEqual(session["metadata"]["approval_policy"], "on-request")
            self.assertEqual(session["metadata"]["sandbox_policy"], {"mode": "workspace-write"})
            self.assertEqual(session["metadata"]["current_date"], "2026-04-24")
            self.assertEqual(session["metadata"]["timezone"], "Asia/Shanghai")
            self.assertEqual(session["metadata"]["last_token_count"], events[1]["payload"])

    def test_duplicate_agent_message_is_suppressed_when_canonical_assistant_message_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            conn = create_codex_state(root)
            rollout = insert_thread(conn, root, "thread-a", "/repo/alpha", "Alpha", "summarize", 1000, 4000)
            conn.close()
            events = [
                {
                    "timestamp": "2026-04-24T10:00:00Z",
                    "type": "event_msg",
                    "payload": {
                        "type": "user_message",
                        "message": "summarize",
                        "images": [],
                        "local_images": [],
                        "text_elements": [],
                    },
                },
                {
                    "timestamp": "2026-04-24T10:00:01Z",
                    "type": "event_msg",
                    "payload": {
                        "type": "agent_message",
                        "phase": "final",
                        "message": "The final answer appears once.",
                    },
                },
                {
                    "timestamp": "2026-04-24T10:00:02Z",
                    "type": "event_msg",
                    "payload": {
                        "type": "agent_message",
                        "phase": "started",
                        "message": "Preparing summary",
                    },
                },
                {
                    "timestamp": "2026-04-24T10:00:03Z",
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": "The final answer appears once."}],
                    },
                },
            ]
            rollout.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

            provider = CodexProvider(root=root)
            project_id = provider.list_projects()[0]["id"]
            session = provider.get_session(project_id, "thread-a")

            contents = [message["content"] for message in session["conversation"]]
            self.assertEqual(contents.count("The final answer appears once."), 1)
            self.assertIn("Preparing summary", contents)
            self.assertEqual(
                [(message["role"], message["content"]) for message in session["conversation"]],
                [
                    ("user", "summarize"),
                    ("event", "Preparing summary"),
                    ("assistant", "The final answer appears once."),
                ],
            )

    def test_transcript_internal_and_user_messages_do_not_render_as_chat_bubbles(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            conn = create_codex_state(root)
            rollout = insert_thread(conn, root, "thread-a", "/repo/alpha", "Alpha", "hello", 1000, 4000)
            conn.close()
            events = [
                {
                    "timestamp": "2026-04-24T10:00:00Z",
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "developer",
                        "content": [{"type": "input_text", "text": "Do not leak developer setup"}],
                    },
                },
                {
                    "timestamp": "2026-04-24T10:00:01Z",
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "user",
                        "content": [{"type": "input_text", "text": "transcript duplicate hello"}],
                    },
                },
                {
                    "timestamp": "2026-04-24T10:00:02Z",
                    "type": "event_msg",
                    "payload": {
                        "type": "user_message",
                        "message": "hello",
                        "images": [],
                        "local_images": [],
                        "text_elements": [],
                    },
                },
                {
                    "timestamp": "2026-04-24T10:00:03Z",
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": "Visible assistant reply"}],
                    },
                },
            ]
            rollout.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

            provider = CodexProvider(root=root)
            project_id = provider.list_projects()[0]["id"]
            session = provider.get_session(project_id, "thread-a")

            self.assertEqual([message["role"] for message in session["conversation"]], ["user", "assistant"])
            self.assertEqual(session["conversation"][0]["content"], "hello")
            self.assertEqual(session["conversation"][1]["content"], "Visible assistant reply")
            session_json = json.dumps(session)
            self.assertNotIn("Do not leak developer setup", session_json)
            self.assertNotIn("transcript duplicate hello", session_json)
            self.assertEqual(session["metadata"]["internal_message_counts"]["developer"], 1)
            self.assertEqual(session["metadata"]["internal_message_counts"]["user"], 1)

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
                    "payload": {
                        "type": "reasoning",
                        "summary": [],
                        "content": None,
                        "encrypted_content": "secret-ciphertext",
                    },
                },
            ]
            rollout.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

            provider = CodexProvider(root=root)
            project_id = provider.list_projects()[0]["id"]
            session = provider.get_session(project_id, "thread-a")

            self.assertNotIn("secret-ciphertext", json.dumps(session))
            self.assertEqual(session["conversation"], [])
            self.assertTrue(session["metadata"]["reasoning_encrypted"])

    def test_subagent_threads_are_attached_to_parent_not_top_level_sessions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            conn = create_codex_state(root)
            parent_rollout = insert_thread(
                conn, root, "parent-thread", "/repo/alpha", "Parent", "delegate work", 1000, 4000
            )
            child_rollout = insert_thread(
                conn, root, "child-thread", "/repo/alpha", "Worker task", "worker prompt", 2000, 3000
            )
            conn.execute(
                "UPDATE threads SET agent_nickname = ?, agent_role = ? WHERE id = ?",
                ("Kuhn", "worker", "child-thread"),
            )
            conn.execute(
                "INSERT INTO thread_spawn_edges (parent_thread_id, child_thread_id, status) VALUES (?, ?, ?)",
                ("parent-thread", "child-thread", "closed"),
            )
            conn.commit()
            conn.close()

            parent_events = [
                {
                    "timestamp": "2026-04-24T10:00:00Z",
                    "type": "event_msg",
                    "payload": {"type": "user_message", "message": "delegate work"},
                },
                {
                    "timestamp": "2026-04-24T10:00:01Z",
                    "type": "response_item",
                    "payload": {
                        "type": "function_call",
                        "name": "spawn_agent",
                        "arguments": "{\"agent_type\":\"worker\",\"message\":\"worker prompt\"}",
                        "call_id": "spawn-1",
                    },
                },
                {
                    "timestamp": "2026-04-24T10:00:02Z",
                    "type": "response_item",
                    "payload": {
                        "type": "function_call_output",
                        "call_id": "spawn-1",
                        "output": "{\"agent_id\":\"child-thread\",\"nickname\":\"Kuhn\"}",
                    },
                },
                {
                    "timestamp": "2026-04-24T10:00:03Z",
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": "Worker is complete."}],
                    },
                },
            ]
            parent_rollout.write_text(
                "\n".join(json.dumps(event) for event in parent_events) + "\n",
                encoding="utf-8",
            )

            child_events = [
                {
                    "timestamp": "2026-04-24T10:00:00Z",
                    "type": "session_meta",
                    "payload": {
                        "id": "child-thread",
                        "cwd": "/repo/alpha",
                        "source": {
                            "subagent": {
                                "thread_spawn": {
                                    "parent_thread_id": "parent-thread",
                                    "depth": 1,
                                    "agent_nickname": "Kuhn",
                                    "agent_role": "worker",
                                }
                            }
                        },
                        "model_provider": "openai",
                    },
                },
                {
                    "timestamp": "2026-04-24T10:00:01Z",
                    "type": "event_msg",
                    "payload": {"type": "user_message", "message": "worker prompt"},
                },
                {
                    "timestamp": "2026-04-24T10:00:02Z",
                    "type": "response_item",
                    "payload": {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": "worker done"}],
                    },
                },
            ]
            child_rollout.write_text(
                "\n".join(json.dumps(event) for event in child_events) + "\n",
                encoding="utf-8",
            )

            (root / "history.jsonl").write_text(
                "\n".join(
                    [
                        json.dumps({"session_id": "parent-thread", "ts": 1777000000000, "text": "delegate work"}),
                        json.dumps({"session_id": "child-thread", "ts": 1777000001000, "text": "worker prompt"}),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            provider = CodexProvider(root=root)
            project_id = provider.list_projects()[0]["id"]
            project = provider.get_project(project_id)
            session = provider.get_session(project_id, "parent-thread")
            subagent = provider.get_subagent(project_id, "parent-thread", "child-thread")
            history = provider.get_history(page=1, limit=50, search=None, project=None)

            self.assertEqual([item["id"] for item in project["sessions"]], ["parent-thread"])
            self.assertEqual([item["sessionId"] for item in history["items"]], ["parent-thread"])
            self.assertEqual(len(session["subagents"]), 1)
            self.assertEqual(session["subagents"][0]["filename"], "child-thread")
            self.assertEqual(session["subagents"][0]["type"], "worker")
            self.assertEqual(session["subagents"][0]["nickname"], "Kuhn")
            self.assertEqual(session["subagents"][0]["status"], "closed")
            self.assertEqual(session["subagents"][0]["size"], child_rollout.stat().st_size)
            self.assertEqual(session["conversation"][1]["tool_uses"][0]["name"], "spawn_agent")
            self.assertEqual(session["conversation"][1]["tool_uses"][0]["metadata"]["agent_id"], "child-thread")
            self.assertEqual(session["conversation"][1]["tool_uses"][0]["metadata"]["agent_nickname"], "Kuhn")
            self.assertEqual([message["content"] for message in subagent["conversation"]], ["worker prompt", "worker done"])
            self.assertEqual(subagent["metadata"]["parent_thread_id"], "parent-thread")

            with self.assertRaises(FileNotFoundError):
                provider.get_session(project_id, "child-thread")

    def test_custom_tool_call_is_reconstructed_as_tool_use(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            conn = create_codex_state(root)
            rollout = insert_thread(conn, root, "thread-a", "/repo/alpha", "Alpha", "patch", 1000, 4000)
            conn.close()
            events = [
                {
                    "timestamp": "2026-04-24T10:00:00Z",
                    "type": "response_item",
                    "payload": {
                        "type": "custom_tool_call",
                        "name": "apply_patch",
                        "call_id": "patch-1",
                        "input": "*** Begin Patch\n*** End Patch\n",
                    },
                },
                {
                    "timestamp": "2026-04-24T10:00:01Z",
                    "type": "response_item",
                    "payload": {"type": "function_call_output", "call_id": "patch-1", "output": "Done"},
                },
            ]
            rollout.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

            provider = CodexProvider(root=root)
            project_id = provider.list_projects()[0]["id"]
            session = provider.get_session(project_id, "thread-a")

            tool = session["conversation"][0]["tool_uses"][0]
            self.assertEqual(tool["name"], "apply_patch")
            self.assertEqual(tool["input"], {"input": "*** Begin Patch\n*** End Patch\n"})
            self.assertEqual(session["conversation"][0]["tool_results"][0]["content"], "Done")


if __name__ == "__main__":
    unittest.main()
