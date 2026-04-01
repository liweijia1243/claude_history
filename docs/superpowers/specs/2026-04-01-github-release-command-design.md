# /github_release Slash Command 设计

## Context

每次发版需要手动执行一系列重复操作：检查未提交代码、提交推送、更新版本号、打 tag、构建 deb、创建 GitHub Release 并撰写 release note。将这些步骤自动化为一个 Claude Code slash command。

## 方案

在项目 `.claude/commands/` 下创建 `github_release.md`，作为项目级自定义 slash command。

### 命令用法

```
/github_release 0.0.7
```

### 文件位置

`.claude/commands/github_release.md` — prompt 模板，使用 `$ARGUMENTS` 接收版本号。

### 执行流程

1. **解析版本号** — 从 `$ARGUMENTS` 提取版本号，校验格式（`x.y.z`）
2. **检查未提交代码** — `git status`，如有未提交变更：
   - `git diff --stat` 分析变更内容
   - 自动生成 commit message（描述变更类型和范围）
   - `git add` 相关文件 + `git commit`
3. **同步到 main 分支并推送** — 检查当前分支：
   - 若在 main 上：直接 `git push origin main`
   - 若在其他分支：`git checkout main`，`git cherry-pick` 原分支超出 main 的增量 commit，然后 `git push origin main`。后续所有发版操作均在 main 分支上进行，不切回原分支
4. **更新版本号** — 修改 `build_deb.sh` 第 7 行和 `deb_package/DEBIAN/control` 第 2 行
5. **提交版本变更** — `git commit -m "chore: 发布版本升至 v{version}"`
6. **打 tag + 推送** — `git tag v{version}` + `git push origin v{version}`
7. **本地构建 deb** — `bash build_deb.sh`
8. **生成 release note** — `git log prev_tag..HEAD --oneline` 分析变更，参考历史 release 风格生成结构化 note（## What's New + emoji 分节 + 安装说明）
9. **创建 GitHub Release** — `gh release create v{version} ./claude-history_{version}_amd64.deb --title "v{version}" --notes "..."`

### Release Note 格式

```
## What's New

### <emoji> <功能分类>
- 变更描述
- 变更描述

---

### 安装

\```bash
sudo dpkg -i claude-history_{version}_amd64.deb
sudo apt-get install -f
claude_history
\```

> 支持 Ubuntu 20.04+，启动后自动在浏览器中打开 http://localhost:8787
```

### 错误处理

- 版本号格式不正确时提示用户
- 有未提交代码时自动处理（步骤 2）
- git push 失败时停止并提示
- deb 构建失败时停止，不创建 release
- gh release 创建失败时停止并提示

### 版本号文件

仅修改以下两处，不同步 `web/package.json`（它与发版无关）：

| 文件 | 字段 |
|------|------|
| `build_deb.sh` 第 7 行 | `VERSION="x.y.z"` |
| `deb_package/DEBIAN/control` 第 2 行 | `Version: x.y.z` |

## 验证

- 运行 `/github_release 0.0.7`（或下一个实际版本号）
- 确认版本号文件已更新
- 确认 tag 已创建并推送
- 确认 deb 包已构建
- 确认 GitHub Release 已创建且包含 deb 包和 release note
