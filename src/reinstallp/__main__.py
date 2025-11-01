#!/usr/bin/env python3
"""
递归查找带有pyproject.toml的文件夹并重新安装可编辑包
"""
import os
import subprocess
import sys
import shutil
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

def install_package(project_path: Path, use_system: bool = True) -> bool:
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
            if not use_system:
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
    
    # 选择安装方式
    console.print("\n[bold cyan]请选择安装方式：[/bold cyan]")
    console.print("[dim]1. 全局安装 (--system) - 安装到系统Python环境[/dim]")
    console.print("[dim]2. 局部安装 (无--system) - 安装到当前虚拟环境[/dim]")
    
    install_choice = Prompt.ask(
        "[bold green]请选择安装方式[/bold green]",
        choices=["1", "2"],
        default="1"
    )
    
    use_system = install_choice == "1"
    install_type = "全局安装" if use_system else "局部安装"
    
    console.print(f"[cyan]选择的安装方式: {install_type}[/cyan]")
    
    # 确认是否继续
    if not Confirm.ask(f"\n[bold yellow]是否继续{install_type}所有项目？[/bold yellow]", default=True):
        console.print("[yellow]取消安装[/yellow]")
        return
      # 安装所有项目
    successful_installs = 0
    failed_installs = 0
    
    for i, project in enumerate(projects, 1):
        console.print(f"[cyan]({i}/{len(projects)})[/cyan]")
        if install_package(project, use_system):
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
