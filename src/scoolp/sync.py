#!/usr/bin/env python3
"""
Scoop 同步模块
基于 scoop_sync.py
用于同步 buckets 和配置
"""

import os
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Tuple

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()
app = typer.Typer(help="同步 Scoop buckets 和配置")


@dataclass
class SyncOptions:
    """同步选项"""
    remove_all_before_add: bool = True
    reset_core_repo: bool = True
    run_update: bool = True
    set_env: bool = False
    try_fix_ownership: bool = True
    dry_run: bool = False


@dataclass
class SyncConfig:
    """同步配置"""
    root: str = "D:/scoop"
    repo: Optional[str] = None
    buckets: List[Tuple[str, str]] = None
    options: SyncOptions = None

    def __post_init__(self):
        if self.buckets is None:
            self.buckets = []
        if self.options is None:
            self.options = SyncOptions()


def run_command(cmd: List[str], dry_run: bool = False, check: bool = True) -> subprocess.CompletedProcess:
    """运行命令"""
    if dry_run:
        console.print(f"[dim yellow]DRYRUN: {' '.join(cmd)}[/dim yellow]")
        return subprocess.CompletedProcess(cmd, 0, b"", b"")
    
    console.print(f"[dim]> {' '.join(cmd)}[/dim]")
    return subprocess.run(cmd, check=check, capture_output=True, text=True)


def powershell_args(script: str) -> List[str]:
    """构建 PowerShell 命令参数"""
    return [
        "powershell.exe",
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        script,
    ]


def load_config(config_path: Path) -> SyncConfig:
    """加载配置文件"""
    if not config_path.exists():
        console.print(f"[yellow]配置文件不存在: {config_path}[/yellow]")
        console.print("[yellow]使用默认配置[/yellow]")
        return SyncConfig()
    
    try:
        data = tomllib.loads(config_path.read_text(encoding="utf-8"))
        scoop = data.get("scoop", {})
        opts = data.get("options", {})
        buckets = [(b["name"], b.get("url", "")) for b in data.get("bucket", [])]
        
        return SyncConfig(
            root=scoop.get("root", "D:/scoop"),
            repo=scoop.get("repo"),
            buckets=buckets,
            options=SyncOptions(
                remove_all_before_add=opts.get("remove_all_before_add", True),
                reset_core_repo=opts.get("reset_core_repo", True),
                run_update=opts.get("run_update", True),
                set_env=opts.get("set_env", False),
                try_fix_ownership=opts.get("try_fix_ownership", True),
                dry_run=opts.get("dry_run", False),
            ),
        )
    except Exception as e:
        console.print(f"[red]配置文件解析错误: {e}[/red]")
        raise typer.Exit(code=1)


def ensure_git_safe_dirs(root: str, dry_run: bool) -> None:
    """添加 Git safe.directory 配置"""
    console.print("[cyan]配置 Git safe.directory...[/cyan]")
    
    candidates: List[str] = []
    candidates.append(os.path.join(root, "apps", "scoop", "current"))
    
    buckets_dir = os.path.join(root, "buckets")
    if os.path.isdir(buckets_dir):
        for name in os.listdir(buckets_dir):
            p = os.path.join(buckets_dir, name)
            if os.path.isdir(os.path.join(p, ".git")):
                candidates.append(p)
    
    for p in candidates:
        p_slash = p.replace("\\", "/")
        run_command(["git", "config", "--global", "--add", "safe.directory", p_slash], dry_run=dry_run, check=False)


def remove_all_buckets(dry_run: bool) -> None:
    """移除所有已安装的 buckets"""
    console.print("[cyan]移除现有 buckets...[/cyan]")
    
    ps = (
        "$ErrorActionPreference='SilentlyContinue';"
        "$names = scoop bucket list | Select-String -NotMatch '^Name|^----|^$' | ForEach-Object { ($_ -split ' +')[0] } | Sort-Object -Unique;"
        "foreach ($n in $names) { scoop bucket rm $n }"
    )
    run_command(powershell_args(ps), dry_run=dry_run, check=False)


def reset_core_repo(root: str, dry_run: bool) -> None:
    """重置 Scoop core 仓库"""
    console.print("[cyan]重置 Scoop core 仓库...[/cyan]")
    
    core = os.path.join(root, "apps", "scoop", "current")
    if os.path.isdir(os.path.join(core, ".git")):
        run_command(["git", "-C", core, "reset", "--hard", "HEAD"], dry_run=dry_run, check=False)
        run_command(["git", "-C", core, "clean", "-fd"], dry_run=dry_run, check=False)


def add_buckets(buckets: List[Tuple[str, str]], dry_run: bool) -> None:
    """添加 buckets"""
    console.print(f"[cyan]添加 {len(buckets)} 个 buckets...[/cyan]")
    
    for name, url in buckets:
        if url:
            run_command(["scoop", "bucket", "add", name, url], dry_run=dry_run, check=False)
        else:
            run_command(["scoop", "bucket", "add", name], dry_run=dry_run, check=False)


def set_repo_mirror(repo: Optional[str], dry_run: bool) -> None:
    """设置仓库镜像"""
    if repo:
        console.print(f"[cyan]设置仓库镜像: {repo}[/cyan]")
        run_command(["scoop", "config", "SCOOP_REPO", repo], dry_run=dry_run, check=False)


def set_env_scoop(root: str, dry_run: bool) -> None:
    """设置环境变量 SCOOP"""
    console.print(f"[cyan]设置环境变量 SCOOP={root}[/cyan]")
    
    ps = f"[Environment]::SetEnvironmentVariable('SCOOP','{root}','User')"
    run_command(powershell_args(ps), dry_run=dry_run, check=False)


def run_update(dry_run: bool) -> None:
    """运行 scoop update"""
    console.print("[cyan]更新 Scoop...[/cyan]")
    run_command(["scoop", "update"], dry_run=dry_run, check=False)


@app.command()
def sync(
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="配置文件路径 (默认: scoop.toml)"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="预览模式，不执行实际操作"
    ),
):
    """
    同步 Scoop buckets 和配置
    
    根据配置文件同步 buckets、设置镜像源等
    """
    # 确定配置文件路径
    if config is None:
        # 默认从 scoolp 目录查找 scoop.toml
        config = Path(__file__).parent / "scoop.toml"
        if not config.exists():
            # 尝试从项目根目录查找
            config = Path(__file__).parents[2] / "config" / "scoop.toml"
    
    console.print(Panel.fit(
        f"[bold cyan]Scoop 同步工具[/bold cyan]\n\n"
        f"配置文件: {config}\n"
        f"模式: {'预览模式 (不执行)' if dry_run else '执行模式'}",
        title="🔄 同步 Buckets",
        border_style="green"
    ))
    
    # 加载配置
    cfg = load_config(config)
    if dry_run:
        cfg.options.dry_run = True
    
    # 显示配置信息
    console.print(f"\n[bold]配置信息:[/bold]")
    console.print(f"  Scoop 路径: [cyan]{cfg.root}[/cyan]")
    console.print(f"  Buckets 数量: [cyan]{len(cfg.buckets)}[/cyan]")
    if cfg.repo:
        console.print(f"  仓库镜像: [cyan]{cfg.repo}[/cyan]")
    console.print()
    
    # 执行同步步骤
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        task = progress.add_task("[cyan]同步中...", total=None)
        
        # 1. 修复 Git 所有权问题
        if cfg.options.try_fix_ownership:
            ensure_git_safe_dirs(cfg.root, cfg.options.dry_run)
        
        # 2. 移除现有 buckets
        if cfg.options.remove_all_before_add:
            remove_all_buckets(cfg.options.dry_run)
        
        # 3. 重置 core 仓库
        if cfg.options.reset_core_repo:
            reset_core_repo(cfg.root, cfg.options.dry_run)
        
        # 4. 设置环境变量
        if cfg.options.set_env:
            set_env_scoop(cfg.root, cfg.options.dry_run)
        
        # 5. 设置仓库镜像
        set_repo_mirror(cfg.repo, cfg.options.dry_run)
        
        # 6. 添加 buckets
        add_buckets(cfg.buckets, cfg.options.dry_run)
        
        # 7. 更新
        if cfg.options.run_update:
            run_update(cfg.options.dry_run)
        
        progress.update(task, completed=True)
    
    console.print("\n[green]✓ 同步完成![/green]")


@app.command()
def show_config(
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="配置文件路径 (默认: scoop.toml)"
    ),
):
    """显示当前配置"""
    # 确定配置文件路径
    if config is None:
        config = Path(__file__).parent / "scoop.toml"
        if not config.exists():
            config = Path(__file__).parents[2] / "config" / "scoop.toml"
    
    if not config.exists():
        console.print(f"[red]配置文件不存在: {config}[/red]")
        raise typer.Exit(code=1)
    
    # 加载并显示配置
    cfg = load_config(config)
    
    console.print(Panel.fit(
        f"[bold cyan]Scoop 同步配置[/bold cyan]\n\n"
        f"配置文件: {config}",
        title="⚙️ 配置信息",
        border_style="green"
    ))
    
    console.print(f"\n[bold]基本配置:[/bold]")
    console.print(f"  Scoop 路径: [cyan]{cfg.root}[/cyan]")
    if cfg.repo:
        console.print(f"  仓库镜像: [cyan]{cfg.repo}[/cyan]")
    
    console.print(f"\n[bold]Buckets ({len(cfg.buckets)}):[/bold]")
    for name, url in cfg.buckets:
        if url:
            console.print(f"  • [green]{name}[/green]: {url}")
        else:
            console.print(f"  • [green]{name}[/green] (官方)")
    
    console.print(f"\n[bold]选项:[/bold]")
    console.print(f"  移除现有 buckets: [cyan]{cfg.options.remove_all_before_add}[/cyan]")
    console.print(f"  重置 core 仓库: [cyan]{cfg.options.reset_core_repo}[/cyan]")
    console.print(f"  运行更新: [cyan]{cfg.options.run_update}[/cyan]")
    console.print(f"  设置环境变量: [cyan]{cfg.options.set_env}[/cyan]")
    console.print(f"  修复 Git 所有权: [cyan]{cfg.options.try_fix_ownership}[/cyan]")


if __name__ == "__main__":
    app()

