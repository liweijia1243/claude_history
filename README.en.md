<div align="center">

<img src="docs/screenshots/logo.png" alt="Claude History Viewer" width="200" />

# Claude History Viewer

**A visual history viewer for [Claude Code](https://claude.ai/code) sessions**

Reads data from the local `~/.claude/` directory and presents conversation history, implementation plans, and project sessions through a beautiful web interface.

[![GitHub Release](https://img.shields.io/github/v/release/liweijia1243/claude_history?include_prereleases)](https://github.com/liweijia1243/claude_history/releases/latest) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) [![Platform: Linux](https://img.shields.io/badge/Platform-Linux-orange.svg)](https://github.com/liweijia1243/claude_history/releases) [![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/) [![Vue 3](https://img.shields.io/badge/Vue-3-4FC08D.svg)](https://vuejs.org/)

**Languages**: [中文](README.md) | [English](README.en.md)

[Download](https://github.com/liweijia1243/claude_history/releases) · [Build from Source](#build-from-source) · [Features](#features) · [Report Bug](https://github.com/liweijia1243/claude_history/issues)

</div>

---

## Screenshots

<p align="center">
  <img src="docs/screenshots/dashboard.png" alt="Dashboard overview" width="49%" />
  <img src="docs/screenshots/conversation.png" alt="Conversation view" width="49%" />
</p>
<p align="center">
  <img src="docs/screenshots/plans.png" alt="Plans viewer" width="49%" />
  <img src="docs/screenshots/history.png" alt="Command history" width="49%" />
</p>
<p align="center">
  <img src="docs/screenshots/subagents.png" alt="Sub-agent dialog popup" width="49%" />
</p>

---

## Features

### Core Features

| Feature | Description |
|---------|-------------|
| **Dashboard** | Overview — command count, plan count, project count, 24h activity heatmap |
| **History** | Searchable command history with project filtering, click to jump to the corresponding session |
| **Plans** | Markdown plan file rendering with multi-plan browsing |
| **Projects** | Browse all sessions by project, automatically maps directory names to actual paths |
| **Conversation** | Chat bubble UI — collapsible thinking blocks, expandable tool call panels, sub-agent dialogs, code diff view |

### Conversation Highlights

| Feature | Description |
|---------|-------------|
| Thinking Block | Collapsible Claude thinking process display |
| Tool Call Panel | Expandable tool call details (file read/write, search, Bash, etc.) |
| Code Diff | File modification diff view with syntax highlighting |
| Sub-agent Dialog | Click Agent tool to open sub-agent conversation popup |
| Code Highlight | Multi-language code block syntax highlighting (highlight.js) |
| Markdown Rendering | Real-time Markdown rendering in assistant responses |

### Highlighted Features

**Search & Jump** — **Double-click** any search result in History or Projects to automatically navigate to the corresponding session and scroll to the exact message position.

**Show Thinkings / Show Tools / Show Agents** — Three toggle switches at the top of the conversation page let you show or hide thinking processes, tool calls, and Agent calls on demand — review conversations at the granularity you need.

**Sub-agent Dialog** — When you encounter an Agent tool call in a conversation, simply click it to open a popup showing the sub-agent's full conversation, without leaving the current page.

---

## Installation (Ubuntu 20.04+)

Download the latest `.deb` file from [GitHub Releases](https://github.com/liweijia1243/claude_history/releases/latest):

```bash
# Install
sudo dpkg -i claude-history_*.deb
sudo apt-get install -f  # Install missing dependencies

# Start
claude_history

# Stop — press Ctrl+C
```

The app automatically opens `http://localhost:8787` in your browser on startup.

### CLI Options

```
claude_history [options]

Options:
  --port <port>   Specify server port (default: 8787)
  --shared        Allow access from other devices on the LAN (default: localhost only)
  --help, -h      Show help message

Examples:
  claude_history                # Start on localhost:8787
  claude_history --port 9000    # Start on a custom port
  claude_history --shared       # Allow LAN access
```

> **Security Note:** By default, the server binds to `127.0.0.1` only — session history is accessible from the local machine only. Using `--shared` binds to `0.0.0.0`, making it accessible to all devices on the local network.

---

## Build from Source

**Prerequisites:** Python 3.8+, Node.js 18+

```bash
# Clone the repository
git clone https://github.com/liweijia1243/claude_history.git
cd claude_history

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd web && npm install && cd ..

# Start both frontend and backend (development mode)
./start.sh
```

- Frontend dev server: `http://localhost:5173`
- Backend API: `http://localhost:8787`

You can also run in production mode (with built frontend):

```bash
cd web && npm run build && cd ..
python server.py              # Localhost only
python server.py --shared     # Allow LAN access
python server.py --port 9000  # Custom port
python server.py --no-open    # Don't auto-open browser
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | ![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white) Python 3.8+ |
| Frontend | ![Vue 3](https://img.shields.io/badge/Vue_3-4FC08D?logo=vue.js&logoColor=white) ![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-06B6D4?logo=tailwindcss&logoColor=white) |
| Build | ![Vite](https://img.shields.io/badge/Vite-646CFF?logo=vite&logoColor=white) npm |
| Syntax Highlighting | highlight.js |

---

## Architecture

```
server.py          # FastAPI backend, reads ~/.claude/ data directly, no database
web/               # Vue 3 + Tailwind CSS frontend
  src/
    views/         # Page components (Dashboard, History, Plans, Projects, Conversation)
    components/    # Shared components (CodeBlock, DiffBlock, ToolCallBlock, ThinkingBlock)
    composables/   # Composable functions
    utils/         # Utility functions
```

### Data Sources

| Path | Content |
|------|---------|
| `~/.claude/history.jsonl` | All user commands |
| `~/.claude/plans/*.md` | Implementation plans (Markdown) |
| `~/.claude/projects/<dir>/*.jsonl` | Full project session conversations |
| `~/.claude/projects/<dir>/<session>/subagents/` | Sub-agent conversations |

### Data Privacy

**100% local.** All data is read directly from the local `~/.claude/` directory. Nothing is uploaded to external servers. No API key required.

---

## Building .deb Package

```bash
./build_deb.sh
```

Push a version tag to trigger GitHub Actions automatic build and release:

```bash
git tag v0.0.4
git push origin v0.0.4
```

---

## License

[MIT](LICENSE)
