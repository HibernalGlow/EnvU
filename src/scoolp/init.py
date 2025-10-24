#!/usr/bin/env python3
"""
Scoop 初次安装模块
用于安装和初始化 Scoop
"""

import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

console = Console()
app = typer.Typer(help="初始化和安装 Scoop")


def run_powershell(script: str, check: bool = True) -> subprocess.CompletedProcess:
    """运行 PowerShell 脚本"""
    cmd = [
        "powershell.exe",
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        script,
    ]
    console.print(f"[dim]> {script[:100]}...[/dim]" if len(script) > 100 else f"[dim]> {script}[/dim]")
    return subprocess.run(cmd, check=check)


@app.command()
def install(
    scoop_dir: Optional[str] = typer.Option(
        None,
        "--dir",
        "-d",
        help="Scoop 安装目录 (默认: C:\\Users\\<用户名>\\scoop)"
    ),
):
    """
    安装 Scoop 到系统
    
    这会下载并安装 Scoop 包管理器
    """
    console.print(Panel.fit(
        "[bold cyan]Scoop 安装向导[/bold cyan]\n\n"
        "这将在您的系统上安装 Scoop 包管理器",
        title="🚀 初始化 Scoop",
        border_style="green"
    ))
    
    # 确认安装
    if not Confirm.ask("是否继续安装 Scoop?", default=True):
        console.print("[yellow]已取消安装[/yellow]")
        raise typer.Exit()
    
    # 设置安装目录
    env_cmds = []
    if scoop_dir:
        env_cmds.append(f"$env:SCOOP='{scoop_dir}'")
        env_cmds.append("[Environment]::SetEnvironmentVariable('SCOOP', $env:SCOOP, 'User')")
        console.print(f"[cyan]设置安装目录: {scoop_dir}[/cyan]")
    
    # 下载并执行安装脚本
    install_script = (
        "; ".join(env_cmds) + "; " if env_cmds else ""
    ) + "irm get.scoop.sh | iex"
    
    console.print("\n[bold green]正在下载并安装 Scoop...[/bold green]")
    
    try:
        result = run_powershell(install_script, check=False)
        
        if result.returncode == 0:
            console.print("\n[green]✓ Scoop 安装成功![/green]")
            console.print("\n[cyan]下一步:[/cyan]")
            console.print("  1. 运行 [bold]scoolp sync[/bold] 同步 buckets")
            console.print("  2. 运行 [bold]scoolp install[/bold] 安装软件包")
        else:
            console.print("\n[red]✗ Scoop 安装失败[/red]")
            console.print("[yellow]请检查网络连接或手动访问 https://scoop.sh 获取帮助[/yellow]")
            raise typer.Exit(code=1)
            
    except Exception as e:
        console.print(f"\n[red]安装过程中发生错误: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def check():
    """检查 Scoop 是否已安装"""
    console.print("[cyan]检查 Scoop 安装状态...[/cyan]\n")
    
    # 检查 scoop 命令是否可用
    result = subprocess.run(
        ["powershell", "-Command", "Get-Command scoop -ErrorAction SilentlyContinue"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        console.print("[green]✓ Scoop 已安装[/green]")
        
        # 获取版本信息
        version_result = subprocess.run(
            ["powershell", "-Command", "scoop --version"],
            capture_output=True,
            text=True
        )
        if version_result.returncode == 0:
            console.print(f"[dim]版本: {version_result.stdout.strip()}[/dim]")
        
        # 获取安装路径
        env_result = subprocess.run(
            ["powershell", "-Command", "$env:SCOOP"],
            capture_output=True,
            text=True
        )
        if env_result.stdout.strip():
            console.print(f"[dim]安装路径: {env_result.stdout.strip()}[/dim]")
            
    else:
        console.print("[yellow]✗ Scoop 未安装[/yellow]")
        console.print("\n运行 [bold]scoolp init install[/bold] 安装 Scoop")


if __name__ == "__main__":
    app()
