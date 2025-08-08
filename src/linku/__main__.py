#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
软链接管理器 - 使用 Rich 交互式界面
支持创建、删除和查看软链接
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich import print as rprint
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


class SymlinkManager:
    def __init__(self):
        self.console = console
        
    def check_admin_privileges(self) -> bool:
        """检查是否有管理员权限"""
        try:
            # Windows 检查
            if os.name == 'nt':
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin()
            else:
                # Unix/Linux 检查
                return os.geteuid() == 0
        except:
            return False
    
    def get_directory_size(self, path: Path) -> tuple[float, int]:
        """获取目录大小（MB）和文件数量"""
        try:
            total_size = 0
            file_count = 0
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
                transient=True
            ) as progress:
                task = progress.add_task("正在计算目录大小...", total=None)
                
                for dirpath, dirnames, filenames in os.walk(path):
                    file_count += len(filenames)
                    for filename in filenames:
                        filepath = os.path.join(dirpath, filename)
                        try:
                            total_size += os.path.getsize(filepath)
                        except (OSError, FileNotFoundError):
                            continue            
            return total_size / (1024 * 1024), file_count  # 转换为 MB
        except Exception as e:
            self.console.print(f"[red]计算目录大小失败: {e}[/red]")
            return 0, 0
    
    def validate_path(self, path_str: str, must_exist: bool = True) -> Optional[Path]:
        """验证路径，支持带引号的路径"""
        try:
            # 移除首尾的引号（支持单引号和双引号）
            path_str = path_str.strip()
            if (path_str.startswith('"') and path_str.endswith('"')) or \
               (path_str.startswith("'") and path_str.endswith("'")):
                path_str = path_str[1:-1]
            
            path = Path(path_str).resolve()
            
            if must_exist and not path.exists():
                self.console.print(f"[red]路径不存在: {path}[/red]")
                return None
                
            return path
        except Exception as e:
            self.console.print(f"[red]无效路径: {e}[/red]")
            return None
    
    def create_symlink(self, source: Path, target: Path) -> bool:
        """创建软链接"""
        try:
            if os.name == 'nt':
                # Windows
                if source.is_dir():
                    cmd = f'mklink /D "{target}" "{source}"'
                else:
                    cmd = f'mklink "{target}" "{source}"'
                result = subprocess.run(
                    cmd, 
                    shell=True, 
                    capture_output=True, 
                    text=True,
                    encoding='gbk'
                )
                
                if result.returncode == 0:
                    return True
                else:
                    self.console.print(f"[red]创建软链接失败: {result.stderr}[/red]")
                    return False
            else:
                # Unix/Linux
                os.symlink(source, target)
                return True
                
        except Exception as e:
            self.console.print(f"[red]创建软链接失败: {e}[/red]")
            return False
    
    def move_and_link(self, source: Path, target: Path) -> bool:
        """移动目录并创建软链接，支持跳过失败文件"""
        try:
            # 确保目标目录的父目录存在
            target.parent.mkdir(parents=True, exist_ok=True)
            
            # 移动源目录到目标位置
            self.console.print(f"[yellow]正在移动 {source} 到 {target}...[/yellow]")
            
            # 使用自定义移动函数，支持跳过失败的文件
            success = self.move_directory_with_skip(source, target)
            
            if success:
                # 创建软链接
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
                    shutil.move(str(target), str(source))
                    self.console.print("[yellow]已回滚移动操作[/yellow]")
            except:
                pass
            return False
    
    def move_directory_with_skip(self, source: Path, target: Path) -> bool:
        """移动目录，跳过无法移动的文件"""
        failed_files = []
        total_files = 0
        
        try:
            # 首先尝试简单移动整个目录
            shutil.move(str(source), str(target))
            self.console.print("[green]✅ 目录移动成功[/green]")
            return True
        except Exception as e:
            self.console.print(f"[yellow]⚠️  整体移动失败，尝试逐个文件移动: {e}[/yellow]")
        
        # 如果整体移动失败，尝试逐个文件移动
        try:
            # 创建目标目录
            target.mkdir(parents=True, exist_ok=True)
            
            # 统计总文件数
            for root, dirs, files in os.walk(source):
                total_files += len(files)
            
            self.console.print(f"[cyan]开始逐个移动 {total_files} 个文件...[/cyan]")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task("移动文件中...", total=total_files)
                moved_count = 0
                
                # 递归移动所有文件和子目录
                for root, dirs, files in os.walk(source):
                    # 计算相对路径
                    rel_path = Path(root).relative_to(source)
                    target_dir = target / rel_path
                    
                    # 创建目标子目录
                    try:
                        target_dir.mkdir(parents=True, exist_ok=True)
                    except Exception as e:
                        self.console.print(f"[red]创建目录失败 {target_dir}: {e}[/red]")
                        continue
                    
                    # 移动文件
                    for file in files:
                        source_file = Path(root) / file
                        target_file = target_dir / file
                        
                        try:
                            shutil.move(str(source_file), str(target_file))
                            moved_count += 1
                        except Exception as e:
                            failed_files.append((str(source_file), str(e)))
                            self.console.print(f"[red]跳过文件 {source_file}: {e}[/red]")
                        
                        progress.update(task, advance=1)
            
            # 移动完成后，尝试删除空的源目录
            try:
                if source.exists():
                    # 删除空目录
                    for root, dirs, files in os.walk(source, topdown=False):
                        for dir_name in dirs:
                            dir_path = Path(root) / dir_name
                            try:
                                if not any(dir_path.iterdir()):  # 如果目录为空
                                    dir_path.rmdir()
                            except:
                                pass
                    
                    # 最后删除根目录
                    if not any(source.iterdir()):
                        source.rmdir()
                        self.console.print("[green]✅ 源目录已清理[/green]")
                    else:
                        self.console.print(f"[yellow]⚠️  源目录仍有剩余文件: {source}[/yellow]")
            except Exception as e:
                self.console.print(f"[yellow]清理源目录时出错: {e}[/yellow]")
            
            # 报告结果
            success_rate = (moved_count / total_files) * 100 if total_files > 0 else 0
            self.console.print(f"\n[cyan]移动完成统计:[/cyan]")
            self.console.print(f"成功移动: {moved_count}/{total_files} 文件 ({success_rate:.1f}%)")
            
            if failed_files:
                self.console.print(f"[red]失败文件数: {len(failed_files)}[/red]")
                
                # 显示部分失败文件（最多显示5个）
                show_count = min(5, len(failed_files))
                for i, (file_path, error) in enumerate(failed_files[:show_count]):
                    self.console.print(f"  {i+1}. {Path(file_path).name}: {error}")
                
                if len(failed_files) > show_count:
                    self.console.print(f"  ... 还有 {len(failed_files) - show_count} 个失败文件")
            
            # 如果成功率超过90%，认为操作成功
            return success_rate >= 90.0
            
        except Exception as e:
            self.console.print(f"[red]逐个文件移动也失败了: {e}[/red]")
            return False
    
    def show_path_info(self, path: Path):
        """显示路径信息"""
        if not path.exists():
            self.console.print(f"[red]路径不存在: {path}[/red]")
            return
            
        # 创建信息表格
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
            except:
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
    
    def main_menu(self):
        """主菜单"""
        while True:
            self.console.clear()
            
            # 显示标题
            title = Text("软链接管理器", style="bold blue")
            panel = Panel(
                title,
                subtitle="使用 Rich 交互式界面",
                border_style="blue"
            )
            self.console.print(panel)
            
            # 检查管理员权限
            if not self.check_admin_privileges():
                self.console.print("[red]⚠️  警告: 当前没有管理员权限，可能无法创建软链接[/red]")
                self.console.print("[yellow]建议以管理员身份运行此脚本[/yellow]\n")
            
            # 显示菜单选项
            self.console.print("请选择操作:")
            self.console.print("1. 创建软链接（移动目录到新位置并创建链接）")
            self.console.print("2. 创建软链接（直接链接，不移动）")
            self.console.print("3. 查看路径信息")
            self.console.print("4. 退出")
            
            choice = Prompt.ask("\n请输入选项", choices=["1", "2", "3", "4"], default="1")
            
            if choice == "1":
                self.create_move_symlink()
            elif choice == "2":
                self.create_direct_symlink()
            elif choice == "3":
                self.show_path_info_interactive()
            elif choice == "4":
                self.console.print("[green]再见！[/green]")
                break
    
    def create_move_symlink(self):
        """创建移动式软链接"""
        self.console.print("\n[bold cyan]创建软链接（移动模式）[/bold cyan]")
        
        # 输入源路径
        while True:
            source_str = Prompt.ask("请输入源路径（要移动的目录）")
            source = self.validate_path(source_str, must_exist=True)
            if source:
                break
        
        # 显示源路径信息
        self.show_path_info(source)
        
        if not source.is_dir():
            self.console.print("[red]源路径必须是目录[/red]")
            Prompt.ask("按回车继续")
            return
        
        # 输入目标路径
        while True:
            target_str = Prompt.ask("请输入目标路径（移动到的位置）")
            target = self.validate_path(target_str, must_exist=False)
            if target:
                if target.exists():
                    self.console.print(f"[red]目标路径已存在: {target}[/red]")
                    continue
                break
        
        # 确认操作
        self.console.print(f"\n[yellow]将要执行以下操作:[/yellow]")
        self.console.print(f"1. 移动 [cyan]{source}[/cyan] 到 [cyan]{target}[/cyan]")
        self.console.print(f"2. 创建软链接 [cyan]{source}[/cyan] -> [cyan]{target}[/cyan]")
        
        if Confirm.ask("\n确认执行吗？"):
            if self.move_and_link(source, target):
                self.console.print("[green]✅ 软链接创建成功！[/green]")
            else:
                self.console.print("[red]❌ 软链接创建失败[/red]")
        
        Prompt.ask("按回车继续")
    
    def create_direct_symlink(self):
        """创建直接软链接"""
        self.console.print("\n[bold cyan]创建软链接（直接模式）[/bold cyan]")
        
        # 输入目标路径（实际文件/目录位置）
        while True:
            target_str = Prompt.ask("请输入目标路径（实际文件/目录位置）")
            target = self.validate_path(target_str, must_exist=True)
            if target:
                break
        
        # 显示目标路径信息
        self.show_path_info(target)
        
        # 输入链接路径
        while True:
            link_str = Prompt.ask("请输入链接路径（软链接位置）")
            link = self.validate_path(link_str, must_exist=False)
            if link:
                if link.exists():
                    self.console.print(f"[red]链接路径已存在: {link}[/red]")
                    continue
                break
        
        # 确认操作
        self.console.print(f"\n[yellow]将要创建软链接:[/yellow]")
        self.console.print(f"[cyan]{link}[/cyan] -> [cyan]{target}[/cyan]")
        
        if Confirm.ask("\n确认创建吗？"):
            if self.create_symlink(target, link):
                self.console.print("[green]✅ 软链接创建成功！[/green]")
            else:
                self.console.print("[red]❌ 软链接创建失败[/red]")
        
        Prompt.ask("按回车继续")
    
    def show_path_info_interactive(self):
        """交互式显示路径信息"""
        self.console.print("\n[bold cyan]查看路径信息[/bold cyan]")
        
        path_str = Prompt.ask("请输入要查看的路径")
        path = self.validate_path(path_str, must_exist=False)
        
        if path:
            self.show_path_info(path)
        
        Prompt.ask("按回车继续")


def main():
    """主函数"""
    try:
        manager = SymlinkManager()
        manager.main_menu()
    except KeyboardInterrupt:
        console.print("\n[yellow]程序被用户中断[/yellow]")
    except Exception as e:
        console.print(f"\n[red]程序发生错误: {e}[/red]")


if __name__ == "__main__":
    main()
