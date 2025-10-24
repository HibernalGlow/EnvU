# Scoop 旧版本清理指南

## 功能概述

`scoolp clean version` 命令用于识别和清理 Scoop 应用的旧版本目录，释放磁盘空间。

## 核心特性

### 🎯 智能版本检测

1. **数字识别**：只有包含数字的目录才会被识别为版本目录
   - ✅ `1.2.3`, `2024-01-01`, `v1.0.0` 等包含数字的目录
   - ❌ `config`, `data`, `download` 等不含数字的目录

2. **黑名单过滤**：自动排除特定模式的目录
   - `config` - 配置目录
   - `.uv`, `.git` 等隐藏目录（以 `.` 开头）
   - `current` - 当前版本的符号链接
   - `persist` - Scoop 持久化数据
   - `cache`, `data`, `logs`, `temp`, `backup` 等系统目录
   - `*.old` - 已标记为旧版本的目录

3. **当前版本识别**：自动解析 `current` 目录指向的实际版本

### 🛡️ 安全机制

1. **回收站删除**：所有删除操作移至回收站，可随时恢复
2. **预览模式**：`--dry-run` 查看将要执行的操作而不实际修改
3. **确认提示**：删除前需要用户确认（除非使用 `--force`）

### ⚙️ 配置文件

通过 `clean_config.toml` 自定义行为：

```toml
[version_detection]
# 版本目录必须包含数字
require_digits = true

# 黑名单正则表达式
blacklist_patterns = [
    "^config$",        # 配置目录
    "^\\..*",          # 隐藏目录
    "^current$",       # current 链接
    # 添加自定义规则...
]

[behavior]
# 显示条目数量
display_limit = 30

# 删除前确认
confirm_before_delete = true
```

## 使用方法

### 基本命令

```bash
# 快速列出（推荐首次使用）
scoolp clean version --no-size

# 列出旧版本（包含大小信息）
scoolp clean version

# 预览重命名操作
scoolp clean version -a rename --dry-run --no-size

# 重命名为 .old 后缀
scoolp clean version -a rename

# 移至回收站（安全）
scoolp clean version -a delete
```

### 高级选项

```bash
# 指定 Scoop 根目录
scoolp clean version --root D:/scoop

# 快速扫描（跳过大小计算）
scoolp clean version --no-size

# 预览模式（不实际修改）
scoolp clean version -a delete --dry-run
```

## 工作原理

### 扫描流程

1. 读取 `D:\scoop\apps\` 下的所有应用目录
2. 对每个应用：
   - 检查是否存在 `current` 目录
   - 解析 `current` 指向的实际版本
   - 遍历所有子目录
   - 应用版本检测规则（数字检测 + 黑名单过滤）
   - 识别非当前版本的目录为"旧版本"

### 版本检测规则

```python
# 1. 黑名单过滤
if matches_blacklist(dir_name):
    return False  # 跳过

# 2. 数字检测
if require_digits and not contains_digit(dir_name):
    return False  # 跳过

# 3. 通过检测
return True  # 是有效的版本目录
```

### 示例说明

以 `D:\scoop\apps\vscode\` 为例：

```
vscode/
├── current -> 1.105.0     ← 当前版本（符号链接）
├── 1.102.3/               ← ✅ 旧版本（包含数字，非 current）
├── 1.103.0/               ← ✅ 旧版本
├── 1.105.0/               ← ❌ 当前版本（current 指向）
├── config/                ← ❌ 配置目录（无数字）
└── persist/               ← ❌ 持久化目录（无数字）
```

识别结果：
- **旧版本**：`1.102.3`, `1.103.0`
- **保留**：`1.105.0` (当前), `config`, `persist`

## 自定义配置

### 添加自定义黑名单

编辑 `src/scoolp/clean_config.toml`：

```toml
[version_detection]
blacklist_patterns = [
    # 默认规则
    "^config$",
    "^\\..*",
    
    # 自定义规则
    "^test.*",           # 所有 test 开头的目录
    ".*_backup$",        # 所有 _backup 结尾的目录
    "^(assets|resources)$",  # assets 或 resources
]
```

### 修改显示限制

```toml
[behavior]
display_limit = 50  # 显示前 50 个结果
```

## 实战案例

### 案例 1：首次清理

```bash
# 1. 快速扫描，查看有多少旧版本
scoolp clean version --no-size

# 输出示例：
# 发现 1 个旧版本 (共 1 个应用)
# ├── rubick: 4.3.5 (当前: 4.3.2)

# 2. 预览删除操作
scoolp clean version -a delete --dry-run --no-size

# 3. 确认无误后执行
scoolp clean version -a delete
```

### 案例 2：保守清理（重命名）

```bash
# 重命名旧版本为 .old（不删除）
scoolp clean version -a rename

# 结果：
# rubick/4.3.5/ → rubick/4.3.5.old/
```

### 案例 3：批量清理大量应用

```bash
# 1. 完整扫描（包含大小）
scoolp clean version

# 输出示例：
# 发现 222 个旧版本 (共 85 个应用)
# 可节省空间: 15.2 GB

# 2. 移至回收站
scoolp clean version -a delete

# 3. 检查回收站，确认无误后清空
```

## 常见问题

### Q: 为什么有些目录没有被检测为旧版本？

A: 可能原因：
1. 目录名不包含数字（如 `config`, `download`）
2. 匹配黑名单规则（如 `.uv`, `persist`）
3. 是当前版本（`current` 指向）
4. 已标记为 `.old`

### Q: 误删了文件怎么办？

A: 所有删除操作都移至回收站：
1. 打开回收站
2. 搜索应用名称
3. 右键恢复

### Q: 如何排除特定应用？

A: 目前不支持按应用排除，但可以通过黑名单规则排除特定版本模式。

### Q: 删除后为什么空间没有立即释放？

A: 文件被移至回收站，需要清空回收站才能真正释放空间：
1. 右键点击桌面回收站
2. 选择"清空回收站"

## 性能优化

### 快速扫描模式

使用 `--no-size` 跳过大小计算，大幅提升速度：

```bash
# 慢（计算每个文件大小）
scoolp clean version

# 快（跳过大小计算）
scoolp clean version --no-size
```

**速度对比**：
- 带大小计算：~30 秒（240 个应用）
- 不计算大小：~5 秒（240 个应用）

## 技术细节

### 依赖库

- `send2trash`：跨平台回收站操作
- `tomllib/tomli`：TOML 配置文件解析
- `rich`：美化终端输出
- `typer`：CLI 框架

### 兼容性

- Python 3.11+（使用内置 `tomllib`）
- Python 3.8-3.10（需要 `tomli` 库）
- Windows/Linux/macOS

### 版本号识别逻辑

```python
def is_valid_version_dir(dir_name: str, config: Dict) -> bool:
    # 1. 检查黑名单
    for pattern in blacklist_patterns:
        if re.match(pattern, dir_name):
            return False
    
    # 2. 检查是否包含数字
    if require_digits:
        if not any(c.isdigit() for c in dir_name):
            return False
    
    return True
```

## 最佳实践

1. **首次使用先预览**：`scoolp clean version --no-size`
2. **重要应用先重命名**：`-a rename` 而不是直接删除
3. **定期清理**：每月运行一次，保持系统整洁
4. **清空回收站**：确认无误后清空以释放空间
5. **备份配置**：修改黑名单前备份配置文件

## 配置文件位置

- **配置文件**：`LazyCommand/EnvU/src/scoolp/clean_config.toml`
- **示例文件**：`LazyCommand/EnvU/src/scoolp/clean_config_example.toml`

## 更新日志

### v1.0 (2025-10-24)

- ✅ 智能版本识别（必须包含数字）
- ✅ 黑名单正则过滤
- ✅ TOML 配置文件支持
- ✅ 回收站安全删除
- ✅ 预览模式
- ✅ 快速扫描模式

## 反馈与建议

如有问题或建议，请通过以下方式反馈：
- 查看详细日志定位问题
- 检查配置文件是否正确
- 确认 Python 版本兼容性

