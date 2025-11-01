# Scoolp 配置指南

## 配置文件概述

`clean_config.toml` 是 scoolp 清理工具的**通用配置文件**，控制所有 `scoolp clean` 子命令的行为。

## 配置文件位置

- **实际配置**: `src/scoolp/clean_config.toml`
- **示例配置**: `src/scoolp/clean_config_example.toml`

## 配置加载优先级

1. **命令行参数** - 最高优先级
2. **配置文件** - 次优先级
3. **环境变量** - 较低优先级
4. **默认值** - 最低优先级

## 配置结构

### 1. 路径配置 `[paths]`

控制 Scoop 相关路径的配置。

```toml
[paths]
# Scoop 根目录（留空则从环境变量获取）
scoop_root = ""

# 缓存目录（相对于 scoop_root）
cache_dir = "cache"

# 备份目录名称模板（支持 {timestamp} 变量）
backup_dir_template = "cache_backup_{timestamp}"
```

**使用场景：**
- 多 Scoop 实例管理
- 自定义缓存位置
- 自定义备份目录命名

**示例：**
```toml
# Windows 用户
scoop_root = "D:/scoop"

# Linux 用户
scoop_root = "/home/user/.scoop"

# 自定义缓存位置
cache_dir = "downloads"

# 简化备份目录名
backup_dir_template = "backup_{timestamp}"
```

### 2. 版本检测配置 `[version_detection]`

控制如何识别有效的版本目录。

```toml
[version_detection]
# 版本号必须包含数字
require_digits = true

# 黑名单正则表达式列表
blacklist_patterns = [
    "^config$",           # 配置目录
    "^\\..*",             # 隐藏目录
    "^current$",          # current 链接
    # ... 更多规则
]
```

**作用：**
- ✅ 防止误删 `config`、`.uv` 等非版本目录
- ✅ 确保只识别真正的版本号（如 `1.2.3`）
- ✅ 支持自定义规则

**自定义规则示例：**
```toml
blacklist_patterns = [
    # 默认规则
    "^config$",
    "^\\..*",
    
    # 排除特定版本
    ".*-alpha$",          # 所有 alpha 版本
    ".*-beta$",           # 所有 beta 版本
    "^nightly-.*",        # 所有 nightly 构建
    
    # 排除特定应用的目录
    "^(assets|resources|plugins)$",
    
    # 排除特定日期格式
    "^\\d{4}-\\d{2}-\\d{2}$",  # YYYY-MM-DD 格式
]
```

### 3. 缓存清理配置 `[cache_cleanup]`

控制缓存清理子命令（list/backup/delete）的行为。

```toml
[cache_cleanup]
# 显示详细的包信息表格
show_detailed_table = true

# 列表中最多显示的包数量（0=不限制）
max_list_items = 0

# 备份时创建时间戳子目录
use_timestamp_backup = true

# 删除前预览显示的文件数量
preview_count = 10
```

**应用命令：**
- `scoolp clean list` - 列出过期包
- `scoolp clean backup` - 备份过期包
- `scoolp clean delete` - 删除过期包

**自定义示例：**
```toml
[cache_cleanup]
# 只显示简单列表
show_detailed_table = false

# 限制显示前 20 个
max_list_items = 20

# 不使用时间戳（固定目录名）
use_timestamp_backup = false

# 预览前 5 个文件
preview_count = 5
```

### 4. 显示配置 `[display]`

控制终端输出的外观。

```toml
[display]
# 版本清理时显示的条目数量
version_display_limit = 30

# 使用彩色输出
use_colors = true

# 显示进度条
show_progress = true

# 表格样式
table_style = "rounded"
```

**表格样式选项：**
- `"simple"` - 简单线条
- `"grid"` - 网格样式
- `"rounded"` - 圆角边框（默认）
- `"heavy"` - 粗线条
- `"double"` - 双线条

**应用场景：**
```toml
# 日志记录模式（纯文本）
use_colors = false
show_progress = false
table_style = "simple"

# 炫酷模式（全功能）
use_colors = true
show_progress = true
table_style = "rounded"

# 显示更多条目
version_display_limit = 50
```

### 5. 行为配置 `[behavior]`

控制工具的行为和安全机制。

```toml
[behavior]
# 删除前需要确认
confirm_before_delete = true

# 备份前需要确认
confirm_before_backup = false

# 使用回收站
use_recycle_bin = true

# 遇到错误继续
continue_on_error = true
```

**安全级别配置：**

**高安全（默认）：**
```toml
confirm_before_delete = true
confirm_before_backup = true
use_recycle_bin = true
continue_on_error = false
```

**快速模式（谨慎使用）：**
```toml
confirm_before_delete = false
confirm_before_backup = false
use_recycle_bin = true
continue_on_error = true
```

**自动化模式（脚本使用）：**
```toml
confirm_before_delete = false
confirm_before_backup = false
use_recycle_bin = true
continue_on_error = true
```

### 6. 过滤配置 `[filters]`

控制哪些包和版本会被排除。

```toml
[filters]
# 排除的包名模式（正则表达式）
excluded_packages = []

# 排除的版本模式（正则表达式）
excluded_versions = []

# 最小文件大小（字节）
min_file_size = 0
```

**实用示例：**

**排除开发工具：**
```toml
excluded_packages = [
    "^python.*",          # 所有 Python 包
    "^nodejs.*",          # 所有 Node.js 包
    "^rust.*",            # 所有 Rust 包
    "^vscode$",           # VS Code
]
```

**只清理大文件：**
```toml
# 只显示大于 10MB 的文件
min_file_size = 10485760

# 只显示大于 100MB 的文件
min_file_size = 104857600
```

**排除特定版本：**
```toml
excluded_versions = [
    ".*-lts$",            # LTS 版本
    ".*-stable$",         # 稳定版本
    "^1\\..*",            # 所有 1.x 版本
]
```

### 7. 性能配置 `[performance]`

控制扫描性能和资源使用。

```toml
[performance]
# 默认跳过大小计算
skip_size_calculation = false

# 最大线程数（0=自动）
max_workers = 0
```

**性能调优：**

**快速扫描（推荐）：**
```toml
skip_size_calculation = true
max_workers = 4
```

**完整信息：**
```toml
skip_size_calculation = false
max_workers = 1
```

**高性能（多核 CPU）：**
```toml
skip_size_calculation = true
max_workers = 8
```

## 实战配置示例

### 场景 1：首次使用（保守配置）

```toml
[version_detection]
require_digits = true
blacklist_patterns = [
    "^config$", "^\\..*", "^current$", "^persist$",
    "^cache$", "^data$", "^logs?$", "^temp$", "^backup$",
    ".*\\.old$",
]

[behavior]
confirm_before_delete = true
confirm_before_backup = true
use_recycle_bin = true
continue_on_error = false

[display]
version_display_limit = 30
use_colors = true
show_progress = true
```

### 场景 2：自动化脚本（快速模式）

```toml
[paths]
scoop_root = "D:/scoop"

[behavior]
confirm_before_delete = false
use_recycle_bin = true
continue_on_error = true

[performance]
skip_size_calculation = true
max_workers = 4

[display]
use_colors = false
show_progress = false
```

### 场景 3：开发环境（排除开发工具）

```toml
[filters]
excluded_packages = [
    "^python.*",
    "^nodejs.*",
    "^rust.*",
    "^go$",
    "^java.*",
    "^vscode$",
]

[display]
version_display_limit = 50

[cache_cleanup]
preview_count = 20
```

### 场景 4：定期维护（只清理大文件）

```toml
[filters]
min_file_size = 52428800  # 50 MB

[cache_cleanup]
max_list_items = 100

[behavior]
confirm_before_delete = true
use_recycle_bin = true

[performance]
skip_size_calculation = false  # 需要显示大小
```

## 配置验证

测试配置是否正确：

```bash
# 1. 列出配置（不实际操作）
scoolp clean version --no-size

# 2. 预览模式
scoolp clean version -a delete --dry-run --no-size

# 3. 检查路径
scoolp clean list
```

## 常见配置问题

### Q: 配置文件不生效？

A: 检查以下几点：
1. 文件名是否正确：`clean_config.toml`
2. 文件位置是否正确：`src/scoolp/clean_config.toml`
3. TOML 语法是否正确（使用 `tomli` 验证）
4. 重新安装：`uv pip install -e . --reinstall`

### Q: 正则表达式不工作？

A: 常见错误：
```toml
# 错误：忘记转义
"^test."  # 匹配 "test" 后跟任意字符

# 正确：转义点号
"^test\\."  # 匹配 "test."

# 错误：忘记锚点
"config"  # 匹配包含 "config" 的任何字符串

# 正确：使用锚点
"^config$"  # 精确匹配 "config"
```

### Q: 为什么有些配置项不起作用？

A: 命令行参数优先级更高：
```bash
# 配置: confirm_before_delete = true
# 但使用了 --force 参数，会跳过确认
scoolp clean delete --force
```

## 配置最佳实践

1. **备份配置文件**：修改前先备份
2. **逐步调整**：每次只改一个配置项
3. **测试验证**：使用 `--dry-run` 测试
4. **添加注释**：记录配置原因
5. **版本控制**：将配置文件纳入 Git

## 配置模板

复制 `clean_config_example.toml` 开始：

```bash
cd src/scoolp
cp clean_config_example.toml clean_config.toml
# 编辑 clean_config.toml
```

## 相关文档

- [CLEAN_VERSION_GUIDE.md](CLEAN_VERSION_GUIDE.md) - 版本清理指南
- [README.md](README.md) - 总体说明
- `clean_config_example.toml` - 配置示例

## 更新日志

### v1.1 (2025-10-24)

- ✅ 统一配置文件（所有子命令共享）
- ✅ 新增路径配置支持
- ✅ 新增缓存清理专用配置
- ✅ 新增显示配置支持
- ✅ 新增过滤配置支持
- ✅ 新增性能配置支持
- ✅ 完整的配置文档和示例


