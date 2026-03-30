# .deb 打包实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Claude History Viewer 打包为 `.deb`，用户安装后输入 `claude_history` 即可启动后端并打开浏览器。

**Architecture:** PyInstaller 将 `server.py` + 前端 dist 打成单文件可执行二进制，配合 shell wrapper 脚本和 DEBIAN 元数据组装成 .deb 包。GitHub Actions 在 Ubuntu 20.04 容器中构建以确保 glibc 兼容性。

**Tech Stack:** PyInstaller, dpkg-deb, GitHub Actions, bash

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `server.py` | 修改 | 添加 `get_base_path()`、`--port`、`--no-open` 参数支持 |
| `deb_package/DEBIAN/control` | 创建 | 包元数据和依赖声明 |
| `deb_package/DEBIAN/postinst` | 创建 | 安装后设置权限 |
| `deb_package/DEBIAN/prerm` | 创建 | 卸载前清理 |
| `deb_package/usr/bin/claude_history` | 创建 | Shell wrapper 入口脚本 |
| `build_deb.sh` | 创建 | 一键构建脚本 |
| `.github/workflows/build-deb.yml` | 创建 | CI 自动构建发布 |
| `.gitignore` | 修改 | 添加 PyInstaller 产物忽略 |

---

### Task 1: 修改 server.py 支持 PyInstaller 打包

**Files:**
- Modify: `server.py:1-7` (import 区)
- Modify: `server.py:664-683` (静态文件 + 启动区)

- [ ] **Step 1: 添加 `get_base_path()` 函数和 `sys` import**

在 `server.py` 文件头部 import 区（第 7 行 `from typing import Optional` 之后）添加 `import sys`。

在 `CLAUDE_DIR` 定义之后（第 14 行之后）添加 `get_base_path()` 函数：

```python
import sys


def get_base_path():
    """获取资源文件基础路径，兼容 PyInstaller 和普通运行"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent
```

- [ ] **Step 2: 修改静态文件路径使用 `get_base_path()`**

将第 668 行：

```python
dist_dir = Path(__file__).parent / "web" / "dist"
```

改为：

```python
dist_dir = get_base_path() / "web" / "dist"
```

- [ ] **Step 3: 修改启动块添加 `--port` 和 `--no-open` 参数**

将第 680-683 行的 `if __name__` 块替换为：

```python
if __name__ == "__main__":
    import argparse
    import webbrowser
    import threading

    parser = argparse.ArgumentParser(description="Claude History Viewer")
    parser.add_argument("--port", type=int, default=8787, help="服务端口 (默认: 8787)")
    parser.add_argument("--no-open", action="store_true", help="不自动打开浏览器")
    args = parser.parse_args()

    if not args.no_open:
        def open_browser():
            import time
            time.sleep(1.5)
            webbrowser.open(f"http://localhost:{args.port}")
        threading.Thread(target=open_browser, daemon=True).start()

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=args.port)
```

- [ ] **Step 4: 验证开发模式仍正常工作**

运行: `cd /home/weijiali/phi_ws/vibe_coding/claude_history && python server.py --no-open &`
等待 2 秒后运行: `curl -s http://localhost:8787/api/stats | head -c 100`
然后: `kill %1`

预期: 能正常返回 JSON 统计数据。

- [ ] **Step 5: Commit**

```bash
git add server.py
git commit -m "feat: server.py 添加 PyInstaller 兼容和 --port/--no-open 参数支持"
```

---

### Task 2: 创建 DEBIAN 控制文件

**Files:**
- Create: `deb_package/DEBIAN/control`
- Create: `deb_package/DEBIAN/postinst`
- Create: `deb_package/DEBIAN/prerm`

- [ ] **Step 1: 创建 `deb_package/DEBIAN/control`**

```bash
mkdir -p deb_package/DEBIAN
```

文件 `deb_package/DEBIAN/control` 内容：

```
Package: claude-history
Version: 0.0.3
Architecture: amd64
Maintainer: liweijia1243 <liweijia1243@users.noreply.github.com>
Depends: libgtk-3-0, libnotify4, libnss3, libxss1, xdg-utils
Section: web
Priority: optional
Description: Claude Code conversation history viewer
 A web-based viewer for Claude Code conversation history,
 projects, plans and command history.
```

注意：文件末尾必须有一个空行。

- [ ] **Step 2: 创建 `deb_package/DEBIAN/postinst`**

文件 `deb_package/DEBIAN/postinst` 内容：

```bash
#!/bin/bash
# 设置可执行权限
chmod +x /opt/claude-history/claude-history-server
chmod +x /usr/bin/claude_history
```

- [ ] **Step 3: 创建 `deb_package/DEBIAN/prerm`**

文件 `deb_package/DEBIAN/prerm` 内容：

```bash
#!/bin/bash
# 停止可能正在运行的实例
pkill -f "/opt/claude-history/claude-history-server" 2>/dev/null || true
```

- [ ] **Step 4: 设置脚本可执行权限**

```bash
chmod +x deb_package/DEBIAN/postinst deb_package/DEBIAN/prerm
```

- [ ] **Step 5: Commit**

```bash
git add deb_package/
git commit -m "feat: 新增 DEBIAN 控制文件用于 .deb 打包"
```

---

### Task 3: 创建 Shell Wrapper 入口脚本

**Files:**
- Create: `deb_package/usr/bin/claude_history`

- [ ] **Step 1: 创建 wrapper 脚本**

```bash
mkdir -p deb_package/usr/bin
```

文件 `deb_package/usr/bin/claude_history` 内容：

```bash
#!/bin/bash
# Claude History Viewer 启动脚本

SERVER="/opt/claude-history/claude-history-server"
PORT=8787

# 检查二进制是否存在
if [ ! -f "$SERVER" ]; then
    echo "错误: 未找到 $SERVER" >&2
    echo "请重新安装 claude-history" >&2
    exit 1
fi

# 检查端口是否被占用
if ss -tlnp 2>/dev/null | grep -q ":${PORT} "; then
    echo "错误: 端口 $PORT 已被占用" >&2
    echo "请先关闭占用该端口的程序，或使用 --port 指定其他端口" >&2
    exit 1
fi

# 清理函数
cleanup() {
    echo ""
    echo "正在停止 Claude History Viewer..."
    kill "$SERVER_PID" 2>/dev/null
    wait "$SERVER_PID" 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

# 启动后端（前台阻塞）
"$SERVER" --port "$PORT" &
SERVER_PID=$!

# 等待端口就绪
echo "正在启动 Claude History Viewer..."
for i in $(seq 1 30); do
    if curl -s -o /dev/null "http://localhost:${PORT}/api/stats" 2>/dev/null; then
        break
    fi
    sleep 0.5
done

# 打开浏览器
echo "正在打开浏览器: http://localhost:${PORT}"
xdg-open "http://localhost:${PORT}" 2>/dev/null &

echo "Claude History Viewer 运行中，按 Ctrl+C 停止"
wait "$SERVER_PID"
```

- [ ] **Step 2: 设置可执行权限**

```bash
chmod +x deb_package/usr/bin/claude_history
```

- [ ] **Step 3: Commit**

```bash
git add deb_package/usr/bin/claude_history
git commit -m "feat: 新增 claude_history 入口脚本"
```

---

### Task 4: 创建一键构建脚本 build_deb.sh

**Files:**
- Create: `build_deb.sh`

- [ ] **Step 1: 创建 `build_deb.sh`**

文件 `build_deb.sh` 内容：

```bash
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

VERSION="0.0.3"
DEB_NAME="claude-history_${VERSION}_amd64.deb"
BUILD_DIR="deb_package"

echo "=== Claude History Viewer .deb 构建 ==="
echo "版本: $VERSION"
echo ""

# Step 1: 构建前端
echo "[1/4] 构建前端..."
cd web
npm install --silent
npm run build
cd "$SCRIPT_DIR"

# Step 2: PyInstaller 打包
echo "[2/4] PyInstaller 打包后端..."
pip install pyinstaller --quiet
pyinstaller --onefile \
    --add-data "web/dist:web/dist" \
    --name claude-history-server \
    --clean \
    --noconfirm \
    server.py

# Step 3: 组装 deb 目录
echo "[3/4] 组装 .deb 包..."

# 创建安装目标目录结构
mkdir -p "$BUILD_DIR/opt/claude-history"
mkdir -p "$BUILD_DIR/usr/share/doc/claude-history"

# 复制二进制
cp dist/claude-history-server "$BUILD_DIR/opt/claude-history/"

# 复制文档
cp LICENSE "$BUILD_DIR/usr/share/doc/claude-history/"
if [ -f README.md ]; then
    cp README.md "$BUILD_DIR/usr/share/doc/claude-history/"
fi

# Step 4: 打包
echo "[4/4] 打包 $DEB_NAME ..."
fakeroot dpkg-deb -b "$BUILD_DIR" "$DEB_NAME"

# 清理构建临时文件（保留 deb_package 模板）
rm -rf "$BUILD_DIR/opt" "$BUILD_DIR/usr/share"

echo ""
echo "=== 构建完成 ==="
echo "产物: $DEB_NAME"
echo "大小: $(du -h "$DEB_NAME" | cut -f1)"
echo ""
echo "安装测试: sudo dpkg -i $DEB_NAME"
```

- [ ] **Step 2: 设置可执行权限**

```bash
chmod +x build_deb.sh
```

- [ ] **Step 3: 更新 .gitignore**

在 `.gitignore` 末尾追加：

```
# PyInstaller
dist/
build/
*.spec
```

- [ ] **Step 4: Commit**

```bash
git add build_deb.sh .gitignore
git commit -m "feat: 新增 build_deb.sh 一键构建脚本"
```

---

### Task 5: 创建 GitHub Actions 工作流

**Files:**
- Create: `.github/workflows/build-deb.yml`

- [ ] **Step 1: 创建工作流文件**

```bash
mkdir -p .github/workflows
```

文件 `.github/workflows/build-deb.yml` 内容：

```yaml
name: Build .deb Package

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: ubuntu-20.04
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install system dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y fakeroot dpkg-dev

      - name: Build .deb
        run: ./build_deb.sh

      - name: Upload to Release
        uses: softprops/action-gh-release@v2
        with:
          files: "*.deb"
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/build-deb.yml
git commit -m "feat: 新增 GitHub Actions 自动构建 .deb 发布工作流"
```

---

### Task 6: 本地构建测试

**Files:**
- 无新文件

- [ ] **Step 1: 运行构建脚本**

```bash
cd /home/weijiali/phi_ws/vibe_coding/claude_history && ./build_deb.sh
```

预期: 生成 `claude-history_0.0.3_amd64.deb` 文件，无报错。

- [ ] **Step 2: 检查 .deb 包内容**

```bash
dpkg-deb -c claude-history_0.0.3_amd64.deb
```

预期输出应包含：
```
/opt/claude-history/claude-history-server
/usr/bin/claude_history
/usr/share/doc/claude-history/
```

- [ ] **Step 3: 检查包元信息**

```bash
dpkg-deb -I claude-history_0.0.3_amd64.deb
```

预期: 显示 Package: claude-history, Version: 0.0.3 等信息。

- [ ] **Step 4: 安装测试**

```bash
sudo dpkg -i claude-history_0.0.3_amd64.deb
```

预期: 安装成功，无错误。

- [ ] **Step 5: 运行测试**

```bash
claude_history
```

预期: 浏览器自动打开 `http://localhost:8787`，页面正常显示。Ctrl+C 可停止。

- [ ] **Step 6: 卸载测试**

```bash
sudo dpkg -r claude-history
```

预期: 干净卸载，`/opt/claude-history/` 和 `/usr/bin/claude_history` 被移除。
