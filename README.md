## owithu：用 TOML 管理“Open with …”右键菜单

本仓库已新增独立包 `owithu`，可用一个 `config/owithu.toml` 统一管理并一键注册/撤销注册表里的“Open with …”菜单项（VSCode、Neeview、PotPlayer）。

### 配置文件
- 路径：`config/owithu.toml`
- 变量：支持 `{scoop_root}` 替换；你也可以扩展更多自定义变量。
- 每个条目字段：
	- `key`：注册表键名（唯一）
	- `label`：右键菜单显示文本
	- `exe`：可执行文件路径（可用变量）
	- `icon`：图标路径（默认同 exe）
	- `args`：传参数组，文件作用域用 `%1`，目录/背景会自动改为 `%V`
	- `scope`：`file`/`directory`/`background` 的任意组合

示例已写在 `config/owithu.toml`。

默认查找顺序：
1. 仓库根 `config/owithu.toml`
2. 当前工作目录 `config/owithu.toml` 或 `owithu.toml`
3. 包内默认 `src/owithu/owithu.toml`（作为回退）

### 使用
在 Windows PowerShell 中，先确保安装依赖（Python 3.11+）：

```powershell
# 可选：在本地虚拟环境或全局安装该包
pip install -e .

# 预览将要注册的条目
owithu preview -c config/owithu.toml

# 注册（默认写入 HKCU\Software\Classes，无需管理员）
owithu register -c config/owithu.toml --hive HKCU

# 撤销全部
owithu unregister -c config/owithu.toml --hive HKCU

# 仅撤销某一项（例如 VSCode）
owithu unregister -c config/owithu.toml --key VSCode
```

说明：
- 默认 `--hive HKCU`，写入当前用户的 `Software\Classes`，不需要管理员权限；也可选择 `HKCR`/`HKLM`（可能需要管理员权限）。
- `directory` 与 `background` 作用域会自动将 `%1` 替换为 `%V`，以匹配原 `.reg` 中的行为。

### 兼容说明
- 该实现依赖标准库 `winreg` 与 `tomllib`，以及第三方库 `rich`（已在 `pyproject.toml` 中声明）。
- 仅在 Windows 有效。

