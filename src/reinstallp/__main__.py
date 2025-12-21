#!/usr/bin/env python3
"""
递归查找带有pyproject.toml的文件夹并重新安装可编辑包
"""
import os
import re
import subprocess
import sys
import shutil
from pathlib import Path
from typing import List, Dict, Any, Pattern
from dataclasses import dataclass

# 根据 Python 版本导入 tomllib 或 tomli
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

try:
    from rich.console import Console
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
except ImportError:
    print("需要安装rich库: uv pip install rich --system")
    sys.exit(1)

console = Console()

@dataclass
class ExcludeConfig:
    """排除路径配置"""
    patterns: List[str]
    match_mode: str  # "any" 或 "all"
    case_sensitive: bool
    compiled_patterns: List[Pattern]

@dataclass
class SearchConfig:
    """搜索配置"""
    default_root: str
    max_depth: int
    follow_symlinks: bool

@dataclass
class InstallConfig:
    """安装配置"""
    default_mode: str  # "system" 或 "local"
    auto_retry: bool
    recreate_venv_on_failure: bool

@dataclass
class DisplayConfig:
    """显示配置"""
    verbose: bool
    show_progress: bool
    max_display_items: int

@dataclass
class PerformanceConfig:
    """性能配置"""
    max_concurrent_installs: int
    search_timeout: int

@dataclass
class ReinstallpConfig:
    """reinstallp 完整配置"""
    exclude: ExcludeConfig
    search: SearchConfig
    install: InstallConfig
    display: DisplayConfig
    performance: PerformanceConfig

# 默认配置
DEFAULT_CONFIG = ReinstallpConfig(
    exclude=ExcludeConfig(
        patterns=[
            r"^\.venv$",
            r"^venv$",
            r"^\.env$",
            r"__pycache__",
            r"^\.git$",
            r"node_modules",
            r"^\.pytest_cache$",
            r"^\.mypy_cache$",
            r"\.egg-info",
            r"build",
            r"dist",
            r"\.tox",
            r"^\..*",
            r".*test.*",
            r".*temp.*",
        ],
        match_mode="any",
        case_sensitive=False,
        compiled_patterns=[]
    ),
    search=SearchConfig(
        default_root="d:\\1VSCODE\\Projects",
        max_depth=0,
        follow_symlinks=False
    ),
    install=InstallConfig(
        default_mode="system",
        auto_retry=True,
        recreate_venv_on_failure=True
    ),
    display=DisplayConfig(
        verbose=True,
        show_progress=True,
        max_display_items=0
    ),
    performance=PerformanceConfig(
        max_concurrent_installs=0,
        search_timeout=0
    )
)

def load_config() -> ReinstallpConfig:
    """加载配置文件"""
    config_path = Path(__file__).parent / "config.toml"
    
    if not config_path.exists():
        console.print(f"[dim]配置文件不存在，使用默认配置: {config_path}[/dim]")
        return DEFAULT_CONFIG
    
    if tomllib is None:
        console.print("[yellow]警告: 无法导入 tomllib/tomli，使用默认配置[/yellow]")
        return DEFAULT_CONFIG
    
    try:
        with open(config_path, 'rb') as f:
            config_dict = tomllib.load(f)
        
        # 解析排除配置
        exclude_dict = config_dict.get('exclude', {})
        exclude_patterns = exclude_dict.get('patterns', DEFAULT_CONFIG.exclude.patterns)
        match_mode = exclude_dict.get('match_mode', DEFAULT_CONFIG.exclude.match_mode)
        case_sensitive = exclude_dict.get('case_sensitive', DEFAULT_CONFIG.exclude.case_sensitive)
        
        # 编译正则表达式
        compiled_patterns = []
        for pattern in exclude_patterns:
            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                compiled_patterns.append(re.compile(pattern, flags))
            except re.error as e:
                console.print(f"[yellow]警告: 无效的正则表达式 '{pattern}': {e}[/yellow]")
        
        exclude_config = ExcludeConfig(
            patterns=exclude_patterns,
            match_mode=match_mode,
            case_sensitive=case_sensitive,
            compiled_patterns=compiled_patterns
        )
        
        # 解析搜索配置
        search_dict = config_dict.get('search', {})
        search_config = SearchConfig(
            default_root=search_dict.get('default_root', DEFAULT_CONFIG.search.default_root),
            max_depth=search_dict.get('max_depth', DEFAULT_CONFIG.search.max_depth),
            follow_symlinks=search_dict.get('follow_symlinks', DEFAULT_CONFIG.search.follow_symlinks)
        )
        
        # 解析安装配置
        install_dict = config_dict.get('install', {})
        install_config = InstallConfig(
            default_mode=install_dict.get('default_mode', DEFAULT_CONFIG.install.default_mode),
            auto_retry=install_dict.get('auto_retry', DEFAULT_CONFIG.install.auto_retry),
            recreate_venv_on_failure=install_dict.get('recreate_venv_on_failure', DEFAULT_CONFIG.install.recreate_venv_on_failure)
        )
        
        # 解析显示配置
        display_dict = config_dict.get('display', {})
        display_config = DisplayConfig(
            verbose=display_dict.get('verbose', DEFAULT_CONFIG.display.verbose),
            show_progress=display_dict.get('show_progress', DEFAULT_CONFIG.display.show_progress),
            max_display_items=display_dict.get('max_display_items', DEFAULT_CONFIG.display.max_display_items)
        )
        
        # 解析性能配置
        performance_dict = config_dict.get('performance', {})
        performance_config = PerformanceConfig(
            max_concurrent_installs=performance_dict.get('max_concurrent_installs', DEFAULT_CONFIG.performance.max_concurrent_installs),
            search_timeout=performance_dict.get('search_timeout', DEFAULT_CONFIG.performance.search_timeout)
        )
        
        return ReinstallpConfig(
            exclude=exclude_config,
            search=search_config,
            install=install_config,
            display=display_config,
            performance=performance_config
        )
        
    except Exception as e:
        console.print(f"[yellow]警告: 配置文件加载失败，使用默认配置: {e}[/yellow]")
        return DEFAULT_CONFIG

def should_exclude_path(path: Path, config: ExcludeConfig) -> bool:
    """检查路径是否应该被排除"""
    path_str = str(path)
    
    if config.match_mode == "any":
        # 任何一个模式匹配即排除
        for pattern in config.compiled_patterns:
            if pattern.search(path_str):
                return True
        return False
    elif config.match_mode == "all":
        # 所有模式都匹配才排除
        for pattern in config.compiled_patterns:
            if not pattern.search(path_str):
                return False
        return len(config.compiled_patterns) > 0
    else:
        # 默认使用 any 模式
        for pattern in config.compiled_patterns:
            if pattern.search(path_str):
                return True
        return False

def find_pyproject_folders(root_path: Path, config: ReinstallpConfig) -> List[Path]:
    """递归查找包含pyproject.toml的文件夹"""
    pyproject_folders = []
    
    try:
        for item in root_path.rglob("pyproject.toml"):
            folder = item.parent
            
            # 使用配置中的排除模式检查路径
            if not should_exclude_path(folder, config.exclude) and folder not in pyproject_folders:
                pyproject_folders.append(folder)
                
                if config.display.verbose:
                    console.print(f"[dim]找到项目: {folder}[/dim]")
                    
    except PermissionError as e:
        console.print(f"[yellow]权限错误，跳过: {e}[/yellow]")
    except Exception as e:
        console.print(f"[red]错误: {e}[/red]")
    
    return sorted(pyproject_folders)

def display_projects_table(projects: List[Path]) -> None:
    """显示找到的项目列表"""
    table = Table(title="找到的Python项目 (包含pyproject.toml)")
    table.add_column("序号", style="cyan", no_wrap=True)
    table.add_column("项目路径", style="magenta")
    table.add_column("项目名", style="green")
    
    for i, project in enumerate(projects, 1):
        project_name = project.name
        table.add_row(str(i), str(project), project_name)
    
    console.print(table)

def recreate_venv(project_path: Path) -> bool:
    """删除并重新创建虚拟环境"""
    venv_path = project_path / ".venv"
    
    try:
        # 删除现有的虚拟环境
        if venv_path.exists():
            console.print(f"[yellow]删除现有虚拟环境: {venv_path}[/yellow]")
            shutil.rmtree(venv_path)        # 创建新的虚拟环境
        console.print(f"[blue]创建新的虚拟环境: {venv_path}[/blue]")
        # 直接使用 uv venv 在指定路径创建虚拟环境
        cmd = ["uv", "venv", str(venv_path)]
        console.print(f"[dim]执行命令: {' '.join(cmd)}[/dim]")
        
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True
        )
        # 调试输出
        console.print(f"[yellow]stdout:[/yellow] {result.stdout}")
        console.print(f"[yellow]stderr:[/yellow] {result.stderr}")
        if result.returncode == 0:
            console.print(f"[green]✓ 虚拟环境创建成功[/green]")
            return True
        else:
            console.print(f"[red]✗ 虚拟环境创建失败: {result.stderr}[/red]")
            return False
            
    except Exception as e:
        console.print(f"[red]✗ 虚拟环境操作异常: {e}[/red]")
        return False

def install_package(project_path: Path, config: ReinstallpConfig, use_system: bool = True) -> bool:
    """使用uv pip install -e .安装包"""
    try:
        console.print(f"[blue]正在安装: {project_path}[/blue]")
        
        # 如果是局部安装，先检查并创建虚拟环境
        if not use_system:
            venv_path = project_path / ".venv"
            if not venv_path.exists():
                console.print(f"[yellow]未找到虚拟环境，正在创建...[/yellow]")
                if not recreate_venv(project_path):
                    console.print(f"[red]✗ 虚拟环境创建失败，跳过该项目[/red]")
                    return False
        
        # 构建命令 - 不切换路径的方式
        if use_system:
            cmd = ["uv", "pip", "install", "-e", str(project_path), "--system"]
        else:
            # 局部安装：使用指定虚拟环境
            venv_python = project_path / ".venv" / "Scripts" / "python.exe"
            if venv_python.exists():
                cmd = [str(venv_python), "-m", "pip", "install", "-e", str(project_path)]
            else:
                cmd = ["uv", "pip", "install", "-e", str(project_path)]
        
        console.print(f"[dim]执行命令: {' '.join(cmd)}[/dim]")
        
        # 直接执行命令，显示完整输出
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True
        )
        # 调试输出
        console.print(f"[yellow]stdout:[/yellow] {result.stdout}")
        console.print(f"[yellow]stderr:[/yellow] {result.stderr}")
        # 检查输出中是否包含错误信息
        has_error = False
        if result.stderr:
            if "No virtual environment found" in result.stderr or "error:" in result.stderr:
                has_error = True
        if result.stdout:
            if "No virtual environment found" in result.stdout or "error:" in result.stdout:
                has_error = True
        if result.returncode == 0 and not has_error:
            console.print(f"[green]✓ 成功安装: {project_path.name}[/green]")
            return True
        else:
            if has_error:
                console.print(f"[red]✗ 安装失败: {project_path.name} (检测到错误信息)[/red]")
            else:
                console.print(f"[red]✗ 安装失败: {project_path.name} (返回码: {result.returncode})[/red]")
            # 如果是局部安装失败，尝试重新创建虚拟环境
            if not use_system and config.install.recreate_venv_on_failure:
                console.print(f"[yellow]检测到局部安装失败，尝试重新创建虚拟环境...[/yellow]")
                if recreate_venv(project_path):
                    # 重新尝试安装
                    console.print(f"[blue]重新尝试安装: {project_path.name}[/blue]")
                    
                    # 重新构建命令
                    if use_system:
                        retry_cmd = ["uv", "pip", "install", "-e", str(project_path), "--system"]
                    else:
                        venv_python = project_path / ".venv" / "Scripts" / "python.exe"
                        if venv_python.exists():
                            retry_cmd = [str(venv_python), "-m", "pip", "install", "-e", str(project_path)]
                        else:
                            retry_cmd = ["uv", "pip", "install", "-e", str(project_path)]
                    
                    console.print(f"[dim]执行命令: {' '.join(retry_cmd)}[/dim]")
                    retry_result = subprocess.run(
                        retry_cmd,
                        check=False,
                        capture_output=True,
                        text=True
                    )
                    # 调试输出
                    console.print(f"[yellow]stdout:[/yellow] {retry_result.stdout}")
                    console.print(f"[yellow]stderr:[/yellow] {retry_result.stderr}")
                    # 再次检查输出
                    retry_has_error = False
                    if retry_result.stderr and ("No virtual environment found" in retry_result.stderr or "error:" in retry_result.stderr):
                        retry_has_error = True
                    if retry_result.stdout and ("No virtual environment found" in retry_result.stdout or "error:" in retry_result.stdout):
                        retry_has_error = True
                    if retry_result.returncode == 0 and not retry_has_error:
                        console.print(f"[green]✓ 重试成功安装: {project_path.name}[/green]")
                        return True
                    else:
                        console.print(f"[red]✗ 重试后仍然失败: {project_path.name}[/red]")
                        return False
                else:
                    console.print(f"[red]✗ 虚拟环境重建失败，跳过该项目[/red]")
                    return False
            return False
    except Exception as e:
        console.print(f"[red]✗ 安装异常: {project_path.name} - {e}[/red]")
        return False

def main():
    console.print(Panel.fit(
        "[bold blue]Python可编辑包重新安装工具[/bold blue]\n"
        "此工具会递归查找包含pyproject.toml的文件夹并重新安装为可编辑包",
        title="欢迎"
    ))
    
    # 加载配置
    config = load_config()
    if config.display.verbose:
        console.print(f"[dim]已加载配置文件，排除模式: {len(config.exclude.patterns)} 个[/dim]")
    
    # 获取搜索路径
    while True:
        search_path = Prompt.ask(
            "[bold green]请输入要搜索的根目录路径[/bold green]",
            default=config.search.default_root
        )
        
        path = Path(search_path)
        if path.exists() and path.is_dir():
            break
        else:
            console.print("[red]路径不存在或不是目录，请重新输入[/red]")
    
    # 搜索项目
    with console.status("[bold green]正在搜索项目..."):
        projects = find_pyproject_folders(path, config)
    
    if not projects:
        console.print("[yellow]未找到包含pyproject.toml的项目[/yellow]")
        return
    console.print(f"[green]找到 {len(projects)} 个项目[/green]")
    display_projects_table(projects)
    
    # 选择安装方式
    console.print("\n[bold cyan]请选择安装方式：[/bold cyan]")
    console.print("[dim]1. 全局安装 (--system) - 安装到系统Python环境[/dim]")
    console.print("[dim]2. 局部安装 (无--system) - 安装到当前虚拟环境[/dim]")
    
    default_choice = "1" if config.install.default_mode == "system" else "2"
    install_choice = Prompt.ask(
        "[bold green]请选择安装方式[/bold green]",
        choices=["1", "2"],
        default=default_choice
    )
    
    use_system = install_choice == "1"
    install_type = "全局安装" if use_system else "局部安装"
    
    console.print(f"[cyan]选择的安装方式: {install_type}[/cyan]")
    
    # 确认是否继续
    if not Confirm.ask(f"\n[bold yellow]是否继续{install_type}所有项目？[/bold yellow]", default=True):
        console.print("[yellow]取消安装[/yellow]")
        return
      # 安装所有项目
    install_results = []
    
    for i, project in enumerate(projects, 1):
        console.print(f"[cyan]({i}/{len(projects)})[/cyan]")
        success = install_package(project, config, use_system)
        install_results.append({
            "project": project,
            "name": project.name,
            "path": str(project),
            "status": "成功" if success else "失败"
        })
    
    # 显示安装结果表格
    result_table = Table(title="安装结果详情")
    result_table.add_column("状态", style="", no_wrap=True, width=6)
    result_table.add_column("项目名", style="cyan", no_wrap=True)
    result_table.add_column("路径", style="magenta")
    
    successful_installs = 0
    failed_installs = 0
    
    for result in install_results:
        if result["status"] == "成功":
            result_table.add_row("✅", result["name"], result["path"], style="green")
            successful_installs += 1
        else:
            result_table.add_row("❌", result["name"], result["path"], style="red")
            failed_installs += 1
    
    console.print(result_table)
    
    # 显示统计摘要
    summary_text = Text()
    summary_text.append("安装完成！\n", style="bold")
    summary_text.append(f"成功: {successful_installs} 个项目\n", style="green")
    summary_text.append(f"失败: {failed_installs} 个项目", style="red" if failed_installs > 0 else "green")
    
    console.print(Panel.fit(summary_text, title="安装摘要"))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]用户取消操作[/yellow]")
    except Exception as e:
        console.print(f"\n[red]程序错误: {e}[/red]")
