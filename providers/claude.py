import json
import os
import time as _time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import HistoryProvider


class ClaudeProvider(HistoryProvider):
    id = "claude"
    name = "Claude"
    _CACHE_TTL = 300

    def __init__(self, root: Optional[Path] = None):
        self.root = root or Path(os.path.expanduser("~/.claude"))
        self._dashboard_cache = {}  # type: Dict[str, Dict[str, Any]]

    def available(self) -> bool:
        return self.root.exists()

    def _read_jsonl(self, path: Path, limit: int = 0) -> List[Dict[str, Any]]:
        """Read a JSONL file and return list of parsed JSON objects."""
        items = []  # type: List[Dict[str, Any]]
        if not path.exists():
            return items
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                items.append(item)
        return items

    @staticmethod
    def _find_string_line(content: str, search_string: str) -> Optional[int]:
        """Find the 1-indexed line number where search_string starts."""
        if not content or not search_string:
            return None

        lines = content.split("\n")
        search_lines = search_string.split("\n")
        first_line = search_lines[0] if search_lines else ""

        for i, line in enumerate(lines):
            if line == first_line:
                match = True
                for j, search_line in enumerate(search_lines):
                    if i + j >= len(lines) or lines[i + j] != search_line:
                        match = False
                        break
                if match:
                    return i + 1
        return None

    @staticmethod
    def _build_file_timeline(messages: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Build timeline of file states from file-history-snapshot messages."""
        file_timeline = {}  # type: Dict[str, List[Dict[str, Any]]]

        for idx, msg in enumerate(messages):
            if msg.get("type") != "file-history-snapshot":
                continue

            snapshot = msg.get("snapshot", {})
            backups = snapshot.get("trackedFileBackups", {})

            for file_path, info in backups.items():
                backup_file = info.get("backupFileName")
                if not backup_file:
                    continue
                file_timeline.setdefault(file_path, []).append(
                    {
                        "backup_file": backup_file,
                        "time": info.get("backupTime"),
                        "idx": idx,
                    }
                )

        return file_timeline

    @staticmethod
    def _find_state_before(
        timeline: Dict[str, List[Dict[str, Any]]],
        file_path: str,
        current_idx: int,
    ) -> Optional[Dict[str, Any]]:
        """Find the most recent file state before the given message index."""
        states = timeline.get(file_path, [])

        if not states:
            for key in timeline:
                if file_path.endswith("/" + key) or file_path.endswith(key):
                    states = timeline[key]
                    break

        before = [state for state in states if state["idx"] < current_idx]
        return max(before, key=lambda state: state["idx"]) if before else None

    def _enrich_tool_uses_with_line_numbers(
        self,
        messages: List[Dict[str, Any]],
        session_id: str = "",
    ) -> List[Dict[str, Any]]:
        """Add startLine to Edit tool uses based on file history."""
        file_timeline = self._build_file_timeline(messages)

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

                state = self._find_state_before(file_timeline, file_path, idx)
                if not state:
                    continue

                backup_file = state.get("backup_file")
                if not backup_file:
                    continue

                backup_path = self.root / "file-history" / session_id / backup_file

                try:
                    content = backup_path.read_text(encoding="utf-8")
                    start_line = self._find_string_line(content, old_string)
                    if start_line is not None:
                        block["startLine"] = start_line
                except (FileNotFoundError, OSError):
                    pass

        return messages

    def _reconstruct_conversation(
        self,
        messages: List[Dict[str, Any]],
        session_id: str = "",
    ) -> List[Dict[str, Any]]:
        """Reconstruct a conversation thread from raw JSONL messages."""
        messages = self._enrich_tool_uses_with_line_numbers(messages, session_id)
        conversation = []  # type: List[Dict[str, Any]]
        assistant_buffer = None  # type: Optional[Dict[str, Any]]

        for msg in messages:
            msg_type = msg.get("type")

            if msg_type == "user":
                content = msg.get("message", {}).get("content", "")
                if isinstance(content, list):
                    has_tool_result = any(
                        isinstance(c, dict) and c.get("type") == "tool_result"
                        for c in content
                    )
                    if has_tool_result:
                        if assistant_buffer is not None:
                            tool_results = []
                            for c in content:
                                if isinstance(c, dict) and c.get("type") == "tool_result":
                                    tool_results.append(
                                        {
                                            "tool_use_id": c.get("tool_use_id", ""),
                                            "content": c.get("content", ""),
                                            "is_error": c.get("is_error", False),
                                        }
                                    )
                            assistant_buffer["tool_results"] = tool_results

                        raw_result = msg.get("toolUseResult")
                        if raw_result and isinstance(raw_result, dict):
                            structured_patch = raw_result.get("structuredPatch")
                            file_path = raw_result.get("filePath", "")
                            if structured_patch and assistant_buffer is not None:
                                for tool_use in assistant_buffer.get("tool_uses", []):
                                    if tool_use.get("name") == "Edit":
                                        tool_input = tool_use.get("input", {})
                                        if tool_input.get("file_path") == file_path:
                                            tool_use["structuredPatch"] = structured_patch
                                            break
                        continue

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
                                pass
                        elif isinstance(c, str):
                            parts.append(c)
                    text = "\n".join(parts)

                conversation.append(
                    {
                        "role": "user",
                        "content": text,
                        "timestamp": msg.get("timestamp", ""),
                        "uuid": msg.get("uuid", ""),
                    }
                )

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
                        tool_use = {
                            "id": block.get("id", ""),
                            "name": block.get("name", ""),
                            "input": block.get("input", {}),
                        }
                        if "startLine" in block:
                            tool_use["startLine"] = block["startLine"]
                        tool_uses.append(tool_use)

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

    def _build_session_project_map(self) -> Dict[str, str]:
        """Build a mapping from session_id to project_id by scanning project directories."""
        projects_dir = self.root / "projects"
        mapping = {}  # type: Dict[str, str]
        if not projects_dir.exists():
            return mapping
        for project_dir in projects_dir.iterdir():
            if not project_dir.is_dir():
                continue
            for session_file in project_dir.glob("*.jsonl"):
                mapping[session_file.stem] = project_dir.name
        return mapping

    def _get_cached_dashboard_stats(self, range_str: str) -> Optional[Dict[str, Any]]:
        """Return cached stats if fresh, else None."""
        entry = self._dashboard_cache.get(range_str)
        if entry and (_time.time() - entry["ts"]) < self._CACHE_TTL:
            return entry["data"]
        return None

    def _set_dashboard_cache(self, range_str: str, data: Dict[str, Any]) -> None:
        self._dashboard_cache[range_str] = {"data": data, "ts": _time.time()}

    def get_stats(self) -> Dict[str, Any]:
        """Get overview statistics."""
        history = self._read_jsonl(self.root / "history.jsonl")
        history_count = len(history)

        plans_dir = self.root / "plans"
        plan_files = list(plans_dir.glob("*.md")) if plans_dir.exists() else []

        projects_dir = self.root / "projects"
        project_dirs = []
        session_count = 0
        if projects_dir.exists():
            for d in projects_dir.iterdir():
                if d.is_dir():
                    project_dirs.append(d.name)
                    session_count += len(list(d.glob("*.jsonl")))

        now_ms = datetime.now().timestamp() * 1000
        day_ago = now_ms - 86400000
        recent_commands = sum(1 for h in history if h.get("timestamp", 0) > day_ago)

        return {
            "total_commands": history_count,
            "total_plans": len(plan_files),
            "total_projects": len(project_dirs),
            "total_sessions": session_count,
            "recent_commands_24h": recent_commands,
        }

    def get_dashboard_stats(self, range_str: str) -> Dict[str, Any]:
        """Get comprehensive dashboard statistics."""
        cached = self._get_cached_dashboard_stats(range_str)
        if cached:
            return cached

        now_ms = datetime.now().timestamp() * 1000
        if range_str == "7d":
            range_ms = 7 * 86400000
        elif range_str == "30d":
            range_ms = 30 * 86400000
        else:
            range_ms = None

        cutoff_ms = (now_ms - range_ms) if range_ms else 0
        prev_cutoff_ms = (cutoff_ms - range_ms) if range_ms else 0

        history = self._read_jsonl(self.root / "history.jsonl")
        history_in_range = [h for h in history if h.get("timestamp", 0) > cutoff_ms]
        history_in_prev = (
            [h for h in history if prev_cutoff_ms < h.get("timestamp", 0) <= cutoff_ms]
            if range_ms
            else []
        )

        daily_commands = defaultdict(int)
        hourly_dist = [0] * 24
        for h in history_in_range:
            ts = h.get("timestamp", 0)
            if ts:
                dt = datetime.fromtimestamp(ts / 1000)
                day_str = dt.strftime("%Y-%m-%d")
                daily_commands[day_str] += 1
                hourly_dist[dt.hour] += 1

        projects_dir = self.root / "projects"
        project_dirs = []
        session_files_all = []
        if projects_dir.exists():
            for d in projects_dir.iterdir():
                if d.is_dir():
                    project_dirs.append(d)
                    for sf in d.glob("*.jsonl"):
                        session_files_all.append((d, sf))

        daily_sessions = defaultdict(int)
        project_session_counts = defaultdict(lambda: {"count": 0, "name": "", "id": ""})
        session_files_in_range = []

        for project_dir, sf in session_files_all:
            mtime = sf.stat().st_mtime
            mtime_ms = mtime * 1000
            if mtime_ms > cutoff_ms:
                day_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
                daily_sessions[day_str] += 1
                session_files_in_range.append((project_dir, sf))

            pid = project_dir.name
            project_session_counts[pid]["count"] += 1
            project_session_counts[pid]["id"] = pid

        for project_dir in project_dirs:
            pid = project_dir.name
            if pid in project_session_counts and not project_session_counts[pid]["name"]:
                for sf in project_dir.glob("*.jsonl"):
                    msgs = self._read_jsonl(sf, limit=3)
                    for m in msgs:
                        cwd = m.get("cwd", "")
                        if cwd:
                            project_session_counts[pid]["name"] = cwd.rstrip("/").split("/")[-1]
                            break
                    break
                if not project_session_counts[pid]["name"]:
                    project_session_counts[pid]["name"] = pid

        top_projects = sorted(
            project_session_counts.values(),
            key=lambda item: item["count"],
            reverse=True,
        )[:5]
        top_projects_out = [
            {"project_id": p["id"], "project_name": p["name"], "session_count": p["count"]}
            for p in top_projects
        ]

        message_types = defaultdict(int)
        total_input_tokens = 0
        total_output_tokens = 0
        session_durations = {
            "under_5min": 0,
            "5_to_15min": 0,
            "15_to_30min": 0,
            "30_to_60min": 0,
            "over_60min": 0,
        }
        daily_tokens = defaultdict(int)

        files_to_scan = (
            session_files_in_range if len(session_files_in_range) <= 100 else session_files_in_range[:100]
        )

        for project_dir, sf in files_to_scan:
            msgs = self._read_jsonl(sf)
            timestamps = []
            for m in msgs:
                msg_type = m.get("type", "")
                if msg_type in ("user", "assistant"):
                    message_types[msg_type] += 1
                    ts = m.get("timestamp")
                    if ts:
                        if isinstance(ts, str):
                            try:
                                ts = datetime.fromisoformat(ts).timestamp() * 1000
                            except (ValueError, TypeError):
                                ts = None
                        if ts:
                            timestamps.append(ts)

                if msg_type == "assistant":
                    content = m.get("message", {}).get("content", [])
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict):
                                bt = block.get("type", "")
                                if bt == "tool_use":
                                    message_types["tool_use"] += 1

                    usage = m.get("message", {}).get("usage", {})
                    inp = usage.get("input_tokens", 0)
                    out = usage.get("output_tokens", 0)
                    total_input_tokens += inp
                    total_output_tokens += out

                    msg_ts = m.get("timestamp")
                    if msg_ts and (inp or out):
                        dt = None
                        if isinstance(msg_ts, (int, float)):
                            dt = datetime.fromtimestamp(msg_ts / 1000 if msg_ts > 1e12 else msg_ts)
                        elif isinstance(msg_ts, str):
                            try:
                                dt = datetime.fromisoformat(msg_ts)
                            except (ValueError, TypeError):
                                dt = None
                        if dt:
                            daily_tokens[dt.strftime("%Y-%m-%d")] += inp + out

                if msg_type == "user":
                    content = m.get("message", {}).get("content", [])
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "tool_result":
                                message_types["tool_result"] += 1

            if len(timestamps) >= 2:
                duration_min = (max(timestamps) - min(timestamps)) / 60000
                if duration_min < 5:
                    session_durations["under_5min"] += 1
                elif duration_min < 15:
                    session_durations["5_to_15min"] += 1
                elif duration_min < 30:
                    session_durations["15_to_30min"] += 1
                elif duration_min < 60:
                    session_durations["30_to_60min"] += 1
                else:
                    session_durations["over_60min"] += 1

        all_days = sorted(set(list(daily_commands.keys()) + list(daily_sessions.keys()) + list(daily_tokens.keys())))
        daily_series = [
            {
                "date": day,
                "commands": daily_commands.get(day, 0),
                "sessions": daily_sessions.get(day, 0),
                "tokens": daily_tokens.get(day, 0),
            }
            for day in all_days
        ]

        total_commands = len(history)
        total_sessions = len(session_files_all)
        total_projects = len(project_dirs)

        prev_commands = len(history_in_prev) if range_ms else 0
        curr_commands = len(history_in_range)
        commands_pct = round(((curr_commands - prev_commands) / prev_commands * 100), 1) if prev_commands > 0 else 0

        prev_session_count = 0
        curr_session_count = 0
        for _, sf in session_files_all:
            mtime_ms = sf.stat().st_mtime * 1000
            if mtime_ms > cutoff_ms:
                curr_session_count += 1
            elif range_ms and mtime_ms > prev_cutoff_ms:
                prev_session_count += 1
        sessions_pct = (
            round(((curr_session_count - prev_session_count) / prev_session_count * 100), 1)
            if prev_session_count > 0
            else 0
        )

        projects_new = 0
        for d in project_dirs:
            try:
                if d.stat().st_ctime * 1000 > cutoff_ms:
                    projects_new += 1
            except OSError:
                pass

        data = {
            "summary": {
                "total_commands": total_commands,
                "total_sessions": total_sessions,
                "total_projects": total_projects,
                "total_tokens": {
                    "input": total_input_tokens,
                    "output": total_output_tokens,
                },
            },
            "changes": {
                "commands_pct": commands_pct,
                "sessions_pct": sessions_pct,
                "projects_new": projects_new,
                "tokens_pct": 0,
            },
            "daily_series": daily_series,
            "message_types": dict(message_types),
            "top_projects": top_projects_out,
            "hourly_distribution": hourly_dist,
            "session_durations": session_durations,
        }

        self._set_dashboard_cache(range_str, data)
        return data

    def get_recent_sessions(self, limit: int) -> List[Dict[str, Any]]:
        """Get most recent sessions across all projects."""
        projects_dir = self.root / "projects"
        if not projects_dir.exists():
            return []

        all_sessions = []
        for project_dir in projects_dir.iterdir():
            if not project_dir.is_dir():
                continue

            project_path = project_dir.name
            for sf in project_dir.glob("*.jsonl"):
                msgs = self._read_jsonl(sf, limit=5)
                for m in msgs:
                    cwd = m.get("cwd", "")
                    if cwd:
                        project_path = cwd
                        break
                break

            for session_file in project_dir.glob("*.jsonl"):
                messages = self._read_jsonl(session_file, limit=10)
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
                all_sessions.append(
                    {
                        "session_id": session_file.stem,
                        "project_id": project_dir.name,
                        "project_path": project_path,
                        "preview": preview,
                        "message_count": len(self._read_jsonl(session_file)),
                        "timestamp": stat.st_mtime,
                        "size": stat.st_size,
                    }
                )

        all_sessions.sort(key=lambda item: item["timestamp"], reverse=True)
        return all_sessions[:limit]

    def get_history(
        self,
        page: int,
        limit: int,
        search: Optional[str],
        project: Optional[str],
    ) -> Dict[str, Any]:
        """Get command history with pagination and filtering."""
        history = self._read_jsonl(self.root / "history.jsonl")
        history.reverse()

        if search:
            search_lower = search.lower()
            history = [h for h in history if search_lower in h.get("display", "").lower()]
        if project:
            history = [h for h in history if project in h.get("project", "")]

        total = len(history)
        start = (page - 1) * limit
        items = history[start : start + limit]

        session_map = self._build_session_project_map()
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

    def get_plans(self) -> List[Dict[str, Any]]:
        """List all plans."""
        plans_dir = self.root / "plans"
        if not plans_dir.exists():
            return []

        plans = []
        for f in sorted(plans_dir.glob("*.md")):
            stat = f.stat()
            plans.append(
                {
                    "name": f.stem,
                    "filename": f.name,
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                }
            )
        return plans

    def get_plan(self, name: str) -> Dict[str, Any]:
        """Get a specific plan's content."""
        plan_path = self.root / "plans" / ("%s.md" % name)
        if not plan_path.exists():
            raise FileNotFoundError("Plan not found")
        return {
            "name": name,
            "content": plan_path.read_text(encoding="utf-8"),
        }

    def list_projects(self) -> List[Dict[str, Any]]:
        """List all projects."""
        projects_dir = self.root / "projects"
        if not projects_dir.exists():
            return []

        projects = []
        for d in sorted(projects_dir.iterdir()):
            if not d.is_dir():
                continue
            sessions_files = list(d.glob("*.jsonl"))

            actual_path = ""
            for sf in sessions_files[:1]:
                msgs = self._read_jsonl(sf, limit=5)
                for m in msgs:
                    cwd = m.get("cwd", "")
                    if cwd:
                        actual_path = cwd
                        break

            projects.append(
                {
                    "id": d.name,
                    "path": actual_path or d.name,
                    "display_name": d.name,
                    "session_count": len(sessions_files),
                    "size": sum(f.stat().st_size for f in sessions_files),
                }
            )
        return projects

    def get_project(self, project_id: str) -> Dict[str, Any]:
        """Get project details with sessions sorted by modification time."""
        project_dir = self.root / "projects" / project_id
        if not project_dir.exists():
            raise FileNotFoundError("Project not found")

        actual_path = ""
        sessions_files = list(project_dir.glob("*.jsonl"))
        for sf in sessions_files[:1]:
            msgs = self._read_jsonl(sf, limit=5)
            for m in msgs:
                cwd = m.get("cwd", "")
                if cwd:
                    actual_path = cwd
                    break

        sessions = []
        for f in project_dir.glob("*.jsonl"):
            messages = self._read_jsonl(f, limit=10)
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
            sessions.append(
                {
                    "id": f.stem,
                    "preview": preview,
                    "message_count": len(self._read_jsonl(f)),
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "created": stat.st_ctime,
                }
            )

        sessions.sort(key=lambda item: item["modified"], reverse=True)

        return {
            "id": project_id,
            "path": actual_path or project_id,
            "sessions": sessions,
        }

    def list_sessions(self, project_id: str) -> List[Dict[str, Any]]:
        """List sessions for a project."""
        project_dir = self.root / "projects" / project_id
        if not project_dir.exists():
            raise FileNotFoundError("Project not found")

        sessions = []
        for f in sorted(project_dir.glob("*.jsonl")):
            messages = self._read_jsonl(f)
            first_msg = next((m for m in messages if m.get("type") == "user"), None)
            last_msg = next(
                (m for m in reversed(messages) if m.get("type") in ("user", "assistant")),
                None,
            )

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

            msg_types = {}
            for m in messages:
                msg_type = m.get("type", "unknown")
                msg_types[msg_type] = msg_types.get(msg_type, 0) + 1

            sessions.append(
                {
                    "id": session_id,
                    "preview": preview,
                    "message_count": len(messages),
                    "message_types": msg_types,
                    "size": stat.st_size,
                    "created": stat.st_ctime,
                    "modified": stat.st_mtime,
                    "first_timestamp": first_msg.get("timestamp", "") if first_msg else "",
                    "last_timestamp": last_msg.get("timestamp", "") if last_msg else "",
                }
            )

        sessions.sort(key=lambda item: item["modified"], reverse=True)
        return sessions

    def get_session(self, project_id: str, session_id: str) -> Dict[str, Any]:
        """Get a session's conversation as a reconstructed thread."""
        session_path = self.root / "projects" / project_id / ("%s.jsonl" % session_id)
        if not session_path.exists():
            raise FileNotFoundError("Session not found")

        messages = self._read_jsonl(session_path)
        conversation = self._reconstruct_conversation(messages, session_id)

        subagents_dir = self.root / "projects" / project_id / session_id / "subagents"
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
                subagents.append(
                    {
                        "filename": f.name,
                        "type": meta.get("agentType", "Unknown"),
                        "description": meta.get("description", ""),
                        "size": f.stat().st_size,
                    }
                )

        return {
            "session_id": session_id,
            "project_id": project_id,
            "total_raw_messages": len(messages),
            "conversation": conversation,
            "subagents": subagents,
        }

    def get_subagent(self, project_id: str, session_id: str, agent_file: str) -> Dict[str, Any]:
        """Get a subagent's conversation."""
        agent_path = self.root / "projects" / project_id / session_id / "subagents" / agent_file
        if not agent_path.exists():
            raise FileNotFoundError("Subagent not found")

        messages = self._read_jsonl(agent_path)
        conversation = self._reconstruct_conversation(messages, session_id)
        return {
            "conversation": conversation,
            "total_raw_messages": len(messages),
        }
