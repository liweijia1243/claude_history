# Claude History Viewer .deb 打包设计

## 目标

将 Claude History Viewer 打包为 `.deb`，发布到 GitHub Release，供 Ubuntu 20.04+ 用户安装使用。安装后终端输入 `claude_history` 即可自动启动后端并打开浏览器。

## 方案选择

**PyInstaller + 手写 deb 结构**

- PyInstaller 将 `server.py` + 前端 dist 打成单个可执行文件
- 手写 `DEBIAN/control` 等元数据组装 .deb
- 不依赖系统 Python 包版本，完全自包含

## 入口脚本

安装后用户执行 `claude_history`，实际是一个 shell wrapper 脚本 `/usr/bin/claude_history`：

1. 启动 `/opt/claude-history/claude-history-server`（后台）
2. 轮询 `localhost:8787` 等待端口就绪
3. `xdg-open http://localhost:8787` 打开浏览器
4. `wait` 后端进程（前台阻塞）
5. 收到 SIGINT/SIGTERM 时 kill 后端并退出

端口冲突检测：如果 8787 已被占用，提示用户并退出。

## 文件布局

### .deb 包内文件结构

```
/opt/claude-history/
  claude-history-server          # PyInstaller 二进制
/usr/bin/
  claude_history                 # shell wrapper 脚本
/usr/share/doc/claude-history/
  README.md
  LICENSE
```

### 项目新增构建文件

```
项目根目录/
  build_deb.sh                   # 一键构建脚本
  deb_package/                    # deb 包结构模板
    DEBIAN/
      control                     # 包元数据 + 依赖声明
      postinst                    # 安装后钩子（设置权限）
      prerm                       # 卸载前钩子（清理）
  claude-history.spec             # PyInstaller spec 文件（可选）
```

## 构建流程

`build_deb.sh` 执行步骤：

1. `cd web && npm install && npm run build` — 构建前端
2. `pyinstaller --onefile --add-data "web/dist:web/dist" --name claude-history-server server.py` — 打包后端
3. 组装 deb 目录：
   - 复制二进制到 `deb_package/opt/claude-history/`
   - 复制 wrapper 脚本到 `deb_package/usr/bin/`
   - 复制文档到 `deb_package/usr/share/doc/claude-history/`
4. `dpkg-deb -b deb_package/ claude-history_X.X.X_amd64.deb` — 生成 deb

## DEBIAN/control

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

## server.py 适配修改

为支持 PyInstaller 打包，`server.py` 需小改动：

1. **静态文件路径**: PyInstaller `--onefile` 模式运行时解压到临时目录 `_MEIPASS`，需用 `sys._MEIPASS` 定位 `web/dist`
2. **自动打开浏览器**: 添加 `--no-open` 参数，wrapper 脚本不传此参数（自动打开）
3. **端口参数**: 添加 `--port` 参数，默认 8787

```python
import sys

def get_base_path():
    """获取资源文件基础路径，兼容 PyInstaller 和普通运行"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent
```

`dist_dir` 改为使用 `get_base_path() / "web" / "dist"`。改动约 10 行，不影响开发模式行为。

## GitHub Release 集成

- 使用 GitHub Actions 在 Ubuntu 20.04 容器中构建，确保 glibc 兼容性（在旧系统构建的产物可在新系统运行）
- 构建产物 `claude-history_X.X.X_amd64.deb` 上传到 Release Assets
- 用户下载后 `sudo dpkg -i claude-history_*.deb` 安装

## 用户使用流程

```bash
# 下载
wget https://github.com/<user>/<repo>/releases/download/v0.0.3/claude-history_0.0.3_amd64.deb

# 安装
sudo dpkg -i claude-history_0.0.3_amd64.deb
sudo apt-get install -f  # 自动安装缺失依赖

# 使用
claude_history  # 自动启动后端 + 打开浏览器

# 退出
Ctrl+C  # 停止后端
```

## 约束与假设

- 目标系统: Ubuntu 20.04+ (amd64)
- 需要有桌面环境（xdg-open 需要图形环境）
- 用户已安装 Claude Code，`~/.claude/` 目录存在
- 构建环境需在 Ubuntu 20.04 上（glibc 前向兼容）
