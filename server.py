"""Claude History Viewer - FastAPI Backend"""
from pathlib import Path
from typing import Optional
import sys

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from providers import get_provider, list_sources


def get_base_path():
    """获取资源文件基础路径，兼容 PyInstaller 和普通运行"""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent


app = FastAPI(title="Claude History Viewer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def provider_or_404(source: str):
    provider = get_provider(source)
    if provider is None or not provider.available():
        raise HTTPException(404, "Source not found/unavailable")
    return provider


def legacy_claude_provider_or_404():
    provider = get_provider("claude")
    if provider is None:
        raise HTTPException(404, "Source not found/unavailable")
    return provider


def _not_found_as_http404(callback):
    try:
        return callback()
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc))


# ── API Routes ───────────────────────────────────────────────────────────────

@app.get("/api/sources")
def get_sources():
    return list_sources()


@app.get("/api/stats")
def get_stats():
    """Get overview statistics."""
    return legacy_claude_provider_or_404().get_stats()


@app.get("/api/dashboard-stats")
def get_dashboard_stats(range: str = Query("30d", pattern="^(7d|30d|all)$")):
    """Get comprehensive dashboard statistics."""
    return legacy_claude_provider_or_404().get_dashboard_stats(range)


@app.get("/api/recent-sessions")
def get_recent_sessions(limit: int = Query(5, ge=1, le=20)):
    """Get most recent sessions across all projects."""
    return legacy_claude_provider_or_404().get_recent_sessions(limit)


@app.get("/api/history")
def get_history(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None),
    project: Optional[str] = Query(None),
):
    """Get command history with pagination and filtering."""
    return legacy_claude_provider_or_404().get_history(page, limit, search, project)


@app.get("/api/plans")
def get_plans():
    """List all plans."""
    return legacy_claude_provider_or_404().get_plans()


@app.get("/api/plans/{name}")
def get_plan(name: str):
    """Get a specific plan's content."""
    return _not_found_as_http404(lambda: legacy_claude_provider_or_404().get_plan(name))


@app.get("/api/projects")
def get_projects():
    """List all projects."""
    return legacy_claude_provider_or_404().list_projects()


@app.get("/api/projects/{project_id}")
def get_project_detail(project_id: str):
    """Get project details with sessions sorted by modification time."""
    return _not_found_as_http404(lambda: legacy_claude_provider_or_404().get_project(project_id))


@app.get("/api/projects/{project_id}/sessions")
def get_project_sessions(project_id: str):
    """List sessions for a project."""
    return _not_found_as_http404(lambda: legacy_claude_provider_or_404().list_sessions(project_id))


@app.get("/api/projects/{project_id}/sessions/{session_id}")
def get_session_conversation(project_id: str, session_id: str):
    """Get a session's conversation as a reconstructed thread."""
    return _not_found_as_http404(lambda: legacy_claude_provider_or_404().get_session(project_id, session_id))


@app.get("/api/projects/{project_id}/sessions/{session_id}/subagents/{agent_file}")
def get_subagent_conversation(project_id: str, session_id: str, agent_file: str):
    """Get a subagent's conversation."""
    return _not_found_as_http404(
        lambda: legacy_claude_provider_or_404().get_subagent(project_id, session_id, agent_file)
    )


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
    return _not_found_as_http404(lambda: provider_or_404(source).get_project(project_id))


@app.get("/api/{source}/projects/{project_id}/sessions")
def get_source_project_sessions(source: str, project_id: str):
    return _not_found_as_http404(lambda: provider_or_404(source).list_sessions(project_id))


@app.get("/api/{source}/projects/{project_id}/sessions/{session_id}")
def get_source_session_conversation(source: str, project_id: str, session_id: str):
    return _not_found_as_http404(lambda: provider_or_404(source).get_session(project_id, session_id))


@app.get("/api/{source}/projects/{project_id}/sessions/{session_id}/subagents/{agent_file}")
def get_source_subagent_conversation(source: str, project_id: str, session_id: str, agent_file: str):
    return _not_found_as_http404(
        lambda: provider_or_404(source).get_subagent(project_id, session_id, agent_file)
    )


# ── Serve Frontend ───────────────────────────────────────────────────────────

# In development, Vite serves the frontend on port 5173
# In production, serve the built files
dist_dir = get_base_path() / "web" / "dist"
if dist_dir.exists():
    app.mount("/assets", StaticFiles(directory=dist_dir / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = dist_dir / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(dist_dir / "index.html")


if __name__ == "__main__":
    import argparse
    import threading
    import webbrowser

    parser = argparse.ArgumentParser(description="Claude History Viewer")
    parser.add_argument("--port", type=int, default=8787, help="服务端口 (默认: 8787)")
    parser.add_argument("--no-open", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--shared", action="store_true", help="允许局域网访问 (默认仅本机访问)")
    args = parser.parse_args()

    host = "0.0.0.0" if args.shared else "127.0.0.1"

    if not args.no_open:
        def open_browser():
            import time

            time.sleep(1.5)
            webbrowser.open("http://localhost:%s" % args.port)

        threading.Thread(target=open_browser, daemon=True).start()

    import uvicorn

    uvicorn.run(app, host=host, port=args.port)
