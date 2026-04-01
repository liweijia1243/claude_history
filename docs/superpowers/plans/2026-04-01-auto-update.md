# Claude History 自动更新功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 `claude_history --update` 命令，支持从 GitHub Releases 自动下载并安装最新版本。

**Architecture:** 创建独立的 Python 更新器脚本 `updater`，支持 `--check`（静默检测）和 `--update`（执行更新）两种模式。修改启动脚本添加 `--update` 入口和后台静默检测逻辑。

**Tech Stack:** Python 3 (requests, packaging), Bash, GitHub REST API

---

## 文件变更概览

| 文件 | 操作 | 说明 |
|------|------|------|
| `updater` | 创建 | Python 更新器脚本 |
| `deb_package/usr/bin/claude_history` | 修改 | 添加 --update 和后台检测 |
| `build_deb.sh` | 修改 | 复制 updater 和 VERSION 文件 |

---

### Task 1: 创建 updater 脚本

**Files:**
- Create: `updater`

创建独立的 Python 更新器脚本，支持 `--check` 和 `--update` 两种模式。

- [ ] **Step 1: 编写 updater 脚本**

```python
#!/usr/bin/env python3
"""Claude History Viewer 自动更新器"""
import argparse
import os
import subprocess
import sys
import tempfile

# 尽量使用 requests，如果不可用则使用 urllib
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
    # 简单版本比较回退
    def parse_version(v):
        return tuple(int(x) for x in v.split('.'))

GITHUB_REPO = "liweijia1243/claude_history"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
INSTALL_DIR = "/opt/claude-history"
VERSION_FILE = f"{INSTALL_DIR}/VERSION"


def get_current_version():
    """获取当前安装版本"""
    try:
        with open(VERSION_FILE, 'r') as f:
            return f.read().strip()
    except (FileNotFoundError, IOError):
        return "0.0.0"


def get_latest_release():
    """获取 GitHub 最新 release 信息"""
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

    # 查找 .deb 文件
    deb_url = None
    for asset in data.get("assets", []):
        if asset["name"].endswith(".deb") and "amd64" in asset["name"]:
            deb_url = asset["browser_download_url"]
            break

    return version, deb_url


def download_file(url, dest):
    """下载文件到指定路径"""
    if HAS_REQUESTS:
        response = requests.get(url, timeout=60, stream=True)
        response.raise_for_status()
        with open(dest, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    else:
        urllib.request.urlretrieve(url, dest)


def cmd_check():
    """静默检测是否有新版本"""
    try:
        current = get_current_version()
        latest, _ = get_latest_release()

        if parse_version(latest) > parse_version(current):
            print(f"UPDATE_AVAILABLE:v{latest}")
    except Exception:
        # 静默失败，不输出任何内容
        pass


def cmd_update():
    """执行更新"""
    try:
        current = get_current_version()
        print(f"当前版本: {current}")
        print("正在检查更新...")

        latest, deb_url = get_latest_release()

        if parse_version(latest) <= parse_version(current):
            print(f"已是最新版本: {current}")
            sys.exit(0)

        print(f"发现新版本: {latest}")

        if not deb_url:
            print("错误: 未找到 .deb 安装包", file=sys.stderr)
            sys.exit(1)

        # 下载
        print(f"正在下载: {deb_url}")
        with tempfile.NamedTemporaryFile(suffix=".deb", delete=False) as tmp:
            tmp_path = tmp.name

        download_file(deb_url, tmp_path)
        print(f"下载完成: {tmp_path}")

        # 安装
        print("正在安装...")
        result = subprocess.run(
            ["dpkg", "-i", tmp_path],
            capture_output=True,
            text=True
        )

        # 清理临时文件
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

    except requests.exceptions.RequestException as e:
        print(f"网络错误: {e}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"网络错误: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyError as e:
        print(f"解析错误: 缺少字段 {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"更新失败: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Claude History 更新器")
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

- [ ] **Step 2: 添加可执行权限并测试基本语法**

```bash
chmod +x updater
python3 updater --help
```

Expected: 显示帮助信息

- [ ] **Step 3: 测试 --check 功能（模拟测试）**

创建临时测试版本文件：
```bash
mkdir -p /tmp/test-update/opt/claude-history
echo "0.0.1" > /tmp/test-update/opt/claude-history/VERSION
```

修改脚本临时指向测试目录进行验证（或直接在真实环境测试）。

- [ ] **Step 4: Commit**

```bash
git add updater
git commit -m "feat: 添加 updater 自动更新器脚本

支持两种模式：
- --check: 静默检测是否有新版本
- --update: 下载并安装最新版本

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 2: 修改启动脚本添加 --update 和后台检测

**Files:**
- Modify: `deb_package/usr/bin/claude_history`

- [ ] **Step 1: 添加 --update 分支和 --check 后台检测**

修改 `deb_package/usr/bin/claude_history`，在参数解析部分添加 `--update` 处理，在启动流程前添加后台检测：

完整修改后的文件：

```bash
#!/bin/bash
# Claude History Viewer 启动脚本

SERVER="/opt/claude-history/claude-history-server"
UPDATER="/opt/claude-history/updater"
PORT=8787
SHARED=false

# --update 单独处理（需要 sudo）
if [ "$1" = "--update" ]; then
    if [ ! -f "$UPDATER" ]; then
        echo "错误: 未找到更新器 $UPDATER" >&2
        exit 1
    fi
    exec sudo "$UPDATER" --update
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

# 检查端口是否被占用
if ss -tlnp 2>/dev/null | grep -q ":${PORT} "; then
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
    ACCESS="http://$(hostname -I 2>/dev/null | awk '{print $1}'):${PORT} 或 http://localhost:${PORT}"
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

# 打开浏览器
echo "正在打开浏览器: $ACCESS"
xdg-open "http://localhost:${PORT}" 2>/dev/null &

echo "Claude History Viewer 运行中: $ACCESS"
echo "按 Ctrl+C 停止"
wait "$SERVER_PID"
```

- [ ] **Step 2: 验证脚本语法**

```bash
bash -n deb_package/usr/bin/claude_history && echo "语法检查通过"
```

Expected: 输出 "语法检查通过"

- [ ] **Step 3: Commit**

```bash
git add deb_package/usr/bin/claude_history
git commit -m "feat: 添加 --update 命令和后台更新检测

- 新增 --update 选项，调用 sudo 执行更新
- 启动时后台静默检测新版本，有则提示用户
- 检测失败时不影响正常启动

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 3: 修改构建脚本

**Files:**
- Modify: `build_deb.sh`

- [ ] **Step 1: 修改 build_deb.sh 添加 updater 和 VERSION**

在 Step 3 的组装部分添加 updater 和 VERSION 文件：

```bash
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

VERSION="0.0.7"
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

# 复制更新器
cp updater "$BUILD_DIR/opt/claude-history/"
chmod +x "$BUILD_DIR/opt/claude-history/updater"

# 生成版本文件
echo "$VERSION" > "$BUILD_DIR/opt/claude-history/VERSION"

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

- [ ] **Step 2: Commit**

```bash
git add build_deb.sh
git commit -m "feat: 构建时包含 updater 和 VERSION 文件

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 4: 端到端测试

**Files:**
- Test: 手动测试

- [ ] **Step 1: 构建新的 .deb 包**

```bash
./build_deb.sh
```

Expected: 构建成功，生成 `claude-history_0.0.7_amd64.deb`

- [ ] **Step 2: 安装测试**

```bash
sudo dpkg -i claude-history_0.0.7_amd64.deb
```

Expected: 安装成功

- [ ] **Step 3: 验证文件安装正确**

```bash
ls -la /opt/claude-history/
cat /opt/claude-history/VERSION
```

Expected: 看到 `updater` 和 `VERSION` 文件

- [ ] **Step 4: 测试 --help 显示新选项**

```bash
claude_history --help
```

Expected: 帮助信息包含 `--update` 选项

- [ ] **Step 5: 测试 --check（需要网络）**

```bash
/opt/claude-history/updater --check
```

Expected: 如果有新版本，输出 `UPDATE_AVAILABLE:vX.X.X`

- [ ] **Step 6: 测试 --update（可选，需要 sudo 和实际有新版本）**

```bash
claude_history --update
```

Expected: 检测版本，如有更新则下载安装

---

## 自检清单

| 需求 | 实现位置 |
|------|----------|
| `--update` 执行更新 | `deb_package/usr/bin/claude_history` 第 10-15 行 |
| 启动时静默检测 | `deb_package/usr/bin/claude_history` 第 65-73 行 |
| 离线容错 | `updater` 中 try/except 静默处理 |
| 更新后提示重启 | `updater` cmd_update() 函数 |
| VERSION 文件 | `build_deb.sh` 第 43 行 |
| updater 脚本安装 | `build_deb.sh` 第 40-41 行 |
