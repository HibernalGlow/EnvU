#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn

# 支持包内导入与脚本直接运行的兜底导入
try:
    from .config import ConfigStore  # type: ignore
    from .symlink_ops import (  # type: ignore
        is_admin as os_is_admin,
        create_symlink as os_create_symlink,
        delete_symlink as os_delete_symlink,
        move_dir_with_skip,
    )
except Exception:  # pragma: no cover - 仅用于开发态脚本运行
    from config import ConfigStore  # type: ignore
    from symlink_ops import (  # type: ignore
        is_admin as os_is_admin,
        create_symlink as os_create_symlink,
        delete_symlink as os_delete_symlink,
        move_dir_with_skip,
    )


console = Console()


class SymlinkManager:
    def __init__(self) -> None:
        self.console = console
        self.config = ConfigStore()  # 默认包目录 linku.toml

    # ---------- 基础 ----------
    def check_admin_privileges(self) -> bool:
        return os_is_admin()

    def _strip_quotes(self, s: str) -> str:
        s = s.strip()
        if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
            return s[1:-1]
        return s

    def validate_path(self, path_str: str, must_exist: bool = True) -> Optional[Path]:
        try:
            path_str = self._strip_quotes(path_str)
            path = Path(path_str).resolve()
            if must_exist and not path.exists():
                self.console.print(f"[red]路径不存在: {path}[/red]")
                return None
            return path
        except Exception as e:
            self.console.print(f"[red]无效路径: {e}[/red]")
            return None

    # ---------- 展示 ----------
    def get_directory_size(self, path: Path) -> tuple[float, int]:
        try:
            total_size = 0
            file_count = 0
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=self.console, transient=True) as progress:
                progress.add_task("正在计算目录大小...", total=None)
                for dirpath, _, filenames in os.walk(path):
                    file_count += len(filenames)
                    for filename in filenames:
                        fp = Path(dirpath) / filename
                        try:
                            total_size += fp.stat().st_size
                        except Exception:
                            pass
            return total_size / (1024 * 1024), file_count
        except Exception as e:
            self.console.print(f"[red]计算目录大小失败: {e}[/red]")
            return 0.0, 0

    def show_path_info(self, path: Path) -> None:
        if not path.exists():
            self.console.print(f"[red]路径不存在: {path}[/red]")
            return

        table = Table(title=f"路径信息: {path}")
        table.add_column("属性", style="cyan")
        table.add_column("值", style="green")
        table.add_row("路径", str(path))
        table.add_row("存在", "是" if path.exists() else "否")
        table.add_row("类型", "目录" if path.is_dir() else "文件" if path.is_file() else "链接" if path.is_symlink() else "未知")
        if path.is_symlink():
            try:
                target = path.readlink()
                table.add_row("链接目标", str(target))
                table.add_row("目标存在", "是" if target.exists() else "否")
            except Exception:
                table.add_row("链接目标", "无法读取")
        if path.exists():
            if path.is_dir():
                size_mb, file_count = self.get_directory_size(path)
                table.add_row("大小", f"{size_mb:.2f} MB")
                table.add_row("文件数量", str(file_count))
            else:
                size_mb = path.stat().st_size / (1024 * 1024)
                table.add_row("大小", f"{size_mb:.2f} MB")
        self.console.print(table)

    # ---------- 业务 ----------
    def create_symlink(self, source: Path, target: Path) -> bool:
        ok, err = os_create_symlink(source, target)
        if ok:
            self.config.record_link(target, source, '目录' if source.is_dir() else '文件')
            return True
        else:
            self.console.print(f"[red]创建软链接失败: {err}[/red]")
            return False

    def move_and_link(self, source: Path, target: Path) -> bool:
        """将源（目录或文件）移动到目标，并在原位置创建软链接。"""
        try:
            if source.is_file():
                # 文件移动
                from shutil import move as sh_move
                target.parent.mkdir(parents=True, exist_ok=True)
                self.console.print(f"[yellow]正在移动文件 {source} 到 {target}...[/yellow]")
                sh_move(str(source), str(target))
                self.console.print("[green]✅ 文件移动成功[/green]")
                self.console.print(f"[yellow]正在创建软链接...[/yellow]")
                return self.create_symlink(target, source)

            # 目录移动（带跳过）
            target.parent.mkdir(parents=True, exist_ok=True)
            self.console.print(f"[yellow]正在移动 {source} 到 {target}...[/yellow]")

            def on_skip(p: Path, e: Exception):
                self.console.print(f"[red]跳过文件 {p}: {e}[/red]")

            ok, moved, total = move_dir_with_skip(source, target, on_skip=on_skip)
            if ok:
                self.console.print(f"[cyan]移动完成: {moved}/{total}[/cyan]")
                self.console.print(f"[yellow]正在创建软链接...[/yellow]")
                return self.create_symlink(target, source)
            else:
                self.console.print("[red]移动过程中遇到太多错误，操作失败[/red]")
                return False
        except Exception as e:
            self.console.print(f"[red]移动失败: {e}[/red]")
            # 尝试回滚
            try:
                if target.exists() and not source.exists():
                    from shutil import move as sh_move
                    sh_move(str(target), str(source))
                    self.console.print("[yellow]已回滚移动操作[/yellow]")
            except Exception:
                pass
            return False

    def show_recorded_links(self):
        links = self.config.get_links()
        if not links:
            self.console.print("[yellow]尚无记录[/yellow]")
            Prompt.ask("按回车继续")
            return
        table = Table(title=f"已记录的链接（{self.config.file_path}）")
        table.add_column("链接路径", style="cyan")
        table.add_column("目标路径", style="green")
        table.add_column("类型", style="magenta")
        table.add_column("创建时间", style="yellow")
        table.add_column("当前状态", style="white")
        for item in links:
            link = Path(item.get('link', ''))
            target = Path(item.get('target', ''))
            kind = item.get('type', '')
            created = item.get('created_at', '')
            status = []
            try:
                link_exists = link.exists()
                status.append('链接存在' if link_exists else '链接缺失')
                if link_exists and link.is_symlink():
                    try:
                        real = link.readlink()
                        status.append('指向OK' if real == target else f'指向异常->{real}')
                    except Exception as e:
                        status.append(f'读取指向失败:{e}')
                else:
                    status.append('非软链接')
                status.append('目标存在' if target.exists() else '目标缺失')
            except Exception as e:
                status.append(f'检测失败:{e}')
            table.add_row(str(link), str(target), kind, created, ' | '.join(status))
        self.console.print(table)
        Prompt.ask("按回车继续")

    def delete_symlink_interactive(self):
        self.console.print("\n[bold cyan]删除软链接（并同步记录）[/bold cyan]")
        link_input = Prompt.ask("请输入要删除的软链接路径")
        link = Path(self._strip_quotes(link_input))

        is_link = False
        try:
            is_link = link.is_symlink()
        except Exception:
            is_link = False

        if not link.exists() and not is_link:
            self.console.print(f"[yellow]路径不存在且不是软链接: {link}[/yellow]")
            if self.config.remove_link_record(link):
                self.console.print("[green]已从记录中移除该链接[/green]")
            else:
                self.console.print("[yellow]记录中也未找到该链接[/yellow]")
            Prompt.ask("按回车继续")
            return

        if not is_link:
            self.console.print(f"[red]该路径不是软链接，已取消删除: {link}[/red]")
            Prompt.ask("按回车继续")
            return

        try:
            try:
                target_info = str(link.readlink())
            except Exception:
                target_info = "(无法读取指向，可能是损坏的链接)"
            self.console.print(f"将删除软链接: [cyan]{link}[/cyan] -> [green]{target_info}[/green]")
        except Exception:
            pass

        if not Confirm.ask("确认删除吗？"):
            self.console.print("[yellow]已取消[/yellow]")
            Prompt.ask("按回车继续")
            return

        ok, err = os_delete_symlink(link)
        if ok:
            self.console.print("[green]✅ 软链接已删除[/green]")
            if self.config.remove_link_record(link):
                self.console.print("[green]✅ 已同步移除记录[/green]")
            else:
                self.console.print("[yellow]记录中未找到该链接或已移除[/yellow]")
        else:
            self.console.print(f"[red]❌ 删除失败: {err}")
        Prompt.ask("按回车继续")

    # ---------- 菜单 ----------
    def create_move_symlink(self):
        self.console.print("\n[bold cyan]创建软链接（移动模式）[/bold cyan]")
        while True:
            source_str = Prompt.ask("请输入源路径（要移动的目录或文件）")
            source = self.validate_path(source_str, must_exist=True)
            if source:
                break
        self.show_path_info(source)
        if not (source.is_dir() or source.is_file()):
            self.console.print("[red]源路径必须是目录或文件[/red]")
            Prompt.ask("按回车继续")
            return
        # 交互输入并解析最终目标
        while True:
            target_str = Prompt.ask("请输入目标路径（移动到的位置，目录或具体文件路径）")
            target_input = self.validate_path(target_str, must_exist=False)
            if not target_input:
                continue
            final_target, err = self.resolve_move_target(source, target_input)
            if err:
                self.console.print(f"[red]{err}[/red]")
                continue
            # 预览与确认
            self.preview_move_result(source, final_target)
            self.console.print(f"\n[yellow]将要执行以下操作:[/yellow]")
            self.console.print(f"1. 移动 [cyan]{source}[/cyan] 到 [cyan]{final_target}[/cyan]")
            self.console.print(f"2. 创建软链接 [cyan]{source}[/cyan] -> [cyan]{final_target}[/cyan]")
            if Confirm.ask("\n确认执行吗？"):
                if self.move_and_link(source, final_target):
                    self.console.print("[green]✅ 软链接创建成功！[/green]")
                else:
                    self.console.print("[red]❌ 软链接创建失败[/red]")
                break
        Prompt.ask("按回车继续")

    def resolve_move_target(self, source: Path, target_input: Path) -> tuple[Path, str | None]:
        """根据源类型与输入目标求最终目标路径。
        目录：目标必须不存在。
        文件：
          - 目标为已存在目录 => 目标/源文件名
          - 目标为已存在文件 => 报错
          - 目标不存在 => 视为最终文件路径
        """
        if source.is_dir():
            if target_input.exists():
                return target_input, f"目标路径已存在: {target_input}"
            return target_input, None
        # 文件
        if target_input.exists():
            if target_input.is_dir():
                final = target_input / source.name
                if final.exists():
                    return final, f"目标文件已存在: {final}"
                return final, None
            else:
                return target_input, f"目标文件已存在: {target_input}"
        return target_input, None

    def preview_move_result(self, source: Path, target: Path, dir_sample: int = 50, file_sample: int = 50) -> None:
        """预览移动后将在目标位置创建的完整路径（目录与文件）。"""
        try:
            if source.is_file():
                panel = Panel.fit(
                    Text(
                        f"将移动文件到: {target}\n并在原位置创建软链接: {source} -> {target}",
                        style="bold yellow",
                    ),
                    title="移动结果预览（文件）",
                    border_style="yellow",
                )
                self.console.print(panel)
                return

            # 目录情况
            dir_paths = []
            file_paths = []
            total_dirs = 0
            total_files = 0
            for root, dirs, files in os.walk(source):
                rel = Path(root).relative_to(source)
                tgt_dir = target / rel
                total_dirs += 1
                if len(dir_paths) < dir_sample:
                    dir_paths.append(str(tgt_dir))
                for d in dirs:
                    sub_dir = tgt_dir / d
                    total_dirs += 1
                    if len(dir_paths) < dir_sample:
                        dir_paths.append(str(sub_dir))
                for f in files:
                    total_files += 1
                    if len(file_paths) < file_sample:
                        file_paths.append(str(tgt_dir / f))

            panel = Panel.fit(
                Text(
                    f"目标根目录: {target}\n目录总数: {total_dirs}，文件总数: {total_files}",
                    style="bold yellow",
                ),
                title="移动结果预览（目录）",
                border_style="yellow",
            )
            self.console.print(panel)

            dir_table = Table(title=f"将创建/出现的目录（示例，最多 {dir_sample} 条）", show_lines=False)
            dir_table.add_column("目录路径", style="cyan")
            for p in dir_paths:
                dir_table.add_row(p)
            if total_dirs > len(dir_paths):
                dir_table.caption = f"... 以及另外 {total_dirs - len(dir_paths)} 个目录"
            self.console.print(dir_table)

            file_table = Table(title=f"将移动到的文件（示例，最多 {file_sample} 条）", show_lines=False)
            file_table.add_column("文件路径", style="green")
            for p in file_paths:
                file_table.add_row(p)
            if total_files > len(file_paths):
                file_table.caption = f"... 以及另外 {total_files - len(file_paths)} 个文件"
            self.console.print(file_table)
        except Exception as e:
            self.console.print(f"[yellow]预览移动结果失败: {e}[/yellow]")

    def create_direct_symlink(self):
        self.console.print("\n[bold cyan]创建软链接（直接模式）[/bold cyan]")
        while True:
            target_str = Prompt.ask("请输入目标路径（实际文件/目录位置）")
            target = self.validate_path(target_str, must_exist=True)
            if target:
                break
        self.show_path_info(target)
        while True:
            link_str = Prompt.ask("请输入链接路径（软链接位置）")
            link = self.validate_path(link_str, must_exist=False)
            if link:
                if link.exists():
                    self.console.print(f"[red]链接路径已存在: {link}[/red]")
                    continue
                break
        self.console.print(f"\n[yellow]将要创建软链接:[/yellow]")
        self.console.print(f"[cyan]{link}[/cyan] -> [cyan]{target}[/cyan]")
        if Confirm.ask("\n确认创建吗？"):
            if self.create_symlink(target, link):
                self.console.print("[green]✅ 软链接创建成功！[/green]")
            else:
                self.console.print("[red]❌ 软链接创建失败[/red]")
        Prompt.ask("按回车继续")

    def show_path_info_interactive(self):
        self.console.print("\n[bold cyan]查看路径信息[/bold cyan]")
        path_str = Prompt.ask("请输入要查看的路径")
        path = self.validate_path(path_str, must_exist=False)
        if path:
            self.show_path_info(path)
        Prompt.ask("按回车继续")

    def main_menu(self):
        while True:
            self.console.clear()
            title = Text("软链接管理器", style="bold blue")
            panel = Panel(title, subtitle="使用 Rich 交互式界面", border_style="blue")
            self.console.print(panel)
            if not self.check_admin_privileges():
                self.console.print("[red]⚠️  警告: 当前没有管理员权限，可能无法创建软链接[/red]")
                self.console.print("[yellow]建议以管理员身份运行此脚本[/yellow]\n")
            self.console.print("请选择操作:")
            self.console.print("1. 创建软链接（移动目录到新位置并创建链接）")
            self.console.print("2. 创建软链接（直接链接，不移动）")
            self.console.print("3. 查看路径信息")
            self.console.print("4. 查看已记录的链接（TOML）")
            self.console.print("5. 删除软链接（并同步记录）")
            self.console.print("6. 退出")
            choice = Prompt.ask("\n请输入选项", choices=["1", "2", "3", "4", "5", "6"], default="1")
            if choice == "1":
                self.create_move_symlink()
            elif choice == "2":
                self.create_direct_symlink()
            elif choice == "3":
                self.show_path_info_interactive()
            elif choice == "4":
                self.show_recorded_links()
            elif choice == "5":
                self.delete_symlink_interactive()
            elif choice == "6":
                self.console.print("[green]再见！[/green]")
                break
