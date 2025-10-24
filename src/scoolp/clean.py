#!/usr/bin/env python3
"""
Scoop 缓存清理模块
复刻自 scoop-cache-cleaner
"""

import os
import re
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
from enum import Enum

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from send2trash import send2trash

# 根据 Python 版本导入 tomllib 或 tomli
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

console = Console()
app = typer.Typer(help="清理 Scoop 缓存中的过期安装包")


# 默认配置
DEFAULT_CONFIG = {
    "paths": {
        "scoop_root": "",
        "cache_dir": "cache",
        "backup_dir_template": "cache_backup_{timestamp}",
    },
    "version_detection": {
        "require_digits": True,
        "blacklist_patterns": [
            r"^config$",
            r"^\..*",
            r"^current$",
            r"^persist$",
            r"^cache$",
            r"^data$",
            r"^logs?$",
            r"^temp$",
            r"^backup$",
            r".*\.old$",
        ]
    },
    "cache_cleanup": {
        "show_detailed_table": True,
        "max_list_items": 0,
        "use_timestamp_backup": True,
        "preview_count": 10,
    },
    "display": {
        "version_display_limit": 30,
        "use_colors": True,
        "show_progress": True,
        "table_style": "rounded",
    },
    "behavior": {
        "confirm_before_delete": True,
        "confirm_before_backup": False,
        "use_recycle_bin": True,
        "continue_on_error": True,
    },
    "filters": {
        "excluded_packages": [],
        "excluded_versions": [],
        "min_file_size": 0,
    },
    "performance": {
        "skip_size_calculation": False,
        "max_workers": 0,
    }
}


def load_config() -> Dict[str, Any]:
    """加载配置文件"""
    config_path = Path(__file__).parent / "config.toml"
    
    if not config_path.exists():
        console.print(f"[dim]配置文件不存在，使用默认配置: {config_path}[/dim]")
        return DEFAULT_CONFIG
    
    if tomllib is None:
        console.print("[yellow]警告: 无法导入 tomllib/tomli，使用默认配置[/yellow]")
        return DEFAULT_CONFIG
    
    try:
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
        return config
    except Exception as e:
        console.print(f"[yellow]警告: 加载配置文件失败 ({e})，使用默认配置[/yellow]")
        return DEFAULT_CONFIG


def is_valid_version_dir(dir_name: str, config: Dict[str, Any]) -> bool:
    """
    判断目录是否是有效的版本目录
    
    Args:
        dir_name: 目录名
        config: 配置字典
    
    Returns:
        bool: 是否是有效的版本目录
    """
    # 获取配置
    version_config = config.get("version_detection", {})
    require_digits = version_config.get("require_digits", True)
    blacklist_patterns = version_config.get("blacklist_patterns", [])
    
    # 检查黑名单
    for pattern in blacklist_patterns:
        try:
            if re.match(pattern, dir_name):
                return False
        except re.error as e:
            console.print(f"[yellow]警告: 无效的正则表达式 '{pattern}': {e}[/yellow]")
            continue
    
    # 如果要求包含数字，检查是否包含数字
    if require_digits:
        if not any(c.isdigit() for c in dir_name):
            return False
    
    return True


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


def get_scoop_cache_path(path: Optional[str] = None, config: Optional[Dict[str, Any]] = None) -> Path:
    """获取 Scoop 缓存路径"""
    if path:
        cache_path = Path(path)
    else:
        # 从配置获取
        if config is None:
            config = load_config()
        
        paths_config = config.get("paths", {})
        scoop_root = paths_config.get("scoop_root", "")
        cache_dir = paths_config.get("cache_dir", "cache")
        
        # 优先使用配置的 scoop_root
        if scoop_root:
            cache_path = Path(scoop_root) / cache_dir
        else:
            # 其次使用环境变量
            scoop = os.environ.get("SCOOP")
            if not scoop:
                console.print("[red]错误: 环境变量 SCOOP 未设置[/red]")
                console.print("[yellow]请设置 SCOOP 环境变量、配置文件中的 scoop_root 或使用参数指定路径[/yellow]")
                raise typer.Exit(code=1)
            cache_path = Path(scoop) / cache_dir

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
                    send2trash(str(file_path))
                    console.print(f"[dim]移至回收站: {pkg.name} {pkg.version} ({format_size(pkg.size)})[/dim]")

                progress.advance(task)

        console.print(f"\n[green]> 已移至回收站 {result.clean_count} 个过期文件[/green]")
        console.print(f"[dim]提示: 清空回收站可释放空间[/dim]")


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
    
    if result.action == ActionType.DELETE:
        stats += f"\n[dim]注: 文件已移至回收站，清空回收站可释放空间[/dim]"

    panel = Panel.fit(
        stats.strip(),
        title="统计信息",
        border_style="blue"
    )
    console.print(panel)


@app.command("list")
def list_obsolete(
    path: Optional[str] = typer.Argument(
        None, 
        help="Scoop 缓存路径 (默认使用配置或 $SCOOP/cache)"
    ),
):
    """列出所有过期的安装包"""
    config = load_config()
    cache_path = get_scoop_cache_path(path, config)
    
    console.print(f"[bold blue]扫描缓存目录: {cache_path}[/bold blue]\n")
    
    result = find_obsolete_packages(cache_path, ActionType.LIST)
    show_clean_result(result)


@app.command("backup")
def backup_obsolete(
    path: Optional[str] = typer.Argument(
        None,
        help="Scoop 缓存路径 (默认使用配置或 $SCOOP/cache)"
    ),
):
    """备份所有过期的安装包到时间戳目录"""
    config = load_config()
    cache_path = get_scoop_cache_path(path, config)
    
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
        help="Scoop 缓存路径 (默认使用配置或 $SCOOP/cache)"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="跳过确认直接删除"
    ),
):
    """删除所有过期的安装包（移至回收站）"""
    config = load_config()
    cache_path = get_scoop_cache_path(path, config)
    
    # 从配置获取行为设置
    behavior_config = config.get("behavior", {})
    confirm_needed = behavior_config.get("confirm_before_delete", True) and not force
    
    console.print(f"[bold blue]扫描缓存目录: {cache_path}[/bold blue]\n")
    
    result = find_obsolete_packages(cache_path, ActionType.DELETE)
    
    if result.clean_count == 0:
        console.print("[green]没有需要清理的过期包[/green]")
        return
    
    console.print(f"[yellow]找到 {result.clean_count} 个过期包，总大小 {format_size(result.clean_size)}[/yellow]\n")
    
    # 显示前N个要处理的文件（从配置获取）
    cache_config = config.get("cache_cleanup", {})
    preview_count = min(cache_config.get("preview_count", 10), len(result.clean_packages))
    console.print("[dim]将移至回收站的文件 (前10个):[/dim]")
    for pkg in result.clean_packages[:preview_count]:
        console.print(f"  [dim]- {pkg.name} {pkg.version} ({format_size(pkg.size)})[/dim]")
    
    if len(result.clean_packages) > preview_count:
        console.print(f"  [dim]... 还有 {len(result.clean_packages) - preview_count} 个文件[/dim]")
    
    # 确认操作
    if confirm_needed:
        confirm = typer.confirm(
            f"\n确定要移动这 {result.clean_count} 个文件到回收站吗？",
            default=False
        )
        if not confirm:
            console.print("[yellow]已取消操作[/yellow]")
            raise typer.Exit()
    
    clean_cache(result)
    show_clean_result(result)


@app.command("version")
def clean_versions(
    scoop_root: Optional[str] = typer.Option(
        None,
        "--root",
        "-r",
        help="Scoop 安装根目录 (默认从环境变量 SCOOP 获取)"
    ),
    action: str = typer.Option(
        "list",
        "--action",
        "-a",
        help="操作类型: list(列出), rename(重命名为.old), delete(移至回收站)"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        "-n",
        help="预览模式，不执行实际操作"
    ),
    no_size: bool = typer.Option(
        False,
        "--no-size",
        help="跳过大小计算以加快扫描速度"
    ),
):
    """
    清理 Scoop 应用的旧版本
    
    找到 current 指向的当前版本，处理其他旧版本
    
    示例:
      scoolp clean version                    # 列出旧版本
      scoolp clean version --no-size          # 快速列出（不计算大小）
      scoolp clean version -a rename --dry-run  # 预览重命名操作
      scoolp clean version -a delete          # 移至回收站
    """
    import os
    from pathlib import Path
    
    # 加载配置
    config = load_config()
    
    # 获取 Scoop 根目录
    if scoop_root is None:
        scoop_root = os.environ.get("SCOOP")
        if not scoop_root:
            console.print("[red]错误: 未找到 SCOOP 环境变量，请使用 --root 指定[/red]")
            raise typer.Exit(code=1)
    
    scoop_path = Path(scoop_root)
    apps_path = scoop_path / "apps"
    
    if not apps_path.exists():
        console.print(f"[red]错误: apps 目录不存在: {apps_path}[/red]")
        raise typer.Exit(code=1)
    
    console.print(f"[cyan]扫描 Scoop 应用目录: {apps_path}[/cyan]")
    if no_size:
        console.print("[dim]提示: 已跳过大小计算[/dim]\n")
    
    # 统计信息
    total_apps = 0
    total_old_versions = 0
    total_size_saved = 0
    operations = []
    
    # 先快速统计应用数量
    all_app_dirs = [d for d in apps_path.iterdir() if d.is_dir()]
    
    # 使用进度条扫描所有应用
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True  # 完成后自动清除进度条
    ) as progress:
        scan_task = progress.add_task(
            f"[cyan]正在扫描 {len(all_app_dirs)} 个应用...",
            total=len(all_app_dirs)
        )
        
        for app_dir in sorted(all_app_dirs):
            app_name = app_dir.name
            progress.update(scan_task, description=f"[cyan]扫描: {app_name}")
            
            current_link = app_dir / "current"
            
            # 跳过没有 current 的应用
            if not current_link.exists():
                progress.advance(scan_task)
                continue
            
            # 获取 current 指向的实际版本
            try:
                if current_link.exists():
                    current_version = current_link.resolve().name
                else:
                    progress.advance(scan_task)
                    continue
            except Exception:
                progress.advance(scan_task)
                continue
            
            # 查找所有版本目录
            versions = []
            try:
                for item in app_dir.iterdir():
                    if item.is_dir() and is_valid_version_dir(item.name, config):
                        versions.append(item.name)
            except Exception:
                progress.advance(scan_task)
                continue
            
            # 找出旧版本
            old_versions = [v for v in versions if v != current_version]
            
            if old_versions:
                total_apps += 1
                total_old_versions += len(old_versions)
                
                for old_ver in old_versions:
                    old_path = app_dir / old_ver
                    
                    # 可选：计算大小
                    size = 0
                    if not no_size:
                        try:
                            size = sum(f.stat().st_size for f in old_path.rglob('*') if f.is_file())
                            total_size_saved += size
                        except Exception:
                            size = 0
                    
                    operations.append({
                        'app': app_name,
                        'version': old_ver,
                        'current': current_version,
                        'path': old_path,
                        'size': size
                    })
            
            progress.advance(scan_task)
    
    # 显示结果
    if not operations:
        console.print("[green]> 没有发现需要清理的旧版本[/green]")
        return
    
    # 创建结果表格
    from rich.table import Table
    table = Table(title=f"发现 {total_old_versions} 个旧版本 (共 {total_apps} 个应用)")
    table.add_column("应用", style="cyan", width=20)
    table.add_column("旧版本", style="yellow", width=15)
    table.add_column("当前版本", style="green", width=15)
    
    if not no_size:
        table.add_column("大小", style="white", justify="right", width=12)
    
    # 显示限制（从配置获取）
    display_config = config.get("display", {})
    display_limit = display_config.get("version_display_limit", 30)
    for op in operations[:display_limit]:
        row = [
            op['app'],
            op['version'],
            op['current'],
        ]
        if not no_size:
            row.append(format_size(op['size']))
        table.add_row(*row)
    
    if len(operations) > display_limit:
        remaining = len(operations) - display_limit
        row = [f"... 还有 {remaining} 个", "...", "..."]
        if not no_size:
            row.append("...")
        table.add_row(*row)
    
    console.print(table)
    
    # 统计信息
    console.print(f"\n[bold]统计:[/bold]")
    console.print(f"  应用总数: {total_apps}")
    console.print(f"  旧版本总数: {total_old_versions}")
    if not no_size:
        console.print(f"  可节省空间: {format_size(total_size_saved)}")
    
    # 执行操作
    if action == "list":
        console.print(f"\n[dim]提示:[/dim]")
        console.print(f"[dim]  - 重命名为 .old:   scoolp clean version -a rename[/dim]")
        console.print(f"[dim]  - 预览重命名:       scoolp clean version -a rename --dry-run[/dim]")
        console.print(f"[dim]  - 移至回收站:       scoolp clean version -a delete[/dim]")
        return
    
    # 确认操作
    if dry_run:
        console.print(f"\n[yellow]预览模式: 以下是将要执行的操作（不会实际修改文件）[/yellow]")
    else:
        action_name = "重命名" if action == "rename" else "移至回收站"
        if not typer.confirm(f"\n确定要{action_name} {total_old_versions} 个旧版本吗？"):
            console.print("[yellow]已取消操作[/yellow]")
            return
    
    # 执行操作
    success_count = 0
    error_count = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=False
    ) as progress:
        task = progress.add_task(
            f"[cyan]{'[预览] ' if dry_run else ''}{'重命名' if action == 'rename' else '移至回收站'}旧版本...",
            total=len(operations)
        )
        
        for op in operations:
            old_path = op['path']
            progress.update(task, description=f"[cyan]处理: {op['app']}/{op['version']}")
            
            try:
                if dry_run:
                    # 预览模式：只显示将要执行的操作
                    if action == "rename":
                        new_name = f"{old_path.name}.old"
                        console.print(f"[dim]将重命名:[/dim] {op['app']}/{op['version']} → {new_name}")
                    elif action == "delete":
                        console.print(f"[dim]将移至回收站:[/dim] {op['app']}/{op['version']}")
                else:
                    # 实际执行
                    if action == "rename":
                        new_path = old_path.parent / f"{old_path.name}.old"
                        old_path.rename(new_path)
                        console.print(f"[green]>[/green] 重命名: {op['app']}/{op['version']} → {new_path.name}")
                    elif action == "delete":
                        send2trash(str(old_path))
                        console.print(f"[green]>[/green] 移至回收站: {op['app']}/{op['version']}")
                
                success_count += 1
            except Exception as e:
                console.print(f"[red]x[/red] 失败: {op['app']}/{op['version']}: {e}")
                error_count += 1
            
            progress.advance(task)
    
    # 结果统计
    console.print(f"\n[bold]{'预览' if dry_run else '完成'}:[/bold]")
    if dry_run:
        console.print(f"  预览操作数: [cyan]{success_count}[/cyan]")
        if not no_size and action == "delete":
            console.print(f"  预计释放: {format_size(total_size_saved)}")
            console.print(f"  [dim]注: 文件将移至回收站，不会立即释放空间[/dim]")
    else:
        console.print(f"  成功: [green]{success_count}[/green]")
        if error_count > 0:
            console.print(f"  失败: [red]{error_count}[/red]")
        if not no_size and action == "delete":
            console.print(f"  已移至回收站: {format_size(total_size_saved)}")
            console.print(f"  [dim]提示: 清空回收站可释放空间[/dim]")


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

