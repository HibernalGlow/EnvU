# Scoolp - Scoop 管理工具

统一的 Scoop 管理工具，集成初始化、包安装、同步和缓存清理功能。

## 功能特性

- 🚀 **init**: 初始化和安装 Scoop
- 📦 **install**: 安装 Scoop 包（来自本地 bucket）
- 🔄 **sync**: 同步 buckets 和配置
- 🧹 **clean**: 清理 Scoop 缓存中的过期安装包
- 🎯 **交互式界面**: 无参数运行时自动进入友好的交互式菜单

## 安装

```bash
cd LazyCommand/EnvU
pip install -e .
```

## 使用方法

### 交互式模式（推荐）

直接运行 `scoolp` 进入交互式菜单：

```bash
scoolp
```

### 命令行模式

#### Init 子命令 - Scoop 初始化

**安装 Scoop:**
```bash
scoolp init install
scoolp init install --dir D:/scoop  # 指定安装目录
```

**检查 Scoop 状态:**
```bash
scoolp init check
```

#### Install 子命令 - 包安装管理

**安装指定包：**
```bash
scoolp install install emm
scoolp install install lanraragi --bucket-path /path/to/bucket
```

**列出所有可用包：**
```bash
scoolp install list
scoolp install list --bucket-path /path/to/bucket
```

**查看包信息：**
```bash
scoolp install info emm
scoolp install info lanraragi --bucket-path /path/to/bucket
```

**交互式安装（无参数）：**
```bash
scoolp install install
```

#### Sync 子命令 - 同步配置

**同步 buckets:**
```bash
scoolp sync sync
scoolp sync sync --config /path/to/scoop.toml
scoolp sync sync --dry-run  # 预览模式
```

**查看配置:**
```bash
scoolp sync show-config
scoolp sync show-config --config /path/to/scoop.toml
```

#### Clean 子命令 - 缓存清理

**列出过期缓存：**
```bash
scoolp clean list
scoolp clean list /custom/cache/path
```

**备份过期缓存：**
```bash
scoolp clean backup
scoolp clean backup /custom/cache/path
```

**删除过期缓存：**
```bash
scoolp clean delete
scoolp clean delete --force  # 跳过确认
scoolp clean delete /custom/cache/path
```

## 目录结构

```
src/scoolp/
├── __init__.py          # 模块初始化
├── __main__.py          # 主入口和 CLI 定义
├── init.py              # Scoop 初始化功能
├── install.py           # 包安装功能（原 scoop/install.py）
├── sync.py              # 同步功能（基于 scoop_sync.py）
├── clean.py             # 缓存清理功能（复刻 scoop-cache-cleaner）
├── interactive.py       # 交互式菜单
├── scoop.toml           # 默认同步配置
└── README.md            # 本文档
```

## 配置文件

### scoop.toml

同步功能使用的配置文件示例：

```toml
[scoop]
root = "D:/scoop"
repo = "https://gitee.com/scoop-bucket/scoop"  # 可选：镜像源

[[bucket]]
name = "main"

[[bucket]]
name = "extras"

[[bucket]]
name = "my-bucket"
url = "https://github.com/username/my-bucket"

[options]
remove_all_before_add = true
reset_core_repo = true
run_update = true
set_env = false
try_fix_ownership = true
dry_run = false
```

## 技术栈

- **typer**: 现代化的 CLI 框架
- **rich**: 美化的终端输出
- **pathlib**: 跨平台路径处理
- **tomllib**: TOML 配置文件解析（Python 3.11+）

## 命令速查

| 场景 | 命令 |
|------|------|
| 交互式菜单 | `scoolp` |
| 安装 Scoop | `scoolp init install` |
| 检查 Scoop | `scoolp init check` |
| 安装包 | `scoolp install install <包名>` |
| 列出包 | `scoolp install list` |
| 同步 buckets | `scoolp sync sync` |
| 清理缓存 | `scoolp clean delete` |

## 迁移说明

### 从原始文件迁移

| 原文件 | 新命令 |
|--------|--------|
| `scoop/install.py` | `scoolp install` |
| `scoop_sync.py` | `scoolp sync` |
| `scoop-cache-cleaner` | `scoolp clean` |

### 命令对照

**原 scoop/install.py:**
```bash
python install.py -p emm    → scoolp install install emm
python install.py -l        → scoolp install list
python install.py -i emm    → scoolp install info emm
```

**原 scoop_sync.py:**
```bash
python scoop_sync.py        → scoolp sync sync
```

**原 scoop-cache-cleaner:**
```bash
scc -l    → scoolp clean list
scc -b    → scoolp clean backup
scc -d    → scoolp clean delete
```

## 环境变量

- `SCOOP`: Scoop 安装路径（用于 clean 命令默认缓存路径）

## 特色功能

### 1. 统一的 CLI 体验
所有功能都在 `scoolp` 命令下，一致的参数风格。

### 2. 交互式和命令行双模式
- 交互式：适合探索和学习
- 命令行：适合自动化和脚本

### 3. 美化的输出
- 表格形式的列表
- 彩色的状态信息
- 进度条显示

### 4. 安全机制
- 删除前确认
- 备份选项
- 预览模式（dry-run）

### 5. 模块化设计
- 清晰的职责分离
- 易于维护和扩展
- 类型安全

## 常见用例

### 场景 1: 首次设置 Scoop

```bash
# 1. 安装 Scoop
scoolp init install

# 2. 同步 buckets（如果有配置文件）
scoolp sync sync

# 3. 安装软件包
scoolp install install
```

### 场景 2: 日常使用

```bash
# 查看可用包
scoolp install list

# 安装包
scoolp install install emm

# 定期清理缓存
scoolp clean delete
```

### 场景 3: 批量同步环境

```bash
# 1. 准备 scoop.toml 配置文件
# 2. 同步所有 buckets
scoolp sync sync --config myconfig.toml
```

## 开发说明

### 添加新的子命令

1. 在 `src/scoolp/` 创建新模块
2. 创建 `app = typer.Typer()` 实例
3. 在 `__main__.py` 中注册：
   ```python
   from .newmodule import app as newmodule_app
   app.add_typer(newmodule_app, name="newmodule", help="...")
   ```

### 添加到交互式菜单

在 `interactive.py` 的 `interactive_menu()` 函数中添加菜单项。

## 许可证

继承自原项目的许可证。
