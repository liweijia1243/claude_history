# Claude History Viewer

一个用于可视化查看 [Claude Code](https://claude.ai/code) 会话记录的 Web 工具。读取本机 `~/.claude/` 下的数据，通过美观的 Web 界面展示对话历史、实施计划、项目会话等内容。

## 功能

- **Dashboard** — 统计概览：命令数、计划数、项目数、24h 活跃度
- **History** — 可搜索的命令历史，支持按项目筛选
- **Plans** — Markdown 计划文件渲染查看
- **Projects** — 按项目浏览所有会话
- **Conversation** — 核心页面：聊天气泡 UI，含可折叠思维块、可展开工具调用面板、子代理弹窗、代码 Diff 视图

## 安装（Ubuntu 20.04+）

从 [GitHub Releases](https://github.com/liweijia1243/claude_history/releases) 下载最新的 `.deb` 文件：

```bash
# 安装
sudo dpkg -i claude-history_*.deb
sudo apt-get install -f  # 自动安装缺失依赖

# 启动
claude_history

# 停止
# 按 Ctrl+C 即可停止服务
```

启动后会自动在浏览器中打开 `http://localhost:8787`。

## 从源码运行

**依赖：** Python 3.8+, Node.js 18+

```bash
# 克隆仓库
git clone https://github.com/liweijia1243/claude_history.git
cd claude_history

# 安装 Python 依赖
pip install -r requirements.txt

# 安装前端依赖
cd web && npm install && cd ..

# 同时启动前后端（开发模式）
./start.sh
```

- 前端开发服务器：http://localhost:5173
- 后端 API：http://localhost:8787

也可以单独启动生产模式（前端已构建）：

```bash
cd web && npm run build && cd ..
python server.py
```

访问 http://localhost:8787 即可。

## 架构

```
server.py          # FastAPI 后端，直接读取 ~/.claude/ 数据，无数据库
web/               # Vue 3 + Tailwind CSS 前端
  src/
    views/         # 页面组件（Dashboard, History, Plans, Projects, Conversation）
    components/    # 公共组件（CodeBlock, DiffBlock, ToolCallBlock, ThinkingBlock）
    composables/   # 组合式函数
    utils/         # 工具函数
```

### 数据来源

| 路径 | 内容 |
|------|------|
| `~/.claude/history.jsonl` | 所有用户命令 |
| `~/.claude/plans/*.md` | 实施计划（Markdown） |
| `~/.claude/projects/<dir>/*.jsonl` | 项目会话的完整对话 |
| `~/.claude/projects/<dir>/<session>/subagents/` | 子代理对话 |

## 构建 .deb 包

```bash
./build_deb.sh
```

推送版本 tag 触发 GitHub Actions 自动构建发布：

```bash
git tag v0.0.4
git push origin v0.0.4
```

## License

MIT
