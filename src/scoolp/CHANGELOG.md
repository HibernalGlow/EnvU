# Scoolp 变更日志

## [0.1.0] - 2025-10-24

### 🎉 初始版本

基于 `scoop/install.py` 迁移并扩展为完整的 Scoop 管理工具。

### ✨ 新增功能

#### Init 模块（包管理）
- ✅ 迁移所有 `install.py` 的功能到 `init.py`
- ✅ 使用 Typer 重构 CLI 接口
- ✅ 三个子命令：`install`, `list`, `info`
- ✅ 支持交互式和命令行两种模式
- ✅ 统一使用 Rich 美化输出

#### Clean 模块（缓存清理）
- ✅ 复刻 Go 版本 `scoop-cache-cleaner` 的完整功能
- ✅ 解析 Scoop 缓存文件格式 (`name#version#extension`)
- ✅ 智能识别每个软件的最新版本
- ✅ 三种清理模式：`list`, `backup`, `delete`
- ✅ 安全确认机制和进度显示
- ✅ 美化的统计信息输出

#### 交互式界面
- ✅ 无参数运行自动进入交互式菜单
- ✅ 直观的菜单选项
- ✅ 可连续执行多个操作
- ✅ 友好的用户体验

### 🔧 技术改进

- ✅ 模块化设计（init, clean, interactive 分离）
- ✅ 类型注解和类型安全
- ✅ 统一的错误处理
- ✅ 跨平台路径处理（pathlib）
- ✅ 配置化的入口点（pyproject.toml）

### 📚 文档

- ✅ 详细的 README 文档
- ✅ 迁移完成报告
- ✅ 快速开始指南
- ✅ 代码注释和类型提示

### 🎯 命令对照表

**原 install.py → scoolp init**
- `python install.py` → `scoolp init install`
- `python install.py -p PKG` → `scoolp init install PKG`
- `python install.py -l` → `scoolp init list`
- `python install.py -i PKG` → `scoolp init info PKG`

**scoop-cache-cleaner → scoolp clean**
- `scc -l` → `scoolp clean list`
- `scc -b` → `scoolp clean backup`
- `scc -d` → `scoolp clean delete`

### 📦 依赖

- rich >= 10.0.0
- typer >= 0.9.0
- Python >= 3.11

### 🏗️ 文件结构

```
src/scoolp/
├── __init__.py          # 模块初始化
├── __main__.py          # 主入口和路由
├── init.py              # 包安装功能
├── clean.py             # 缓存清理功能
├── interactive.py       # 交互式界面
├── README.md            # 使用文档
└── CHANGELOG.md         # 本文件
```

### 🎨 特色功能

1. **统一的 CLI 体验**：所有功能都在 `scoolp` 命令下
2. **交互式和命令行双模式**：适合不同使用场景
3. **美化的输出**：使用 Rich 提供更好的视觉效果
4. **安全的清理机制**：删除前确认、备份选项
5. **详细的统计信息**：清晰了解清理效果

### 🔜 未来计划

- [ ] 添加配置文件支持
- [ ] 支持多 bucket 管理
- [ ] 缓存分析和可视化
- [ ] 自动化清理策略
- [ ] 包依赖关系图
- [ ] 批量操作支持

---

迁移自：
- `scoop/install.py` (原始包安装工具)
- `scoop/ref/scoop-cache-cleaner/*.go` (Go 版本缓存清理工具)

