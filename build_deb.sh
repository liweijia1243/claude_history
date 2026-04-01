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
