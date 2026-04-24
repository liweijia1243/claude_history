#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

VERSION="0.1.3"
PKG_NAME="claude-history_${VERSION}_arm64.pkg"
PKG_ROOT="build_pkg_root"

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
pyinstaller --onedir \
    --target-arch arm64 \
    --add-data "web/dist:web/dist" \
    --name claude-history-server \
    --clean \
    --noconfirm \
    server.py

# Step 3: 组装 pkg 目录
echo "[3/4] 组装 .pkg 包..."

# 创建安装目标目录结构
mkdir -p "$PKG_ROOT/usr/local/claude-history/server"
mkdir -p "$PKG_ROOT/usr/local/bin"

# 复制整个 onedir 目录（包含可执行文件和所有依赖）
cp -r dist/claude-history-server/ "$PKG_ROOT/usr/local/claude-history/server/"

# 复制更新器
cp updater-mac "$PKG_ROOT/usr/local/claude-history/"
chmod +x "$PKG_ROOT/usr/local/claude-history/updater-mac"

# 生成版本文件
echo "$VERSION" > "$PKG_ROOT/usr/local/claude-history/VERSION"

# 复制 wrapper 脚本（从模板）
cp pkg_package/root/usr/local/bin/claude_history "$PKG_ROOT/usr/local/bin/"

# Step 4: 打包
echo "[4/4] 打包 $PKG_NAME ..."
pkgbuild --root "$PKG_ROOT" \
    --identifier "com.claude-history.viewer" \
    --version "$VERSION" \
    --scripts "pkg_package/scripts" \
    --install-location "/" \
    "$PKG_NAME"

# 清理构建临时目录
rm -rf "$PKG_ROOT"

echo ""
echo "=== 构建完成 ==="
echo "产物: $PKG_NAME"
echo "大小: $(du -h "$PKG_NAME" | cut -f1)"
echo ""
echo "安装测试: sudo installer -pkg $PKG_NAME -target /"
