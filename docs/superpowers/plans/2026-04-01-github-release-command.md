# /github_release Slash Command 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建 `/github_release` 项目级 slash command，一键完成版本号更新、提交、打 tag、构建 deb、发布 GitHub Release 的全流程。

**Architecture:** 在 `.claude/commands/github_release.md` 中编写 prompt 模板，使用 `$ARGUMENTS` 接收版本号，指导 Claude 按步骤执行发版操作。

**Tech Stack:** Claude Code custom command (`.claude/commands/*.md`)，git，gh CLI，bash

---

### Task 1: 创建命令目录和文件

**Files:**
- Create: `.claude/commands/github_release.md`

- [ ] **Step 1: 创建 `.claude/commands/` 目录**

```bash
mkdir -p .claude/commands
```

- [ ] **Step 2: 创建 `github_release.md`**

```markdown
---
description: "GitHub Release 发版命令。用法: /github_release <version>，如 /github_release 0.0.7"
---

# GitHub Release 发布流程

版本号: `$ARGUMENTS`

请按以下步骤执行发版流程。版本号为上面指定的值（从 `$ARGUMENTS` 获取）。

## 前置检查

1. 校验版本号格式（必须为 `x.y.z` 格式，如 `0.0.7`），不合法则停止并提示用户
2. 检查该版本 tag 是否已存在（`git tag -l "v{version}"`），已存在则停止并提示

## 步骤 1: 提交未暂存代码

运行 `git status` 检查是否有未提交变更：
- 如果有变更：运行 `git diff --stat` 和 `git diff` 分析变更内容，自动生成 commit message（使用中文，遵循项目 commit 规范），然后 `git add` 相关文件并 `git commit`
- 如果没有变更：跳过此步骤

## 步骤 2: 同步到 main 分支并推送

检查当前分支（`git branch --show-current`）：
- 如果在 main 上：直接 `git push origin main`
- 如果在其他分支上：
  1. 记录当前分支名
  2. `git checkout main`
  3. `git cherry-pick` 原分支超出 main 的增量 commit（用 `git log main..{原分支} --oneline` 找出增量 commit）
  4. `git push origin main`
  5. 后续所有操作在 main 分支上进行，不切回原分支

## 步骤 3: 更新版本号

修改以下两个文件中的版本号：

1. `build_deb.sh` 第 7 行：`VERSION="x.y.z"` → `VERSION="{version}"`
2. `deb_package/DEBIAN/control` 第 2 行：`Version: x.y.z` → `Version: {version}`

其中 `{version}` 替换为实际版本号。

## 步骤 4: 提交版本变更

```bash
git add build_deb.sh deb_package/DEBIAN/control
git commit -m "chore: 发布版本升至 v{version}"
```

## 步骤 5: 打 tag 并推送

```bash
git tag v{version}
git push origin main
git push origin v{version}
```

## 步骤 6: 本地构建 deb 包

```bash
bash build_deb.sh
```

如果构建失败，停止流程并提示用户。

## 步骤 7: 生成 Release Note

1. 用 `git describe --tags --abbrev=0 HEAD^` 找到上一个 tag
2. 用 `git log {上一个tag}..HEAD --oneline` 获取本次所有变更
3. 分析变更内容，按功能分类归纳
4. 生成结构化 release note，格式如下：

```
## What's New

### 🎯 <功能分类>
- 变更描述1
- 变更描述2

### 🐛 Bug 修复
- 修复描述

---

### 安装

sudo dpkg -i claude-history_{version}_amd64.deb
sudo apt-get install -f
claude_history

> 支持 Ubuntu 20.04+，启动后自动在浏览器中打开 http://localhost:8787
```

## 步骤 8: 创建 GitHub Release

使用生成的 release note 创建 release：

```bash
gh release create v{version} ./claude-history_{version}_amd64.deb --title "v{version}" --notes "{release_note}"
```

完成后输出 release URL。
```

- [ ] **Step 3: 提交**

```bash
git add .claude/commands/github_release.md
git commit -m "feat: 添加 /github_release 自定义 slash command"
```
