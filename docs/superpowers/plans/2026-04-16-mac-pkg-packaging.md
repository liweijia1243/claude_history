# Mac .pkg + Homebrew 打包实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Claude History Viewer 添加 Mac (.pkg) 打包支持，用户下载 .pkg 双击安装后输入 `claude_history` 即可使用，同时预留 Homebrew Formula 接口。

**Architecture:** 复用现有 deb 打包模式，新建 `build_pkg.sh` 构建脚本 + `pkg_package/` 模板目录 + `updater-mac` 更新脚本。用 macOS 原生 `pkgbuild` 命令生成 .pkg 安装包。wrapper 脚本适配 macOS 命令差异（`open` 替代 `xdg-open`，`lsof` 替代 `ss`）。统一发版命令同时产出 .deb 和 .pkg。

**Tech Stack:** PyInstaller (arm64), pkgbuild, bash, Python

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `build_pkg.sh` | 创建 | Mac 一键构建脚本（对称 build_deb.sh） |
| `pkg_package/scripts/preinstall` | 创建 | 安装前停掉旧版进程 |
| `pkg_package/scripts/postinstall` | 创建 | 安装后设置可执行权限 |
| `pkg_package/root/usr/local/bin/claude_history` | 创建 | Mac 版 wrapper 入口脚本 |
| `pkg_package/root/usr/local/claude-history/.gitkeep` | 创建 | 目录占位 |
| `updater-mac` | 创建 | Mac 版自动更新脚本 |
| `.gitignore` | 修改 | 添加 *.pkg 忽略规则 |
| `.claude/commands/github_release.md` | 修改 | 新增 .pkg 构建和上传逻辑 |

---

### Task 1: 创建 Mac wrapper 脚本

**Files:**
- Create: `pkg_package/root/usr/local/bin/claude_history`

- [ ] **Step 1: 创建目录并编写 wrapper 脚本**

```bash
mkdir -p pkg_package/root/usr/local/bin
mkdir -p pkg_package/root/usr/local/claude-history
```

文件 `pkg_package/root/usr/local/bin/claude_history` 内容：

```bash
#!/bin/bash
# Claude History Viewer 启动脚本 (macOS)

SERVER="/usr/local/claude-history/claude-history-server"
UPDATER="/usr/local/claude-history/updater-mac"
PORT=8787
SHARED=false

VERSION_FILE="/usr/local/claude-history/VERSION"

# --update 单独处理（需要 sudo）
if [ "$1" = "--update" ]; then
    if [ ! -f "$UPDATER" ]; then
        echo "错误: 未找到更新器 $UPDATER" >&2
        exit 1
    fi
    exec sudo "$UPDATER" --update
fi

# --version 单独处理
if [ "$1" = "--version" ] || [ "$1" = "-v" ]; then
    if [ -f "$VERSION_FILE" ]; then
        VERSION=$(cat "$VERSION_FILE")
        echo "Claude History Viewer v$VERSION"
    else
        echo "Claude History Viewer (版本未知)"
    fi
    exit 0
fi

# 解析参数
while [[ $# -gt 0 ]]; do
    case "$1" in
        --port)
            if [ -z "$2" ] || ! [[ "$2" =~ ^[0-9]+$ ]] || [ "$2" -lt 1 ] || [ "$2" -gt 65535 ]; then
                echo "错误: --port 需要一个 1-65535 之间的端口号" >&2
                exit 1
            fi
            PORT="$2"
            shift 2
            ;;
        --shared)
            SHARED=true
            shift
            ;;
        --help|-h)
            echo "Claude History Viewer - Claude Code 会话记录可视化查看器"
            echo ""
            echo "用法: claude_history [选项]"
            echo ""
            echo "选项:"
            echo "  --port <端口>  指定服务端口 (默认: 8787)"
            echo "  --shared       允许局域网内其他设备访问 (默认仅本机可访问)"
            echo "  --update       检查并安装最新版本"
            echo "  --version, -v  显示版本信息"
            echo "  --help, -h     显示此帮助信息"
            echo ""
            echo "示例:"
            echo "  claude_history              # 本机 8787 端口启动"
            echo "  claude_history --port 9000  # 指定端口启动"
            echo "  claude_history --shared     # 允许局域网访问"
            echo "  claude_history --update     # 更新到最新版本"
            echo ""
            echo "启动后自动在浏览器中打开，按 Ctrl+C 停止服务"
            exit 0
            ;;
        *)
            echo "未知选项: $1" >&2
            echo "使用 --help 查看帮助" >&2
            exit 1
            ;;
    esac
done

# 检查二进制是否存在
if [ ! -f "$SERVER" ]; then
    echo "错误: 未找到 $SERVER" >&2
    echo "请重新安装 claude-history" >&2
    exit 1
fi

# 后台静默检测更新（不等待，不阻塞）
if [ -f "$UPDATER" ]; then
    ("$UPDATER" --check 2>/dev/null | while read -r line; do
        if [[ "$line" == UPDATE_AVAILABLE:* ]]; then
            new_ver="${line#UPDATE_AVAILABLE:}"
            echo ""
            echo "  有新版本 $new_ver 可用，运行 claude_history --update 进行更新"
            echo ""
        fi
    done) &
fi

# 检查端口是否被占用（macOS: 使用 lsof）
if lsof -i :"$PORT" -t >/dev/null 2>&1; then
    echo "错误: 端口 $PORT 已被占用" >&2
    echo "请先关闭占用该端口的程序" >&2
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

# 启动后端
if [ "$SHARED" = true ]; then
    "$SERVER" --port "$PORT" --no-open --shared &
    ACCESS="http://$(ipconfig getifaddr en0 2>/dev/null || echo "localhost"):${PORT} 或 http://localhost:${PORT}"
else
    "$SERVER" --port "$PORT" --no-open &
    ACCESS="http://localhost:${PORT}"
fi
SERVER_PID=$!

# 等待端口就绪
echo "正在启动 Claude History Viewer..."
for i in $(seq 1 30); do
    if curl -s -o /dev/null "http://localhost:${PORT}/api/stats" 2>/dev/null; then
        break
    fi
    sleep 0.5
done

# 打开浏览器（macOS: 使用 open）
echo "正在打开浏览器: $ACCESS"
open "http://localhost:${PORT}" 2>/dev/null &

echo "Claude History Viewer 运行中: $ACCESS"
echo "按 Ctrl+C 停止"
wait "$SERVER_PID"
```

- [ ] **Step 2: 创建 .gitkeep 占位文件**

```bash
touch pkg_package/root/usr/local/claude-history/.gitkeep
```

- [ ] **Step 3: 设置可执行权限**

```bash
chmod +x pkg_package/root/usr/local/bin/claude_history
```

- [ ] **Step 4: Commit**

```bash
git add pkg_package/root/
git commit -m "feat: 新增 Mac 版 claude_history wrapper 脚本"
```

---

### Task 2: 创建 pkg 安装脚本 (preinstall / postinstall)

**Files:**
- Create: `pkg_package/scripts/preinstall`
- Create: `pkg_package/scripts/postinstall`

- [ ] **Step 1: 创建 scripts 目录**

```bash
mkdir -p pkg_package/scripts
```

- [ ] **Step 2: 创建 `pkg_package/scripts/preinstall`**

```bash
#!/bin/bash
# 安装前：停掉正在运行的旧版
pkill -f "/usr/local/claude-history/claude-history-server" 2>/dev/null || true
exit 0
```

- [ ] **Step 3: 创建 `pkg_package/scripts/postinstall`**

```bash
#!/bin/bash
# 设置可执行权限
chmod +x /usr/local/claude-history/claude-history-server
chmod +x /usr/local/bin/claude_history
chmod +x /usr/local/claude-history/updater-mac
exit 0
```

- [ ] **Step 4: 设置可执行权限**

```bash
chmod +x pkg_package/scripts/preinstall pkg_package/scripts/postinstall
```

- [ ] **Step 5: Commit**

```bash
git add pkg_package/scripts/
git commit -m "feat: 新增 .pkg 安装前后脚本 (preinstall/postinstall)"
```

---

### Task 3: 创建 Mac 版更新脚本 updater-mac

**Files:**
- Create: `updater-mac`

- [ ] **Step 1: 创建 `updater-mac`**

文件 `updater-mac` 内容（与 Linux `updater` 功能对齐）：

```python
#!/usr/bin/env python3
"""Claude History Viewer 自动更新器 (macOS)"""
import argparse
import os
import subprocess
import sys
import tempfile

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    import urllib.error
    import json
    HAS_REQUESTS = False

try:
    from packaging.version import parse as parse_version
except ImportError:
    def parse_version(v):
        return tuple(int(x) for x in v.split('.'))

GITHUB_REPO = "liweijia1243/claude_history"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
INSTALL_DIR = "/usr/local/claude-history"
VERSION_FILE = f"{INSTALL_DIR}/VERSION"


def get_current_version():
    try:
        with open(VERSION_FILE, 'r') as f:
            return f.read().strip()
    except (FileNotFoundError, IOError):
        return "0.0.0"


def get_latest_release():
    if HAS_REQUESTS:
        response = requests.get(GITHUB_API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
    else:
        req = urllib.request.Request(GITHUB_API_URL, headers={
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "claude-history-updater"
        })
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))

    version = data["tag_name"].lstrip("v")

    # 查找 .pkg 文件（macOS）
    pkg_url = None
    for asset in data.get("assets", []):
        if asset["name"].endswith(".pkg") and "arm64" in asset["name"]:
            pkg_url = asset["browser_download_url"]
            break

    return version, pkg_url


def download_file(url, dest):
    if HAS_REQUESTS:
        response = requests.get(url, timeout=60, stream=True)
        response.raise_for_status()
        with open(dest, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    else:
        urllib.request.urlretrieve(url, dest)


def cmd_check():
    try:
        current = get_current_version()
        latest, _ = get_latest_release()

        if parse_version(latest) > parse_version(current):
            print(f"UPDATE_AVAILABLE:v{latest}")
    except Exception:
        pass


def cmd_update():
    try:
        current = get_current_version()
        print(f"当前版本: {current}")
        print("正在检查更新...")

        latest, pkg_url = get_latest_release()

        if parse_version(latest) <= parse_version(current):
            print(f"已是最新版本: {current}")
            sys.exit(0)

        print(f"发现新版本: {latest}")

        if not pkg_url:
            print("错误: 未找到 .pkg 安装包", file=sys.stderr)
            sys.exit(1)

        print(f"正在下载: {pkg_url}")
        with tempfile.NamedTemporaryFile(suffix=".pkg", delete=False) as tmp:
            tmp_path = tmp.name

        download_file(pkg_url, tmp_path)
        print(f"下载完成: {tmp_path}")

        print("正在安装...")
        result = subprocess.run(
            ["sudo", "installer", "-pkg", tmp_path, "-target", "/"],
            capture_output=True,
            text=True
        )

        try:
            os.unlink(tmp_path)
        except OSError:
            pass

        if result.returncode != 0:
            print(f"安装失败: {result.stderr}", file=sys.stderr)
            sys.exit(1)

        print("")
        print("更新成功!")
        print("请重新运行 claude_history 启动新版本")
        sys.exit(0)

    except KeyError as e:
        print(f"解析错误: 缺少字段 {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        error_name = type(e).__name__
        if "RequestException" in error_name or "URLError" in error_name or "HTTPError" in error_name:
            print(f"网络错误: {e}", file=sys.stderr)
        else:
            print(f"更新失败: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Claude History 更新器 (macOS)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="静默检测是否有新版本")
    group.add_argument("--update", action="store_true", help="执行更新")

    args = parser.parse_args()

    if args.check:
        cmd_check()
    elif args.update:
        cmd_update()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 设置可执行权限**

```bash
chmod +x updater-mac
```

- [ ] **Step 3: Commit**

```bash
git add updater-mac
git commit -m "feat: 新增 Mac 版自动更新脚本 updater-mac"
```

---

### Task 4: 创建构建脚本 build_pkg.sh

**Files:**
- Create: `build_pkg.sh`
- Modify: `.gitignore`（添加 `*.pkg`）

- [ ] **Step 1: 创建 `build_pkg.sh`**

文件 `build_pkg.sh` 内容：

```bash
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

VERSION="0.1.1"
PKG_NAME="claude-history_${VERSION}_arm64.pkg"
PKG_ROOT="pkg_package/root"

echo "=== Claude History Viewer .pkg 构建 ==="
echo "版本: $VERSION"
echo ""

# Step 1: 构建前端
echo "[1/4] 构建前端..."
cd web
npm install --silent
npm run build
cd "$SCRIPT_DIR"

# Step 2: PyInstaller 打包 (arm64)
echo "[2/4] PyInstaller 打包后端 (arm64)..."
pip install pyinstaller --quiet
pyinstaller --onefile \
    --target-arch arm64 \
    --add-data "web/dist:web/dist" \
    --name claude-history-server \
    --clean \
    --noconfirm \
    server.py

# Step 3: 组装 pkg 目录
echo "[3/4] 组装 .pkg 包..."

# 创建安装目标目录结构
mkdir -p "$PKG_ROOT/usr/local/claude-history"
mkdir -p "$PKG_ROOT/usr/local/bin"

# 复制二进制
cp dist/claude-history-server "$PKG_ROOT/usr/local/claude-history/"

# 复制更新器
cp updater-mac "$PKG_ROOT/usr/local/claude-history/"
chmod +x "$PKG_ROOT/usr/local/claude-history/updater-mac"

# 生成版本文件
echo "$VERSION" > "$PKG_ROOT/usr/local/claude-history/VERSION"

# 复制 wrapper 脚本
cp pkg_package/root/usr/local/bin/claude_history "$PKG_ROOT/usr/local/bin/"

# Step 4: 打包
echo "[4/4] 打包 $PKG_NAME ..."
pkgbuild --root "$PKG_ROOT" \
    --identifier "com.claude-history.viewer" \
    --version "$VERSION" \
    --scripts "pkg_package/scripts" \
    --install-location "/" \
    "$PKG_NAME"

# 清理构建临时文件（保留 pkg_package 模板）
rm -rf "$PKG_ROOT/usr"

echo ""
echo "=== 构建完成 ==="
echo "产物: $PKG_NAME"
echo "大小: $(du -h "$PKG_NAME" | cut -f1)"
echo ""
echo "安装测试: sudo installer -pkg $PKG_NAME -target /"
```

- [ ] **Step 2: 设置可执行权限**

```bash
chmod +x build_pkg.sh
```

- [ ] **Step 3: 更新 .gitignore**

在 `.gitignore` 末尾添加：

```
*.pkg
```

- [ ] **Step 4: Commit**

```bash
git add build_pkg.sh .gitignore
git commit -m "feat: 新增 build_pkg.sh Mac 一键构建脚本"
```

---

### Task 5: 修改发版命令支持同时构建 .deb + .pkg

**Files:**
- Modify: `.claude/commands/github_release.md`

- [ ] **Step 1: 更新 `.claude/commands/github_release.md`**

替换整个文件内容为（直接写入文件）：

- 对比旧版的变化：
  1. 步骤 3 新增第三个版本号文件 `build_pkg.sh`
  2. 步骤 4 的 `git add` 新增 `build_pkg.sh`
  3. 步骤 6 改为按系统判断构建 `.deb` 还是 `.pkg`
  4. 步骤 7 release note 新增 macOS 安装说明
  5. 步骤 8 收集所有已构建的包（`.deb` 和 `.pkg`）上传

文件内容请参考 `docs/superpowers/specs/2026-04-16-mac-pkg-packaging-design.md` 中「统一发版命令」章节的完整设计，按以下规则写入 `.claude/commands/github_release.md`：

- 前置检查、步骤 1-2 与旧版完全一致
- 步骤 3 改为更新 3 个文件的版本号：`build_deb.sh`、`deb_package/DEBIAN/control`、`build_pkg.sh`
- 步骤 4 的 git add 包含 `build_deb.sh deb_package/DEBIAN/control build_pkg.sh`
- 步骤 6 改为：根据 `uname` 判断系统，macOS 跑 `build_pkg.sh`，Linux 跑 `build_deb.sh`
- 步骤 7 的 release note 模板新增 macOS 安装说明（`sudo installer -pkg ...`）
- 步骤 8 改为收集当前目录下所有 `*.deb` 和 `*.pkg` 文件上传到 Release

- [ ] **Step 2: Commit**

```bash
git add .claude/commands/github_release.md
git commit -m "feat: 发版命令支持同时构建 .deb 和 .pkg"
```

---

### Task 6: 本地构建测试

**Files:**
- 无新文件

- [ ] **Step 1: 运行构建脚本**

```bash
cd /Users/liweijia/workspace/vibe_coding/claude_history && ./build_pkg.sh
```

预期: 生成 `claude-history_0.1.1_arm64.pkg` 文件，无报错。

- [ ] **Step 2: 检查 .pkg 包内容**

```bash
pkgutil --expand claude-history_0.1.1_arm64.pkg /tmp/claude-history-pkg-check
ls -la /tmp/claude-history-pkg-check/
cat /tmp/claude-history-pkg-check/*package-info 2>/dev/null || cat /tmp/claude-history-pkg-check/*/*.plist 2>/dev/null
```

预期: 包含 `claude-history-server`、`updater-mac`、`VERSION`、`claude_history` 等文件。

- [ ] **Step 3: 清理检查目录**

```bash
rm -rf /tmp/claude-history-pkg-check
```

- [ ] **Step 4: 安装测试（可选，需要 sudo）**

```bash
sudo installer -pkg claude-history_0.1.1_arm64.pkg -target /
```

预期: 安装成功，文件出现在 `/usr/local/claude-history/` 和 `/usr/local/bin/claude_history`。

- [ ] **Step 5: 运行测试**

```bash
claude_history
```

预期: 浏览器自动打开 `http://localhost:8787`，页面正常显示。Ctrl+C 可停止。

- [ ] **Step 6: 版本信息测试**

```bash
claude_history -v
```

预期: 输出 `Claude History Viewer v0.1.1`

- [ ] **Step 7: 卸载测试**

手动删除已安装文件：

```bash
sudo rm -f /usr/local/bin/claude_history
sudo rm -rf /usr/local/claude-history/
```

预期: 干净移除，无残留。

---

### Task 7: 最终提交和清理

- [ ] **Step 1: 确认所有文件已提交**

```bash
git status
```

预期: 工作区干净，无未提交变更。

- [ ] **Step 2: 查看完整 commit 历史**

```bash
git log --oneline -10
```

预期: 包含所有 Mac 打包相关的 commit。
