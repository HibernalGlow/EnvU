# Scoolp 快速开始指南

## 🎉 迁移已完成！

`scoop/install.py` 已成功迁移到 `src/scoolp` 模块，并复刻了 `scoop-cache-cleaner` 功能。

## ⚡ 5 分钟快速上手

### 第一步：安装

```bash
# 进入项目目录
cd LazyCommand/EnvU

# 安装 scoolp（这会自动安装 typer 和 rich 依赖）
pip install -e .
```

### 第二步：验证安装

```bash
# 查看帮助信息
scoolp --help

# 查看子命令帮助
scoolp init --help
scoolp clean --help
```

### 第三步：开始使用

#### 🎯 推荐：交互式模式

最简单的使用方式，直接运行：

```bash
scoolp
```

你会看到一个友好的菜单界面，选择你想要的操作即可。

#### 📦 安装 Scoop 包

```bash
# 方式1: 直接安装指定包
scoolp init install emm

# 方式2: 交互式选择安装
scoolp init install

# 列出所有可用的包
scoolp init list

# 查看某个包的详细信息
scoolp init info lanraragi
```

#### 🧹 清理 Scoop 缓存

```bash
# 查看有哪些过期的缓存文件
scoolp clean list

# 备份过期缓存（移动到时间戳目录）
scoolp clean backup

# 删除过期缓存（会提示确认）
scoolp clean delete

# 强制删除（跳过确认）
scoolp clean delete --force
```

## 📚 常用命令速查

| 场景 | 命令 |
|------|------|
| 进入交互式菜单 | `scoolp` |
| 安装包 | `scoolp init install <包名>` |
| 查看所有包 | `scoolp init list` |
| 查看包信息 | `scoolp init info <包名>` |
| 查看过期缓存 | `scoolp clean list` |
| 清理缓存 | `scoolp clean delete` |

## 🔧 高级用法

### 指定 Bucket 路径

```bash
scoolp init list --bucket-path D:/scoop/buckets/my-bucket
scoolp init install emm --bucket-path D:/scoop/buckets/my-bucket
```

### 指定缓存路径

```bash
scoolp clean list D:/custom/cache/path
scoolp clean delete D:/custom/cache/path --force
```

### 环境变量

如果设置了 `SCOOP` 环境变量，clean 命令会自动使用 `$SCOOP/cache` 作为缓存路径。

## 💡 使用技巧

1. **第一次使用**：建议先运行 `scoolp` 进入交互式模式熟悉功能
2. **安装包前**：可以先用 `scoolp init info <包名>` 查看包的详细信息
3. **清理缓存前**：建议先用 `scoolp clean list` 查看会清理哪些文件
4. **安全清理**：首次使用建议用 `backup` 模式，确认无误后再用 `delete`

## 📖 更多文档

- 详细使用文档: `src/scoolp/README.md`
- 迁移报告: `SCOOLP_MIGRATION.md`

## 🐛 常见问题

### Q: 提示找不到 typer 模块？

A: 运行 `pip install -e .` 安装依赖

### Q: Clean 命令提示找不到 SCOOP 环境变量？

A: 方式1：设置环境变量 `set SCOOP=D:\scoop`  
方式2：直接指定路径 `scoolp clean list D:\scoop\cache`

### Q: 原来的 install.py 还能用吗？

A: 可以，保留了原文件作为参考。但建议使用新的 scoolp 命令。

## 🎊 开始探索吧！

现在就试试运行 `scoolp` 体验新的命令行工具吧！

