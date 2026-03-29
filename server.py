"""Claude History Viewer - FastAPI Backend"""
import json
import os
import glob
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

CLAUDE_DIR = Path(os.path.expanduser("~/.claude"))

app = FastAPI(title="Claude History Viewer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def read_jsonl(path: Path, limit: int = 0):
    """Read a JSONL file and return list of parsed JSON objects."""
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
    return items


def find_string_line(content: str, search_string: str) -> int | None:
    """Find the 1-indexed line number where search_string starts."""
    if not content or not search_string:
        return None

    lines = content.split("\n")
    search_lines = search_string.split("\n")
    first_line = search_lines[0] if search_lines else ""

    for i, line in enumerate(lines):
        if line == first_line:
            # Verify full match
            match = True
            for j, search_line in enumerate(search_lines):
                if i + j >= len(lines) or lines[i + j] != search_line:
                    match = False
                    break
            if match:
                return i + 1  # 1-indexed
    return None


def build_file_timeline(messages: list[dict]) -> dict:
    """Build timeline of file states from file-history-snapshot messages."""
    file_timeline = {}  # file_path -> [{"message_id", "backup_file", "time", "idx"}]

    for idx, msg in enumerate(messages):
        if msg.get("type") != "file-history-snapshot":
            continue

        snapshot = msg.get("snapshot", {})
        backups = snapshot.get("trackedFileBackups", {})
        message_id = msg.get("messageId")

        for file_path, info in backups.items():
            file_timeline.setdefault(file_path, []).append({
                "message_id": message_id,
                "backup_file": info.get("backupFileName"),
                "time": info.get("backupTime"),
                "idx": idx
            })

    return file_timeline


def find_state_before(timeline: dict, file_path: str, current_idx: int) -> dict | None:
    """Find the most recent file state before the given message index."""
    states = timeline.get(file_path, [])
    before = [s for s in states if s["idx"] < current_idx]
    return max(before, key=lambda s: s["idx"]) if before else None


def enrich_tool_uses_with_line_numbers(messages: list[dict]) -> list[dict]:
    """Add startLine to Edit tool uses based on file-history snapshots."""
    file_timeline = build_file_timeline(messages)

    for idx, msg in enumerate(messages):
        if msg.get("type") != "assistant":
            continue

        content_blocks = msg.get("message", {}).get("content", [])
        for block in content_blocks:
            if not isinstance(block, dict):
                continue
            if block.get("type") != "tool_use":
                continue
            if block.get("name") != "Edit":
                continue

            input_data = block.get("input", {})
            file_path = input_data.get("file_path", "")
            old_string = input_data.get("old_string", "")

            if not file_path or not old_string:
                continue

            state = find_state_before(file_timeline, file_path, idx)
            if not state:
                continue

            backup_path = CLAUDE_DIR / "file-history" / state["message_id"] / state["backup_file"]
            if not backup_path.exists():
                continue

            try:
                content = backup_path.read_text(encoding="utf-8")
                start_line = find_string_line(content, old_string)
                if start_line is not None:
                    block["startLine"] = start_line
            except Exception:
                pass

    return messages


def reconstruct_conversation(messages: list[dict]) -> list[dict]:
    """Reconstruct a conversation thread from raw JSONL messages.

    Groups user messages, assistant messages, and tool results together.
    Enriches Edit tool uses with line numbers from file history.
    """
    # First, enrich tool uses with line numbers
    messages = enrich_tool_uses_with_line_numbers(messages)

    uuid_map = {m.get("uuid"): m for m in messages if m.get("uuid")}
    conversation = []
    assistant_buffer = None

    for msg in messages:
        msg_type = msg.get("type")

        if msg_type == "user":
            content = msg.get("message", {}).get("content", "")
            # Check if this is a tool result
            if isinstance(content, list):
                has_tool_result = any(
                    isinstance(c, dict) and c.get("type") == "tool_result"
                    for c in content
                )
                if has_tool_result:
                    # Attach tool results to the previous assistant message
                    if assistant_buffer is not None:
                        tool_results = []
                        for c in content:
                            if isinstance(c, dict) and c.get("type") == "tool_result":
                                tool_results.append({
                                    "tool_use_id": c.get("tool_use_id", ""),
                                    "content": c.get("content", ""),
                                    "is_error": c.get("is_error", False),
                                })
                        assistant_buffer["tool_results"] = tool_results
                    continue

            # Regular user message
            if assistant_buffer is not None:
                conversation.append(assistant_buffer)
                assistant_buffer = None

            text = ""
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                parts = []
                for c in content:
                    if isinstance(c, dict):
                        if c.get("type") == "text":
                            parts.append(c.get("text", ""))
                        elif c.get("type") == "tool_result":
                            pass  # handled above
                    elif isinstance(c, str):
                        parts.append(c)
                text = "\n".join(parts)

            conversation.append({
                "role": "user",
                "content": text,
                "timestamp": msg.get("timestamp", ""),
                "uuid": msg.get("uuid", ""),
            })

        elif msg_type == "assistant":
            if assistant_buffer is not None:
                conversation.append(assistant_buffer)

            message_data = msg.get("message", {})
            content_blocks = message_data.get("content", [])

            text_parts = []
            thinking_parts = []
            tool_uses = []

            for block in content_blocks:
                if not isinstance(block, dict):
                    continue
                block_type = block.get("type", "")
                if block_type == "text":
                    text_parts.append(block.get("text", ""))
                elif block_type == "thinking":
                    thinking_parts.append(block.get("thinking", ""))
                elif block_type == "tool_use":
                    tool_uses.append({
                        "id": block.get("id", ""),
                        "name": block.get("name", ""),
                        "input": block.get("input", {}),
                    })

            model = message_data.get("model", "")
            usage = message_data.get("usage", {})

            assistant_buffer = {
                "role": "assistant",
                "content": "\n".join(text_parts),
                "thinking": "\n".join(thinking_parts),
                "tool_uses": tool_uses,
                "tool_results": [],
                "model": model,
                "usage": usage,
                "timestamp": msg.get("timestamp", ""),
                "uuid": msg.get("uuid", ""),
            }

    if assistant_buffer is not None:
        conversation.append(assistant_buffer)

    return conversation


def build_session_project_map():
    """Build a mapping from session_id to project_id by scanning project directories."""
    projects_dir = CLAUDE_DIR / "projects"
    mapping = {}
    if not projects_dir.exists():
        return mapping
    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue
        for session_file in project_dir.glob("*.jsonl"):
            mapping[session_file.stem] = project_dir.name
    return mapping


# ── API Routes ───────────────────────────────────────────────────────────────

@app.get("/api/stats")
def get_stats():
    """Get overview statistics."""
    # History stats
    history = read_jsonl(CLAUDE_DIR / "history.jsonl")
    history_count = len(history)

    # Plans stats
    plans_dir = CLAUDE_DIR / "plans"
    plan_files = list(plans_dir.glob("*.md")) if plans_dir.exists() else []

    # Projects stats
    projects_dir = CLAUDE_DIR / "projects"
    project_dirs = []
    session_count = 0
    if projects_dir.exists():
        for d in projects_dir.iterdir():
            if d.is_dir():
                project_dirs.append(d.name)
                session_count += len(list(d.glob("*.jsonl")))

    # Recent activity (last 24h)
    now_ms = datetime.now().timestamp() * 1000
    day_ago = now_ms - 86400000
    recent_commands = sum(
        1 for h in history if h.get("timestamp", 0) > day_ago
    )

    return {
        "total_commands": history_count,
        "total_plans": len(plan_files),
        "total_projects": len(project_dirs),
        "total_sessions": session_count,
        "recent_commands_24h": recent_commands,
    }


@app.get("/api/recent-sessions")
def get_recent_sessions(limit: int = Query(5, ge=1, le=20)):
    """Get most recent sessions across all projects."""
    projects_dir = CLAUDE_DIR / "projects"
    if not projects_dir.exists():
        return []

    all_sessions = []
    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue

        # Get actual project path from first session's cwd
        project_path = project_dir.name
        for sf in project_dir.glob("*.jsonl"):
            msgs = read_jsonl(sf, limit=5)
            for m in msgs:
                cwd = m.get("cwd", "")
                if cwd:
                    project_path = cwd
                    break
            break

        for session_file in project_dir.glob("*.jsonl"):
            messages = read_jsonl(session_file, limit=10)
            first_msg = next((m for m in messages if m.get("type") == "user"), None)

            preview = ""
            if first_msg:
                content = first_msg.get("message", {}).get("content", "")
                if isinstance(content, str):
                    preview = content[:150]
                elif isinstance(content, list):
                    for c in content:
                        if isinstance(c, dict) and c.get("type") == "text":
                            preview = c.get("text", "")[:150]
                            break

            stat = session_file.stat()
            all_sessions.append({
                "session_id": session_file.stem,
                "project_id": project_dir.name,
                "project_path": project_path,
                "preview": preview,
                "message_count": len(read_jsonl(session_file)),
                "timestamp": stat.st_mtime,
                "size": stat.st_size,
            })

    # Sort by timestamp descending
    all_sessions.sort(key=lambda x: x["timestamp"], reverse=True)
    return all_sessions[:limit]


@app.get("/api/history")
def get_history(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None),
    project: Optional[str] = Query(None),
):
    """Get command history with pagination and filtering."""
    history = read_jsonl(CLAUDE_DIR / "history.jsonl")

    # Reverse to show newest first
    history.reverse()

    # Filter
    if search:
        search_lower = search.lower()
        history = [
            h for h in history
            if search_lower in h.get("display", "").lower()
        ]
    if project:
        history = [
            h for h in history
            if project in h.get("project", "")
        ]

    total = len(history)
    start = (page - 1) * limit
    items = history[start : start + limit]

    # Enrich items with project_id
    session_map = build_session_project_map()
    for item in items:
        sid = item.get("sessionId", "")
        item["project_id"] = session_map.get(sid, "")

    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
    }


@app.get("/api/plans")
def get_plans():
    """List all plans."""
    plans_dir = CLAUDE_DIR / "plans"
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


@app.get("/api/plans/{name}")
def get_plan(name: str):
    """Get a specific plan's content."""
    plan_path = CLAUDE_DIR / "plans" / f"{name}.md"
    if not plan_path.exists():
        raise HTTPException(404, "Plan not found")
    return {
        "name": name,
        "content": plan_path.read_text(encoding="utf-8"),
    }


@app.get("/api/projects")
def get_projects():
    """List all projects."""
    projects_dir = CLAUDE_DIR / "projects"
    if not projects_dir.exists():
        return []

    projects = []
    for d in sorted(projects_dir.iterdir()):
        if not d.is_dir():
            continue
        sessions_files = list(d.glob("*.jsonl"))

        # Try to get actual cwd from first session's messages
        actual_path = ""
        for sf in sessions_files[:1]:
            msgs = read_jsonl(sf, limit=5)
            for m in msgs:
                cwd = m.get("cwd", "")
                if cwd:
                    actual_path = cwd
                    break

        projects.append({
            "id": d.name,
            "path": actual_path or d.name,
            "display_name": d.name,
            "session_count": len(sessions_files),
            "size": sum(f.stat().st_size for f in sessions_files),
        })
    return projects


@app.get("/api/projects/{project_id}")
def get_project_detail(project_id: str):
    """Get project details with sessions sorted by modification time."""
    project_dir = CLAUDE_DIR / "projects" / project_id
    if not project_dir.exists():
        raise HTTPException(404, "Project not found")

    # Get actual path from first session's cwd
    actual_path = ""
    sessions_files = list(project_dir.glob("*.jsonl"))
    for sf in sessions_files[:1]:
        msgs = read_jsonl(sf, limit=5)
        for m in msgs:
            cwd = m.get("cwd", "")
            if cwd:
                actual_path = cwd
                break

    # Get sessions sorted by mtime descending
    sessions = []
    for f in project_dir.glob("*.jsonl"):
        messages = read_jsonl(f, limit=10)
        first_msg = next((m for m in messages if m.get("type") == "user"), None)

        preview = ""
        if first_msg:
            content = first_msg.get("message", {}).get("content", "")
            if isinstance(content, str):
                preview = content[:150]
            elif isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "text":
                        preview = c.get("text", "")[:150]
                        break

        stat = f.stat()
        sessions.append({
            "id": f.stem,
            "preview": preview,
            "message_count": len(read_jsonl(f)),
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "created": stat.st_ctime,
        })

    sessions.sort(key=lambda x: x["modified"], reverse=True)

    return {
        "id": project_id,
        "path": actual_path or project_id,
        "sessions": sessions,
    }


@app.get("/api/projects/{project_id}/sessions")
def get_project_sessions(project_id: str):
    """List sessions for a project."""
    project_dir = CLAUDE_DIR / "projects" / project_id
    if not project_dir.exists():
        raise HTTPException(404, "Project not found")

    sessions = []
    for f in sorted(project_dir.glob("*.jsonl")):
        messages = read_jsonl(f)
        # Extract session info
        first_msg = next((m for m in messages if m.get("type") == "user"), None)
        last_msg = next(
            (m for m in reversed(messages) if m.get("type") in ("user", "assistant")),
            None,
        )

        # Get first user message as preview
        preview = ""
        if first_msg:
            content = first_msg.get("message", {}).get("content", "")
            if isinstance(content, str):
                preview = content[:200]
            elif isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "text":
                        preview = c.get("text", "")[:200]
                        break

        session_id = f.stem
        stat = f.stat()

        # Count message types
        msg_types = {}
        for m in messages:
            t = m.get("type", "unknown")
            msg_types[t] = msg_types.get(t, 0) + 1

        sessions.append({
            "id": session_id,
            "preview": preview,
            "message_count": len(messages),
            "message_types": msg_types,
            "size": stat.st_size,
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
            "first_timestamp": first_msg.get("timestamp", "") if first_msg else "",
            "last_timestamp": last_msg.get("timestamp", "") if last_msg else "",
        })

    sessions.sort(key=lambda x: x["modified"], reverse=True)
    return sessions


@app.get("/api/projects/{project_id}/sessions/{session_id}")
def get_session_conversation(project_id: str, session_id: str):
    """Get a session's conversation as a reconstructed thread."""
    session_path = CLAUDE_DIR / "projects" / project_id / f"{session_id}.jsonl"
    if not session_path.exists():
        raise HTTPException(404, "Session not found")

    messages = read_jsonl(session_path)
    conversation = reconstruct_conversation(messages)

    # Get subagent info
    subagents_dir = CLAUDE_DIR / "projects" / project_id / session_id / "subagents"
    subagents = []
    if subagents_dir.exists():
        for f in subagents_dir.glob("*.jsonl"):
            meta_path = f.with_suffix(".meta.json")
            meta = {}
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text())
                except Exception:
                    pass
            subagents.append({
                "filename": f.name,
                "type": meta.get("agentType", "Unknown"),
                "size": f.stat().st_size,
            })

    return {
        "session_id": session_id,
        "project_id": project_id,
        "total_raw_messages": len(messages),
        "conversation": conversation,
        "subagents": subagents,
    }


@app.get("/api/projects/{project_id}/sessions/{session_id}/subagents/{agent_file}")
def get_subagent_conversation(project_id: str, session_id: str, agent_file: str):
    """Get a subagent's conversation."""
    agent_path = (
        CLAUDE_DIR / "projects" / project_id / session_id / "subagents" / agent_file
    )
    if not agent_path.exists():
        raise HTTPException(404, "Subagent not found")

    messages = read_jsonl(agent_path)
    conversation = reconstruct_conversation(messages)
    return {
        "conversation": conversation,
        "total_raw_messages": len(messages),
    }


# ── Serve Frontend ───────────────────────────────────────────────────────────

# In development, Vite serves the frontend on port 5173
# In production, serve the built files
dist_dir = Path(__file__).parent / "web" / "dist"
if dist_dir.exists():
    app.mount("/assets", StaticFiles(directory=dist_dir / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = dist_dir / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(dist_dir / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8787)
