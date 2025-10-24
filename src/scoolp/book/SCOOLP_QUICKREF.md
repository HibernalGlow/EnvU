# Scoolp 快速参考

## 📦 安装

```bash
cd LazyCommand/EnvU
pip install -e .
```

## 🚀 快速开始

```bash
# 交互式模式（最简单）
scoolp

# 或查看帮助
scoolp --help
```

## 📋 命令速查表

### 基础命令

| 命令 | 说明 |
|------|------|
| `scoolp` | 进入交互式菜单 |
| `scoolp --help` | 查看帮助 |
| `scoolp [子命令] --help` | 查看子命令帮助 |

### Init - Scoop 初始化

| 命令 | 说明 |
|------|------|
| `scoolp init install` | 安装 Scoop |
| `scoolp init install --dir D:/scoop` | 安装到指定目录 |
| `scoolp init check` | 检查 Scoop 是否已安装 |

### Install - 包管理

| 命令 | 说明 |
|------|------|
| `scoolp install install` | 交互式安装包 |
| `scoolp install install <包名>` | 安装指定包 |
| `scoolp install list` | 列出所有可用包 |
| `scoolp install info <包名>` | 查看包信息 |

### Sync - 同步 Buckets

| 命令 | 说明 |
|------|------|
| `scoolp sync sync` | 同步 buckets |
| `scoolp sync sync --dry-run` | 预览模式（不执行） |
| `scoolp sync sync -c config.toml` | 使用指定配置 |
| `scoolp sync show-config` | 显示当前配置 |

### Clean - 缓存清理

| 命令 | 说明 |
|------|------|
| `scoolp clean list` | 列出过期缓存 |
| `scoolp clean backup` | 备份过期缓存 |
| `scoolp clean delete` | 删除过期缓存 |
| `scoolp clean delete --force` | 强制删除（跳过确认） |

## 🎯 常见场景

### 场景 1: 首次设置

```bash
# 1. 安装 Scoop
scoolp init install

# 2. 同步 buckets
scoolp sync sync

# 3. 安装软件
scoolp install install
```

### 场景 2: 安装软件包

```bash
# 查看可用包
scoolp install list

# 查看包详情
scoolp install info emm

# 安装包
scoolp install install emm
```

### 场景 3: 定期维护

```bash
# 同步 buckets
scoolp sync sync

# 清理缓存
scoolp clean delete
```

## ⚙️ 配置文件

创建 `scoop.toml`：

```toml
[scoop]
root = "D:/scoop"
repo = "https://gitee.com/scoop-bucket/scoop"

[[bucket]]
name = "main"

[[bucket]]
name = "extras"

[options]
remove_all_before_add = true
reset_core_repo = true
run_update = true
```

## 🎨 交互式菜单

运行 `scoolp` 后的菜单选项：

```
0 - 检查 Scoop 状态
1 - 安装包
2 - 列出可用包
3 - 查看包信息
4 - 同步 buckets
5 - 列出过期缓存
6 - 备份过期缓存
7 - 删除过期缓存
q - 退出
```

## 📚 更多帮助

- 详细文档: `src/scoolp/README.md`
- 重构报告: `SCOOLP_REFACTOR.md`
- 在线帮助: `scoolp [命令] --help`

## 💡 提示

1. **首次使用**: 运行 `scoolp` 进入交互式模式
2. **脚本使用**: 使用完整命令如 `scoolp install install emm`
3. **安全操作**: 删除前先用 `--dry-run` 预览
4. **配置文件**: 放在项目根目录或 `config/` 目录

---

快速开始，就这么简单！ 🚀

