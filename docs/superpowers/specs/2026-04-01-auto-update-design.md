# Claude History 自动更新功能设计

## 概述

实现 `claude_history --update` 命令，支持从 GitHub Releases 自动下载并安装最新版本。

## 需求

1. 用户执行 `claude_history --update` 时，自动检测、下载并安装最新版本
2. 每次启动时静默检测是否有新版本，有则提示用户（不阻塞）
3. 离线环境或 API 受限时，静默失败，不影响正常运行
4. 更新完成后提示用户重新启动

## 约束

- 使用 GitHub 匿名 API（60次/小时限额），不做 Token 配置
- 更新需要 sudo 权限
- 仅支持 Linux amd64 (.deb)

## 文件结构

```
/opt/claude-history/
├── claude-history-server     # 主程序（不变）
└── updater                   # 新增：Python 更新器脚本

/usr/bin/claude_history       # 启动脚本（修改）
```

## 组件设计

### 1. updater 脚本

路径：`/opt/claude-history/updater`

独立的 Python 脚本，两种运行模式：

#### 模式 A：`--check` 静默检测

```bash
/opt/claude-history/updater --check
```

- 调用 GitHub API 获取最新 release 版本号
- 与当前版本比较（从 `/opt/claude-history/VERSION` 读取）
- 有新版本时输出 `UPDATE_AVAILABLE:v0.0.8`，无则无输出
- 任何错误（网络、API、解析）都静默退出（exit 0，无输出）

#### 模式 B：`--update` 执行更新

```bash
sudo /opt/claude-history/updater --update
```

- 获取最新版本信息
- 下载 `.deb` 文件到 `/tmp/claude-history-update.deb`
- 执行 `dpkg -i` 安装
- 成功后输出提示信息，失败输出错误信息
- 返回码：0 成功，1 失败

#### 版本文件

新增 `/opt/claude-history/VERSION`，内容为版本号（如 `0.0.7`），供 updater 读取比较。

### 2. claude_history 启动脚本修改

#### 新增 `--update` 分支

```bash
if [ "$1" = "--update" ]; then
    exec sudo /opt/claude-history/updater --update
fi
```

#### 启动时后台静默检测

在正常启动流程前添加：

```bash
# 后台静默检测更新（不等待，不阻塞）
(/opt/claude-history/updater --check 2>/dev/null | while read -r line; do
    if [[ "$line" == UPDATE_AVAILABLE:* ]]; then
        new_ver="${line#UPDATE_AVAILABLE:}"
        echo ""
        echo "  有新版本 $new_ver 可用，运行 claude_history --update 进行更新"
        echo ""
    fi
done) &
```

## 流程图

### 正常启动流程

```
用户运行 claude_history
        │
        ▼
┌───────────────────┐
│ 后台启动检测进程   │ ──(不等待)──► 检测 API ──► 有新版本？ ──► 打印提示
└───────────────────┘                              │
        │                                          ▼
        │                                    无新版本/失败
        │                                          │
        ▼                                          ▼
   正常启动服务                               静默退出
```

### 更新流程

```
用户运行 claude_history --update
        │
        ▼
   sudo 调用 updater --update
        │
        ▼
   获取最新版本信息
        │
        ▼
   下载 .deb 到 /tmp
        │
        ▼
   dpkg -i 安装
        │
        ▼
   提示用户重启
```

## 错误处理

| 场景 | --check 行为 | --update 行为 |
|------|-------------|---------------|
| 网络不可达 | 静默退出（无输出） | 提示网络错误，exit 1 |
| GitHub API 限流 | 静默退出（无输出） | 提示 API 限流，exit 1 |
| 下载失败 | N/A | 提示下载失败，exit 1 |
| dpkg 安装失败 | N/A | 提示安装失败，exit 1 |
|已是最新版本 | 无输出 | 提示已是最新，exit 0 |

## 实现要点

### GitHub API 调用

```python
# 获取最新 release
url = "https://api.github.com/repos/liweijia1243/claude_history/releases/latest"
response = requests.get(url, timeout=5)
data = response.json()
version = data["tag_name"].lstrip("v")  # v0.0.7 -> 0.0.7
deb_url = next(a["browser_download_url"] for a in data["assets"] if a["name"].endswith(".deb"))
```

### 版本比较

使用 `packaging.version.parse()` 进行语义化版本比较。

## 构建变更

### build_deb.sh 修改

1. 生成 `VERSION` 文件到 `/opt/claude-history/VERSION`
2. 复制 `updater` 脚本到 `/opt/claude-history/updater`

### deb_package 目录变更

```
deb_package/
├── DEBIAN/
│   ├── control
│   ├── postinst
│   └── prerm
└── opt/claude-history/
    └── (构建时填入)
    ├── claude-history-server
    ├── updater          # 新增
    └── VERSION          # 新增
```
