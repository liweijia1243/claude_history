# Codex Provider 历史可视化支持设计

## 背景

当前项目是 Claude Code 会话记录可视化查看器。后端在 `server.py` 中直接读取 `~/.claude` 下的数据，包括：

- `history.jsonl`：用户命令历史
- `plans/*.md`：实施计划
- `projects/<project>/*.jsonl`：项目会话
- `projects/<project>/<session>/subagents/`：子代理会话

这套结构与 Codex 的本地数据结构不同。当前 Codex 桌面和 CLI 的核心会话索引主要来自 `~/.codex/state_5.sqlite` 的 `threads` 表，每条 thread 通过 `rollout_path` 指向实际的 `sessions/YYYY/MM/DD/rollout-*.jsonl` 文件。用户命令历史还存在于 `~/.codex/history.jsonl`，部分调试日志存在于 `~/.codex/logs_2.sqlite`。

如果继续在现有 Claude 读取逻辑中增加 Codex 分支，后端会快速变成格式判断堆叠，前端也会被不同数据源的字段差异牵连。因此本次改造应引入 Provider 适配层，把 Claude 和 Codex 都转换为统一的前端消费模型。

## 目标

将项目从单一 Claude 历史查看器改造为支持 Claude 和 Codex 的 AI coding history viewer。

本次目标：

- 支持当前 Codex 桌面和 CLI 的完整会话可视化
- 读取 Codex `state_5.sqlite` 中的 threads，并通过 `rollout_path` 展示 conversation
- 展示 Codex 用户消息、助手消息、reasoning、tool call、tool output、shell 执行结果和 agent message
- 保留现有 Claude 功能和旧 API 兼容性
- 前端尽量消费统一 conversation 模型，避免页面按 provider 分叉
- 为后续支持其他 AI coding 工具预留扩展边界

## 非目标

以下内容不在本次第一阶段范围内：

- 跨 Claude 和 Codex 的全局聚合 Dashboard
- 把 Codex 数据转换或写回为 Claude 格式
- 编辑、删除或归档 Codex 原始历史数据
- 支持远古 Codex schema 或未来未知 schema 的完整兼容
- 对 `logs_2.sqlite` 做完整日志浏览器
- 对 encrypted reasoning 做解密或恢复
- 重写现有 UI 风格

## 设计原则

1. **读取层与展示层解耦**
   不让前端直接感知 Claude JSONL 和 Codex rollout 的原始结构。后端 provider 负责归一化。

2. **保留现有行为**
   旧的 `/api/projects`、`/api/history` 等接口继续默认指向 Claude，避免破坏已有链接和使用习惯。

3. **Codex 一等支持**
   Codex 不作为 Claude 格式的模拟数据处理，而是由独立 provider 使用 Codex 自己的索引、thread、rollout 语义。

4. **统一模型允许 provider metadata**
   公共字段覆盖通用渲染需求，差异化信息放入 `metadata`，避免为了某个 provider 污染公共模型。

## 后端架构

后端从当前单文件结构逐步拆出 provider 模块：

```text
server.py
providers/
  __init__.py
  base.py
  models.py
  claude.py
  codex.py
```

### Provider 接口

`providers/base.py` 定义统一接口：

```python
class HistoryProvider:
    id: str
    name: str

    def available(self) -> bool: ...
    def get_stats(self) -> dict: ...
    def get_dashboard_stats(self, range: str) -> dict: ...
    def get_history(self, page: int, limit: int, search: str | None, project: str | None) -> dict: ...
    def list_projects(self) -> list[dict]: ...
    def get_project(self, project_id: str) -> dict: ...
    def list_sessions(self, project_id: str) -> list[dict]: ...
    def get_session(self, project_id: str, session_id: str) -> dict: ...
    def get_subagent(self, project_id: str, session_id: str, agent_file: str) -> dict: ...
```

Claude provider 可以完整实现 subagent。Codex provider 第一阶段可以让 `get_subagent()` 返回 404 或空结果，因为当前确认到的本地 Codex 数据使用 `thread_spawn_edges` 表表达 thread 间关系，但样本中没有实际 spawn edge。

### Provider 注册

`providers/__init__.py` 暴露 registry：

```python
PROVIDERS = {
    "claude": ClaudeProvider(),
    "codex": CodexProvider(),
}
```

`server.py` 中通过 `get_provider(source)` 统一取 provider。未知 source 返回 404。

## 统一数据模型

`providers/models.py` 定义 provider 输出的统一结构。第一阶段可使用普通 dict，后续再按需要引入 Pydantic 模型。

### Conversation Message

```json
{
  "role": "user | assistant | event",
  "content": "string",
  "thinking": "string",
  "tool_uses": [],
  "tool_results": [],
  "model": "string",
  "usage": {},
  "timestamp": "string | number",
  "uuid": "string",
  "metadata": {}
}
```

### Tool Use

```json
{
  "id": "string",
  "name": "string",
  "input": {},
  "metadata": {}
}
```

### Tool Result

```json
{
  "tool_use_id": "string",
  "content": "string",
  "is_error": false,
  "metadata": {}
}
```

Codex shell 执行结果可在 metadata 中保留：

```json
{
  "exit_code": 0,
  "cwd": "/path",
  "stdout": "...",
  "stderr": "...",
  "duration": {"secs": 1, "nanos": 0},
  "status": "completed"
}
```

## Claude Provider

Claude provider 承接现有 `server.py` 中的 Claude 逻辑：

- `read_jsonl()`
- `reconstruct_conversation()`
- `enrich_tool_uses_with_line_numbers()`
- `build_session_project_map()`
- stats、history、plans、projects、sessions、subagents 相关逻辑

迁移后应保持当前返回字段基本不变，并补齐统一字段：

- message 增加 `metadata`
- tool use 增加 `metadata`
- tool result 增加 `metadata`

旧 API 兼容层仍使用 Claude provider，所以迁移完成后现有前端不应出现行为变化。

## Codex Provider

### 数据来源

Codex provider 默认读取：

- `~/.codex/state_5.sqlite`
- `~/.codex/history.jsonl`
- `threads.rollout_path` 指向的 rollout JSONL

`~/.Codex` 可以作为大小写兼容候选路径，但优先使用 `~/.codex`。如果两个路径存在且指向同一数据，不重复展示。

### Thread 索引

Codex sessions 以 `threads` 表为准。关键字段：

- `id`：session id
- `rollout_path`：conversation JSONL 文件
- `cwd`：项目路径
- `title`：会话标题
- `first_user_message`：预览文本
- `created_at_ms` / `updated_at_ms`：排序和统计时间
- `model_provider`、`model`、`reasoning_effort`
- `source`：cli、vscode 等来源
- `tokens_used`
- `git_sha`、`git_branch`、`git_origin_url`

### Project 聚合

Codex 没有 Claude 那种 `projects/<encoded-path>` 目录。Codex provider 使用 `cwd` 聚合项目：

- `project_id = sha1(cwd).hexdigest()[:12]`
- `path = cwd`
- `display_name = cwd` 的最后一级目录名
- sessions 为该 cwd 下的 threads

provider 内部维护 `project_id -> cwd` 映射。请求 project detail 时通过映射查找 cwd；如果找不到，返回 404。

### History

Codex `history.jsonl` 字段形态为：

```json
{
  "session_id": "string",
  "ts": 1777012056882,
  "text": "string"
}
```

Codex provider 将其转换为与 Claude history 页面兼容的字段：

- `sessionId = session_id`
- `timestamp = ts`
- `display = text`
- `project_id` 通过 threads 表中的 session id 反查
- `project` 使用 thread.cwd

### Rollout Conversation 映射

Codex rollout JSONL 的顶层常见字段：

- `timestamp`
- `type`
- `payload`

常见 `payload.type` 映射如下。

#### `message`

当 payload 为：

```json
{
  "type": "message",
  "role": "user | assistant",
  "content": [{"type": "input_text | output_text", "text": "..."}]
}
```

映射为对应 role 的 conversation message。content 中多个文本块用换行合并。

#### `user_message`

映射为 user message：

- `content = payload.message`
- `metadata.images = payload.images`
- `metadata.local_images = payload.local_images`
- `metadata.text_elements = payload.text_elements`

#### `reasoning`

映射到最近的 assistant message 的 `thinking`。如果当前还没有 assistant message，则创建一个 assistant buffer。

规则：

- 有 `content` 时使用明文 content
- 有 `summary` 时合并 summary 文本
- 只有 `encrypted_content` 时不展示密文正文，`thinking` 使用短占位文案，并把 `encrypted: true` 放入 metadata

#### `function_call`

映射为 assistant message 上的 tool use：

- `id = call_id`
- `name = name`
- `input = json.loads(arguments)`，解析失败时使用 `{"arguments": raw_string}`
- `metadata.provider = "codex"`

#### `function_call_output`

映射为 tool result：

- `tool_use_id = call_id`
- `content = output`
- `is_error = false`

关联到最近包含相同 `call_id` 的 assistant message；找不到时创建 event message 保留原始结果。

#### `exec_command_end`

映射为更丰富的 shell 工具结果。

如果存在相同 `call_id` 的 function call，将其作为对应 tool result；否则创建一个 synthetic tool use：

- `id = call_id`
- `name = "exec_command"`
- `input.command = command`
- `input.cwd = cwd`

result content 优先使用：

1. `formatted_output`
2. `aggregated_output`
3. `stdout + stderr`

metadata 保留 `exit_code`、`duration`、`status`、`stdout`、`stderr`、`parsed_cmd`。

#### `agent_message`

映射为 assistant message 或 event message：

- 如果 `phase` 表示 agent 正常输出，role 使用 `assistant`
- 其他阶段可使用 `event`
- `metadata.phase = phase`

#### `token_count`

不默认渲染为聊天气泡。放入 session metadata 或最近 message metadata，用于后续 Dashboard 或 rate limit 展示。

#### `turn_context` 和 `session_meta`

不渲染成聊天气泡。作为 session metadata 返回：

- cwd
- model
- effort
- sandbox_policy
- approval_policy
- current_date
- timezone
- git
- source
- dynamic_tools

### Conversation 重建规则

Codex rollout 是事件流，不完全等同 Claude 的 user/assistant/tool_result 顺序。重建策略：

1. 顺序读取 rollout JSONL
2. 维护 `current_assistant` buffer
3. 遇到 user message 前，先 flush assistant buffer
4. assistant 文本、reasoning、function_call 都合并到当前 assistant buffer
5. function output 根据 `call_id` 回填到对应 tool use 所在 assistant message
6. 无法关联的事件保留为 `event` message，避免数据丢失

## API 设计

新增 source 维度：

```text
GET /api/sources
GET /api/{source}/stats
GET /api/{source}/dashboard-stats
GET /api/{source}/history
GET /api/{source}/projects
GET /api/{source}/projects/{project_id}
GET /api/{source}/projects/{project_id}/sessions
GET /api/{source}/projects/{project_id}/sessions/{session_id}
GET /api/{source}/projects/{project_id}/sessions/{session_id}/subagents/{agent_file}
```

`/api/sources` 返回：

```json
[
  {"id": "claude", "name": "Claude", "available": true},
  {"id": "codex", "name": "Codex", "available": true}
]
```

旧 API 保持兼容：

```text
GET /api/stats                                  -> /api/claude/stats
GET /api/dashboard-stats                       -> /api/claude/dashboard-stats
GET /api/history                               -> /api/claude/history
GET /api/projects                              -> /api/claude/projects
GET /api/projects/{project_id}                 -> /api/claude/projects/{project_id}
GET /api/projects/{project_id}/sessions        -> /api/claude/projects/{project_id}/sessions
GET /api/projects/{project_id}/sessions/{id}   -> /api/claude/projects/{project_id}/sessions/{id}
```

Plans 第一阶段继续只来自 Claude provider，因为 Codex 当前没有等价的 `plans/*.md` 数据源。

## 前端设计

### 路由

新增带 source 的路由：

```text
/sources/:source
/sources/:source/history
/sources/:source/projects
/sources/:source/projects/:projectId
/sources/:source/projects/:projectId/sessions/:sessionId
```

旧路由保留并默认使用 Claude：

```text
/
/history
/projects
/projects/:projectId
/projects/:projectId/sessions/:sessionId
```

### Source 切换

在 `App.vue` 的导航区域增加 Claude / Codex 切换入口。切换规则：

- 当前在 source 路由内时，切换到另一个 source 的相同一级页面
- 当前在旧路由时，视为 Claude
- source 选择可以存入 localStorage，作为进入 `/` 时的默认 source

### 页面请求

`Dashboard.vue`、`HistoryView.vue`、`ProjectsView.vue`、`ProjectDetailView.vue`、`ConversationView.vue` 增加 source 解析：

- route params 有 source 时使用 params source
- 没有 source 时使用 `claude`

请求 URL 从 `/api/projects` 改为 `/api/${source}/projects`，旧路由仍可工作。

### Conversation 渲染

`ConversationView.vue` 继续消费统一 `conversation`。需要增加：

- session metadata 展示 Codex source/model/reasoning effort
- event message 的轻量渲染
- Codex encrypted reasoning 的占位展示

### Tool 展示

`ToolCallBlock.vue` 增加 Codex 工具识别：

- `exec_command`：按 shell 工具展示 command、cwd、exit code、duration、stdout/stderr
- `apply_patch`：按 patch/diff 展示
- `spawn_agent`、`wait_agent`、`close_agent`：归类为 agent 工具
- `web.run`、`image_gen`、MCP function call：使用通用 JSON 输入和文本结果展示
- unknown tool：保持当前 JSON fallback

为了降低耦合，工具展示不依赖 provider，而是按 tool name 和 metadata 判断。

## Dashboard 与统计

第一阶段 Dashboard 按当前 source 独立展示。

Codex stats：

- total_commands：`history.jsonl` 行数
- total_projects：按 threads.cwd 聚合数量
- total_sessions：threads 数量
- recent_commands_24h：history 中最近 24 小时命令数
- total_tokens：优先使用 `threads.tokens_used`

Codex dashboard-stats：

- daily commands：来自 `history.jsonl`
- daily sessions：来自 threads.created_at_ms 或 updated_at_ms
- top projects：按 cwd 下 thread 数
- message types：抽样扫描 rollout payload.type
- session durations：用 rollout 事件首尾 timestamp 或 threads created/updated 估算

Claude dashboard 逻辑保持不变。

## 错误处理

Codex provider 需要明确处理以下情况：

- `~/.codex/state_5.sqlite` 不存在：provider unavailable
- sqlite 打不开：返回 unavailable 并在 API 中给出清晰错误
- thread 的 rollout_path 缺失或文件不存在：session detail 返回 404 或带错误 metadata 的空 conversation
- rollout JSONL 某行解析失败：跳过该行并记录 parse error count
- function call arguments 不是合法 JSON：保留原始字符串
- call_id 无法关联：创建 event message 保留输出

前端应对 provider unavailable 给出空状态，而不是无限 loading。

## 测试策略

### 后端测试

增加 fixture：

- Claude JSONL fixture：验证迁移 provider 后旧 conversation 重建结果不变
- Codex SQLite fixture：包含 threads 表和最小字段，验证 projects/sessions 聚合
- Codex rollout fixture：覆盖 `message`、`user_message`、`reasoning`、`function_call`、`function_call_output`、`exec_command_end`、`agent_message`

关键断言：

- Codex project_id 稳定且可反查 cwd
- Codex session 按 updated_at_ms 倒序
- function_call 和 function_call_output 能按 call_id 关联
- exec_command_end 能生成 shell result 并保留 exit_code
- encrypted reasoning 不泄露原始 encrypted_content
- 旧 `/api/projects` 仍返回 Claude 数据

### 前端测试

重点覆盖：

- source 路由参数解析
- source 切换后请求正确 API
- ConversationView 能渲染 Claude 和 Codex conversation
- ToolCallBlock 能展示 Codex shell result
- unknown Codex tool 使用 JSON fallback

## 实施计划概览

1. 抽出 provider 接口和统一模型。
2. 将 Claude 读取逻辑迁移到 `ClaudeProvider`，保持旧 API 行为。
3. 实现 `CodexProvider` 的 source availability、threads 查询、project/session 聚合。
4. 实现 Codex rollout conversation 重建。
5. 增加 `/api/{source}/...` 路由和旧 API 兼容层。
6. 前端接入 source 路由和请求路径。
7. 增强 Codex tool/event 渲染。
8. 增加后端 fixture 测试和前端渲染测试。
9. 更新 README 中的数据源说明和启动说明。

## 验收标准

- 用户可以在 UI 中切换 Claude 和 Codex 数据源
- Codex Projects 页面按 cwd 展示项目
- Codex Project Detail 页面展示该 cwd 下的 threads
- Codex Conversation 页面能展示完整 rollout conversation
- Codex 工具调用和 shell 执行结果能展开查看
- Claude 现有 History、Projects、Conversation、Plans 功能不回退
- 旧 API 路由仍可使用
- 缺少 Codex 数据时 UI 显示 unavailable 或空状态，不影响 Claude 使用
