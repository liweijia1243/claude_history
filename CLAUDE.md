# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目简介

Claude Code 会话记录可视化查看器。读取 `~/.claude/` 下的数据，通过 Web 界面美观地展示对话历史、实施计划、项目会话等内容。

## 常用命令

```bash
# 同时启动前后端
./start.sh

# 仅后端（端口 8787）
python server.py

# 仅前端开发（端口 5173，自动代理 /api 到后端）
cd web && npm run dev

# 构建前端生产包
cd web && npm run build
```

## 架构

**FastAPI 后端**（`server.py`）直接读取 `~/.claude/` 数据，无数据库。**Vue 3 前端**（`web/src/`）消费 API。

### 后端关键逻辑

- `reconstruct_conversation()` — 将原始 JSONL 消息重建成有序的用户/助手对话轮次，把工具结果关联到对应的助手消息
- 项目目录名与实际路径的映射通过读取会话消息中的 `cwd` 字段实现，而非解码目录名

### 前端页面

- Dashboard — 统计概览
- History — 可搜索的命令历史
- Plans — Markdown 计划渲染
- Projects → Sessions → Conversation — 逐级浏览
- Conversation — 核心页面：聊天气泡 UI，含可折叠思维块、可展开工具调用面板、子代理弹窗

### 数据来源

| 路径 | 内容 |
|------|------|
| `~/.claude/history.jsonl` | 所有用户命令 |
| `~/.claude/plans/*.md` | 实施计划（Markdown） |
| `~/.claude/projects/<dir>/*.jsonl` | 项目会话的完整对话 |
| `~/.claude/projects/<dir>/<session>/subagents/` | 子代理对话 |
