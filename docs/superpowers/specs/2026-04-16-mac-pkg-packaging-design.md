# Mac .pkg + Homebrew 打包设计

## 背景

项目已有完整的 Ubuntu/Deb 打包流程（`build_deb.sh` + `deb_package/`），需要新增 Mac (.pkg) 打包支持，同时为后续 Homebrew Formula 预留空间。

## 目标

1. 产出 `.pkg` 安装包，用户双击即可安装
2. Mac 版 wrapper 脚本，适配 macOS 命令差异
3. Mac 版 updater，支持自动更新
4. 统一发版命令，同时产出 `.deb` + `.pkg`
5. 为 Homebrew Formula 预留接口

## 安装路径

```
/usr/local/claude-history/
├── claude-history-server    # PyInstaller 单文件二进制 (arm64)
├── updater-mac              # Mac 版更新脚本
└── VERSION                  # 版本文件

/usr/local/bin/
└── claude_history           # Shell wrapper 入口脚本
```

使用 `/usr/local/`（Mac 标准做法，Homebrew 默认路径，PATH 默认包含）。

## 文件结构

### 新增文件

```
build_pkg.sh                        # Mac 构建脚本
pkg_package/
├── scripts/
│   ├── preinstall                  # 安装前：停掉旧版进程
│   └── postinstall                 # 安装后：设权限 + 检查 PATH
└── root/
    └── usr/
        └── local/
            ├── bin/
            │   └── claude_history  # Mac 版 wrapper 脚本
            └── claude-history/
                └── .gitkeep        # 目录占位（构建时填充）
updater-mac                         # Mac 版自动更新脚本
```

### 修改文件

```
.github/workflows/build-deb.yml     # 暂不改（CI 后续再加）
.claude/commands/github_release.md   # 新增 .pkg 构建逻辑
.gitignore                           # 新增 *.pkg 忽略规则
```

## build_pkg.sh

4 步构建流程（对称 `build_deb.sh`）：

```bash
VERSION="0.1.1"
PKG_NAME="claude-history_${VERSION}_arm64.pkg"
PKG_ROOT="pkg_package/root"

# Step 1: 构建前端
cd web && npm install --silent && npm run build && cd ..

# Step 2: PyInstaller 打包 (arm64)
pip install pyinstaller --quiet
pyinstaller --onefile \
    --target-arch arm64 \
    --add-data "web/dist:web/dist" \
    --name claude-history-server \
    --clean --noconfirm server.py

# Step 3: 组装 pkg 目录
mkdir -p "$PKG_ROOT/usr/local/claude-history"
mkdir -p "$PKG_ROOT/usr/local/bin"
cp dist/claude-history-server "$PKG_ROOT/usr/local/claude-history/"
cp updater-mac "$PKG_ROOT/usr/local/claude-history/"
echo "$VERSION" > "$PKG_ROOT/usr/local/claude-history/VERSION"
cp pkg_package/root/usr/local/bin/claude_history "$PKG_ROOT/usr/local/bin/"

# Step 4: 打包
pkgbuild --root "$PKG_ROOT" \
    --identifier "com.claude-history.viewer" \
    --version "$VERSION" \
    --scripts "pkg_package/scripts" \
    --install-location "/" \
    "$PKG_NAME"
```

## Mac wrapper 脚本 (`claude_history`)

与 Linux 版功能对齐，适配 macOS 命令：

| 功能 | Linux | Mac |
|------|-------|-----|
| 打开浏览器 | `xdg-open URL` | `open URL` |
| 检查端口占用 | `ss -tlnp \| grep :PORT` | `lsof -i :PORT -t` |
| 获取局域网 IP | `hostname -I \| awk '{print $1}'` | `ipconfig getifaddr en0` |
| 二进制路径 | `/opt/claude-history/` | `/usr/local/claude-history/` |
| 更新命令 | `sudo updater --update` | `sudo updater-mac --update` |

其余逻辑（参数解析、后台更新检测、端口检查、cleanup trap）与 Linux 版一致。

## 安装脚本

### preinstall

```bash
#!/bin/bash
# 安装前：停掉正在运行的旧版
pkill -f "/usr/local/claude-history/claude-history-server" 2>/dev/null || true
exit 0
```

### postinstall

```bash
#!/bin/bash
# 设置可执行权限
chmod +x /usr/local/claude-history/claude-history-server
chmod +x /usr/local/bin/claude_history
chmod +x /usr/local/claude-history/updater-mac
exit 0
```

## Mac updater (`updater-mac`)

与 Linux `updater` 功能对齐：

- 读取 `/usr/local/claude-history/VERSION`
- 查 GitHub API，查找 `.pkg` 附件（而非 `.deb`）
- 下载到临时文件
- 安装：`sudo installer -pkg tmp.pkg -target /`（替代 `dpkg -i`）
- 清理临时文件
- 支持 `--check`（静默检测）和 `--update`（执行更新）

## 统一发版命令 `/github_release`

修改 `.claude/commands/github_release.md`：

### 版本号更新

新增第三个文件需要更新版本号：
1. `build_deb.sh` 第 7 行（已有）
2. `deb_package/DEBIAN/control` 第 2 行（已有）
3. **`build_pkg.sh` 第 X 行**（新增）

### 本地构建

根据当前系统决定构建哪种包：

```bash
# Linux: 构建 .deb
bash build_deb.sh

# Mac: 构建 .pkg
bash build_pkg.sh
```

### 创建 Release

```bash
# 收集所有已构建的包
ASSETS=""
[ -f claude-history_${VERSION}_amd64.deb ] && ASSETS+="claude-history_${VERSION}_amd64.deb "
[ -f claude-history_${VERSION}_arm64.pkg ] && ASSETS+="claude-history_${VERSION}_arm64.pkg "

gh release create v${VERSION} $ASSETS --title "v${VERSION}" --notes "..."
```

### Release Note 格式

```markdown
## What's New
### 功能分类
- 变更描述

---

### 安装

**Ubuntu/Debian:**
sudo dpkg -i claude-history_{version}_amd64.deb
sudo apt-get install -f
claude_history

**macOS:**
sudo installer -pkg claude-history_{version}_arm64.pkg -target /
claude_history

> 或通过 Homebrew: brew tap liweijia1243/claude-history && brew install claude-history
```

## Homebrew Formula（预留）

后续添加一个 Homebrew tap 仓库（`homebrew-claude-history`），Formula 内容：

```ruby
class ClaudeHistory < Formula
  desc "Claude Code session history visualizer"
  homepage "https://github.com/liweijia1243/claude_history"
  url "https://github.com/liweijia1243/claude_history/releases/download/v{VERSION}/claude-history_{VERSION}_arm64.pkg"
  version "{VERSION}"
  sha256 "..."

  def install
    # 解压 .pkg，复制文件到 Homebrew prefix
    system "pkgutil", "--expand", cached_download, "pkg_expanded"
    # ... 提取二进制到 bin/
  end
end
```

用户使用：`brew install liweijia1243/claude-history/claude-history`

## 版本号策略

与现有 deb 保持一致：版本号存储在 `build_pkg.sh` 中的 `VERSION` 变量，
`/github_release` 命令统一更新所有三个位置。

## 后续工作

1. CI 添加 macOS runner（`macos-latest`），tag 触发时自动构建 `.pkg`
2. 代码签名（`codesign`）和 notarization（`xcrun notarytool`）
3. Universal Binary（同时支持 arm64 + x86_64，用 `lipo` 合并）
