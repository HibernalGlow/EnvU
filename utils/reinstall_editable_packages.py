#!/usr/bin/env python3
"""
递归查找带有pyproject.toml的文件夹并重新安装可编辑包
"""
import os
import subprocess
import sys
from pathlib import Path
from typing import List

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

def find_pyproject_folders(root_path: Path) -> List[Path]:
    """递归查找包含pyproject.toml的文件夹"""
    pyproject_folders = []
    
    # 要跳过的路径模式
    skip_patterns = [
        ".venv",
        "venv", 
        ".env",
        "__pycache__",
        ".git",
        "node_modules",
        ".pytest_cache",
        ".mypy_cache"
    ]
    
    try:
        for item in root_path.rglob("pyproject.toml"):
            folder = item.parent
            
            # 检查路径中是否包含要跳过的模式
            should_skip = False
            for part in folder.parts:
                if part in skip_patterns:
                    should_skip = True
                    break
            
            if not should_skip and folder not in pyproject_folders:
                pyproject_folders.append(folder)
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

def install_package(project_path: Path) -> bool:
    """使用uv pip install -e . --system安装包"""
    try:
        console.print(f"[blue]正在安装: {project_path}[/blue]")
        console.print(f"[dim]执行命令: uv pip install -e . --system[/dim]")
        
        # 直接执行命令，显示完整输出
        result = subprocess.run(
            ["uv", "pip", "install", "-e", ".", "--system"],
            cwd=project_path,
            check=False
        )
        
        if result.returncode == 0:
            console.print(f"[green]✓ 成功安装: {project_path.name}[/green]")
            return True
        else:
            console.print(f"[red]✗ 安装失败: {project_path.name} (返回码: {result.returncode})[/red]")
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
    
    # 获取搜索路径
    while True:
        search_path = Prompt.ask(
            "[bold green]请输入要搜索的根目录路径[/bold green]",
            default="d:\\1VSCODE\\Projects"
        )
        
        path = Path(search_path)
        if path.exists() and path.is_dir():
            break
        else:
            console.print("[red]路径不存在或不是目录，请重新输入[/red]")
    
    # 搜索项目
    with console.status("[bold green]正在搜索项目..."):
        projects = find_pyproject_folders(path)
    
    if not projects:
        console.print("[yellow]未找到包含pyproject.toml的项目[/yellow]")
        return
    
    console.print(f"[green]找到 {len(projects)} 个项目[/green]")
    display_projects_table(projects)
    
    # 确认是否继续
    if not Confirm.ask("\n[bold yellow]是否继续安装所有项目？[/bold yellow]",default=True):
        console.print("[yellow]取消安装[/yellow]")
        return
      # 安装所有项目
    successful_installs = 0
    failed_installs = 0
    
    for i, project in enumerate(projects, 1):
        console.print(f"[cyan]({i}/{len(projects)})[/cyan]")
        
        if install_package(project):
            successful_installs += 1
        else:
            failed_installs += 1
    
    # 显示安装结果
    result_text = Text()
    result_text.append("安装完成！\n", style="bold")
    result_text.append(f"成功: {successful_installs} 个项目\n", style="green")
    result_text.append(f"失败: {failed_installs} 个项目", style="red" if failed_installs > 0 else "green")
    
    console.print(Panel.fit(result_text, title="安装结果"))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]用户取消操作[/yellow]")
    except Exception as e:
        console.print(f"\n[red]程序错误: {e}[/red]")
