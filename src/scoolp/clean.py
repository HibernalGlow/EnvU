#!/usr/bin/env python3
"""
Scoop 缓存清理模块
复刻自 scoop-cache-cleaner
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Tuple
from datetime import datetime
from enum import Enum

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()
app = typer.Typer(help="清理 Scoop 缓存中的过期安装包")


class ActionType(Enum):
    """操作类型"""
    LIST = "list"
    BACKUP = "backup"
    DELETE = "delete"


@dataclass
class PackageInfo:
    """包信息"""
    name: str
    version: str
    size: int
    filename: str


@dataclass
class CleanResult:
    """清理结果"""
    file_count: int = 0
    clean_count: int = 0
    clean_size: int = 0
    software_count: int = 0
    scoop_path: str = ""
    backup_path: str = ""
    action: ActionType = ActionType.LIST
    clean_packages: List[PackageInfo] = None

    def __post_init__(self):
        if self.clean_packages is None:
            self.clean_packages = []


def format_size(size: int) -> str:
    """格式化文件大小"""
    kb = 1024
    mb = kb * kb
    gb = mb * kb
    tb = gb * kb

    if size < kb:
        return f"{size:.0f} bytes"
    elif size < mb:
        return f"{size / kb:.2f} KB"
    elif size < gb:
        return f"{size / mb:.2f} MB"
    elif size < tb:
        return f"{size / gb:.2f} GB"
    else:
        return f"{size / tb:.2f} TB"


def get_scoop_cache_path(path: Optional[str] = None) -> Path:
    """获取 Scoop 缓存路径"""
    if path:
        cache_path = Path(path)
    else:
        scoop = os.environ.get("SCOOP")
        if not scoop:
            console.print("[red]错误: 环境变量 SCOOP 未设置[/red]")
            raise typer.Exit(code=1)
        cache_path = Path(scoop) / "cache"

    if not cache_path.exists():
        console.print(f"[red]错误: Scoop 缓存路径不存在: {cache_path}[/red]")
        raise typer.Exit(code=1)

    return cache_path


def parse_package_filename(filename: str) -> Optional[Tuple[str, str]]:
    """
    解析包文件名
    Scoop 安装文件格式: name#version#other-information
    """
    parts = filename.split("#")
    if len(parts) != 3:
        return None
    return parts[0], parts[1]


def find_obsolete_packages(cache_path: Path, action: ActionType) -> CleanResult:
    """查找过期的包"""
    result = CleanResult(
        scoop_path=str(cache_path),
        action=action
    )

    # 获取所有文件
    files = []
    for entry in cache_path.iterdir():
        if entry.is_file():
            files.append(entry)

    # 按文件名排序
    files.sort(key=lambda x: x.name)

    result.file_count = len(files)
    newest_packages = {}  # {name: version}

    # 倒序处理文件，第一个遇到的就是最新版本
    for file_path in reversed(files):
        package_info = parse_package_filename(file_path.name)
        
        if not package_info:
            continue

        name, version = package_info

        if name not in newest_packages:
            # 这是该软件的最新版本
            newest_packages[name] = version
            result.software_count += 1
        elif newest_packages[name] != version:
            # 这是旧版本
            size = file_path.stat().st_size
            result.clean_count += 1
            result.clean_size += size
            result.clean_packages.append(
                PackageInfo(
                    name=name,
                    version=version,
                    size=size,
                    filename=file_path.name
                )
            )

    # 排序清理列表
    result.clean_packages.sort(key=lambda x: (x.name.lower(), x.version.lower()))

    return result


def prepare_backup_path(scoop_path: Path) -> Path:
    """准备备份路径"""
    timestamp = datetime.now().strftime("bak_%Y-%m-%dT%H-%M-%S")
    backup_path = scoop_path / timestamp

    if not backup_path.exists():
        backup_path.mkdir(parents=True, exist_ok=True)

    return backup_path


def clean_cache(result: CleanResult) -> None:
    """清理缓存"""
    if result.clean_count == 0:
        console.print("[yellow]没有需要清理的过期包[/yellow]")
        return

    scoop_path = Path(result.scoop_path)

    if result.action == ActionType.LIST:
        # 只列出，不做任何操作
        for pkg in result.clean_packages:
            pass  # 已经在外部显示了

    elif result.action == ActionType.BACKUP:
        # 备份到指定目录
        backup_path = prepare_backup_path(scoop_path)
        result.backup_path = str(backup_path)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[green]备份文件中...", total=len(result.clean_packages))

            for pkg in result.clean_packages:
                old_path = scoop_path / pkg.filename
                new_path = backup_path / pkg.filename

                if old_path.exists():
                    old_path.rename(new_path)
                    console.print(f"[dim]备份: {pkg.name} {pkg.version} ({format_size(pkg.size)})[/dim]")

                progress.advance(task)

        console.print(f"\n[green]✓ 已备份到: {backup_path}[/green]")

    elif result.action == ActionType.DELETE:
        # 直接删除
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[red]删除文件中...", total=len(result.clean_packages))

            for pkg in result.clean_packages:
                file_path = scoop_path / pkg.filename

                if file_path.exists():
                    file_path.unlink()
                    console.print(f"[dim]删除: {pkg.name} {pkg.version} ({format_size(pkg.size)})[/dim]")

                progress.advance(task)

        console.print(f"\n[green]✓ 已删除 {result.clean_count} 个过期文件[/green]")


def show_clean_result(result: CleanResult) -> None:
    """显示清理结果"""
    # 如果是列表模式，显示详细的包信息
    if result.action == ActionType.LIST and result.clean_packages:
        table = Table(title="过期安装包列表", show_header=True)
        table.add_column("序号", style="cyan", justify="right", width=5)
        table.add_column("包名", style="green", width=30)
        table.add_column("版本", style="yellow", width=20)
        table.add_column("大小", style="white", justify="right", width=12)

        for i, pkg in enumerate(result.clean_packages, 1):
            table.add_row(
                str(i),
                pkg.name,
                pkg.version,
                format_size(pkg.size)
            )

        console.print(table)

    # 显示统计信息
    stats = f"""
文件总数         : {result.file_count}
软件总数         : {result.software_count}
过期包数量       : {result.clean_count}
过期包总大小     : {format_size(result.clean_size)}
"""

    panel = Panel.fit(
        stats.strip(),
        title="📊 统计信息",
        border_style="blue"
    )
    console.print(panel)


@app.command("list")
def list_obsolete(
    path: Optional[str] = typer.Argument(
        None, 
        help="Scoop 缓存路径 (默认使用 $SCOOP/cache)"
    ),
):
    """列出所有过期的安装包"""
    cache_path = get_scoop_cache_path(path)
    
    console.print(f"[bold blue]扫描缓存目录: {cache_path}[/bold blue]\n")
    
    result = find_obsolete_packages(cache_path, ActionType.LIST)
    show_clean_result(result)


@app.command("backup")
def backup_obsolete(
    path: Optional[str] = typer.Argument(
        None,
        help="Scoop 缓存路径 (默认使用 $SCOOP/cache)"
    ),
):
    """备份所有过期的安装包到时间戳目录"""
    cache_path = get_scoop_cache_path(path)
    
    console.print(f"[bold blue]扫描并备份缓存目录: {cache_path}[/bold blue]\n")
    
    result = find_obsolete_packages(cache_path, ActionType.BACKUP)
    
    if result.clean_count > 0:
        console.print(f"[yellow]找到 {result.clean_count} 个过期包，总大小 {format_size(result.clean_size)}[/yellow]")
        clean_cache(result)
    
    show_clean_result(result)


@app.command("delete")
def delete_obsolete(
    path: Optional[str] = typer.Argument(
        None,
        help="Scoop 缓存路径 (默认使用 $SCOOP/cache)"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="跳过确认直接删除"
    ),
):
    """删除所有过期的安装包"""
    cache_path = get_scoop_cache_path(path)
    
    console.print(f"[bold blue]扫描缓存目录: {cache_path}[/bold blue]\n")
    
    result = find_obsolete_packages(cache_path, ActionType.DELETE)
    
    if result.clean_count == 0:
        console.print("[green]没有需要清理的过期包[/green]")
        return
    
    console.print(f"[yellow]找到 {result.clean_count} 个过期包，总大小 {format_size(result.clean_size)}[/yellow]\n")
    
    # 显示前10个要删除的文件
    preview_count = min(10, len(result.clean_packages))
    console.print("[dim]将删除以下文件 (前10个):[/dim]")
    for pkg in result.clean_packages[:preview_count]:
        console.print(f"  [dim]• {pkg.name} {pkg.version} ({format_size(pkg.size)})[/dim]")
    
    if len(result.clean_packages) > preview_count:
        console.print(f"  [dim]... 还有 {len(result.clean_packages) - preview_count} 个文件[/dim]")
    
    # 确认删除
    if not force:
        confirm = typer.confirm(
            f"\n确定要删除这 {result.clean_count} 个文件吗？",
            default=False
        )
        if not confirm:
            console.print("[yellow]已取消操作[/yellow]")
            raise typer.Exit()
    
    clean_cache(result)
    show_clean_result(result)


@app.callback(invoke_without_command=True)
def clean_main(ctx: typer.Context):
    """
    清理 Scoop 缓存中的过期安装包
    
    默认行为: 列出过期包
    """
    if ctx.invoked_subcommand is None:
        # 默认执行 list
        list_obsolete()


if __name__ == "__main__":
    app()

