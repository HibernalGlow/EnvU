#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件迁移管理器 - 使用 Rich 交互式界面
支持批量迁移文件和目录到新位置
"""

import os
import sys
import shutil
import time
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.tree import Tree
from rich import print as rprint
from rich.columns import Columns

console = Console()


class FileMigrator:
    def __init__(self):
        self.console = console
        self.failed_operations = []
        self.skipped_files = []
        
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
    
    def get_directory_size(self, path: Path) -> tuple[float, int]:
        """获取目录大小（MB）和文件数量"""
        try:
            total_size = 0
            file_count = 0
            
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
    
    def scan_directory_structure(self, path: Path, max_depth: int = 3) -> Tree:
        """扫描目录结构"""
        tree = Tree(f"📁 {path.name}")
        
        def add_to_tree(current_path: Path, parent_tree: Tree, depth: int):
            if depth >= max_depth:
                parent_tree.add("[dim]...[/dim]")
                return
                
            try:
                items = list(current_path.iterdir())
                # 先添加目录，再添加文件
                items.sort(key=lambda x: (x.is_file(), x.name.lower()))
                
                for item in items[:10]:  # 限制显示数量
                    if item.is_dir():
                        size_mb, file_count = self.get_directory_size(item)
                        branch = parent_tree.add(f"📁 {item.name} [dim]({size_mb:.1f}MB, {file_count} files)[/dim]")
                        if depth < max_depth - 1:
                            add_to_tree(item, branch, depth + 1)
                    else:
                        size_mb = item.stat().st_size / (1024 * 1024)
                        parent_tree.add(f"📄 {item.name} [dim]({size_mb:.1f}MB)[/dim]")
                
                if len(items) > 10:
                    parent_tree.add(f"[dim]... 还有 {len(items) - 10} 个项目[/dim]")
                    
            except PermissionError:
                parent_tree.add("[red]❌ 权限不足[/red]")
            except Exception as e:
                parent_tree.add(f"[red]❌ 错误: {e}[/red]")
        
        add_to_tree(path, tree, 0)
        return tree
    
    def migrate_with_progress(self, source: Path, destination: Path, operation: str = "move") -> bool:
        """迁移文件/目录并显示进度"""
        self.failed_operations.clear()
        self.skipped_files.clear()
        
        # 统计需要处理的文件数
        total_files = 0
        total_size = 0
        
        self.console.print("[cyan]正在扫描源目录...[/cyan]")
        
        if source.is_file():
            total_files = 1
            total_size = source.stat().st_size
        else:
            for root, dirs, files in os.walk(source):
                total_files += len(files)
                for file in files:
                    file_path = Path(root) / file
                    try:
                        total_size += file_path.stat().st_size
                    except:
                        continue
        
        self.console.print(f"[green]扫描完成: {total_files} 个文件, 总大小 {total_size / (1024**3):.2f} GB[/green]\n")
        
        # 开始迁移
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=self.console
        ) as progress:
            
            main_task = progress.add_task(f"正在{operation}文件...", total=total_files)
            
            if source.is_file():
                # 单文件迁移
                try:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    if operation == "move":
                        shutil.move(str(source), str(destination))
                    else:  # copy
                        shutil.copy2(str(source), str(destination))
                    progress.update(main_task, advance=1)
                    return True
                except Exception as e:
                    self.failed_operations.append((str(source), str(e)))
                    return False
            else:
                # 目录迁移
                return self._migrate_directory(source, destination, operation, progress, main_task, total_files)
    
    def _migrate_directory(self, source: Path, destination: Path, operation: str, 
                          progress: Progress, main_task, total_files: int) -> bool:
        """迁移目录的核心实现"""
        processed_files = 0
        
        try:
            # 首先尝试整体操作
            if operation == "move":
                try:
                    shutil.move(str(source), str(destination))
                    progress.update(main_task, completed=total_files)
                    return True
                except Exception as e:
                    self.console.print(f"[yellow]整体移动失败，尝试逐个文件操作: {e}[/yellow]")
            
            # 逐个文件操作
            destination.mkdir(parents=True, exist_ok=True)
            
            for root, dirs, files in os.walk(source):
                # 计算相对路径
                rel_path = Path(root).relative_to(source)
                target_dir = destination / rel_path
                
                # 创建目标目录
                try:
                    target_dir.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    self.console.print(f"[red]创建目录失败 {target_dir}: {e}[/red]")
                    continue
                
                # 处理文件
                for file in files:
                    source_file = Path(root) / file
                    target_file = target_dir / file
                    
                    try:
                        if target_file.exists():
                            if not Confirm.ask(f"文件已存在: {target_file.name}，是否覆盖？", default=False):
                                self.skipped_files.append(str(source_file))
                                processed_files += 1
                                progress.update(main_task, advance=1)
                                continue
                        
                        if operation == "move":
                            shutil.move(str(source_file), str(target_file))
                        else:  # copy
                            shutil.copy2(str(source_file), str(target_file))
                        
                        processed_files += 1
                        
                    except Exception as e:
                        self.failed_operations.append((str(source_file), str(e)))
                        self.console.print(f"[red]处理文件失败 {source_file.name}: {e}[/red]")
                    
                    progress.update(main_task, advance=1)
            
            # 如果是移动操作，删除空的源目录
            if operation == "move":
                self._cleanup_empty_directories(source)
            
            return len(self.failed_operations) < (total_files * 0.1)  # 90% 成功率
            
        except Exception as e:
            self.console.print(f"[red]迁移过程发生错误: {e}[/red]")
            return False
    
    def _cleanup_empty_directories(self, source: Path):
        """清理空目录"""
        try:
            for root, dirs, files in os.walk(source, topdown=False):
                for dir_name in dirs:
                    dir_path = Path(root) / dir_name
                    try:
                        if not any(dir_path.iterdir()):
                            dir_path.rmdir()
                    except:
                        pass
            
            # 删除根目录
            if source.exists() and not any(source.iterdir()):
                source.rmdir()
                self.console.print("[green]✅ 源目录已清理[/green]")
            elif source.exists():
                self.console.print(f"[yellow]⚠️  源目录仍有剩余内容: {source}[/yellow]")
                
        except Exception as e:
            self.console.print(f"[yellow]清理目录时出错: {e}[/yellow]")
    
    def show_migration_summary(self, total_files: int, operation: str):
        """显示迁移汇总"""
        # 创建汇总表格
        table = Table(title=f"{operation}操作汇总", border_style="blue")
        table.add_column("项目", style="cyan")
        table.add_column("数量", style="green")
        table.add_column("详情", style="yellow")
        
        successful = total_files - len(self.failed_operations) - len(self.skipped_files)
        success_rate = (successful / total_files * 100) if total_files > 0 else 0
        
        table.add_row("总文件数", str(total_files), "")
        table.add_row("成功处理", str(successful), f"{success_rate:.1f}%")
        table.add_row("跳过文件", str(len(self.skipped_files)), "用户选择跳过")
        table.add_row("失败文件", str(len(self.failed_operations)), "处理时出错")
        
        self.console.print(table)
        
        # 显示失败详情
        if self.failed_operations:
            self.console.print("\n[red]失败文件详情:[/red]")
            for i, (file_path, error) in enumerate(self.failed_operations[:5]):
                self.console.print(f"  {i+1}. {Path(file_path).name}: {error}")
            
            if len(self.failed_operations) > 5:
                self.console.print(f"  ... 还有 {len(self.failed_operations) - 5} 个失败文件")
        
        # 显示跳过详情
        if self.skipped_files:
            self.console.print("\n[yellow]跳过文件:[/yellow]")
            for i, file_path in enumerate(self.skipped_files[:3]):
                self.console.print(f"  {i+1}. {Path(file_path).name}")
            
            if len(self.skipped_files) > 3:
                self.console.print(f"  ... 还有 {len(self.skipped_files) - 3} 个跳过文件")
    
    def main_menu(self):
        """主菜单"""
        while True:
            self.console.clear()
            
            # 显示标题
            title = Text("文件迁移管理器", style="bold blue")
            panel = Panel(
                title,
                subtitle="支持批量移动和复制文件",
                border_style="blue"
            )
            self.console.print(panel)
            
            # 显示菜单选项
            self.console.print("请选择操作:")
            self.console.print("1. 移动文件/目录")
            self.console.print("2. 复制文件/目录")
            self.console.print("3. 预览目录结构")
            self.console.print("4. 批量迁移多个目录")
            self.console.print("5. 退出")
            
            choice = Prompt.ask("\n请输入选项", choices=["1", "2", "3", "4", "5"], default="1")
            
            if choice == "1":
                self.single_migration("move")
            elif choice == "2":
                self.single_migration("copy")
            elif choice == "3":
                self.preview_directory()
            elif choice == "4":
                self.batch_migration()
            elif choice == "5":
                self.console.print("[green]再见！[/green]")
                break
    
    def single_migration(self, operation: str):
        """单个文件/目录迁移"""
        op_name = "移动" if operation == "move" else "复制"
        self.console.print(f"\n[bold cyan]{op_name}文件/目录[/bold cyan]")
        self.console.print("[dim]提示: 支持带引号的路径[/dim]\n")
        
        # 输入源路径
        source_path = None
        while not source_path:
            source_str = Prompt.ask("请输入源路径（文件或目录）")
            if source_str.lower() in ['q', 'quit', 'exit']:
                return
            source_path = self.validate_path(source_str, must_exist=True)
        
        # 显示源信息
        if source_path.is_dir():
            size_mb, file_count = self.get_directory_size(source_path)
            self.console.print(f"[cyan]源目录: {source_path}[/cyan]")
            self.console.print(f"[green]大小: {size_mb:.2f} MB, 文件数: {file_count}[/green]\n")
        else:
            size_mb = source_path.stat().st_size / (1024 * 1024)
            self.console.print(f"[cyan]源文件: {source_path}[/cyan]")
            self.console.print(f"[green]大小: {size_mb:.2f} MB[/green]\n")
        
        # 输入目标路径
        destination_path = None
        while not destination_path:
            dest_str = Prompt.ask("请输入目标路径")
            if dest_str.lower() in ['q', 'quit', 'exit']:
                return
            destination_path = self.validate_path(dest_str, must_exist=False)
            
            if destination_path and destination_path.exists():
                if not Confirm.ask(f"目标路径已存在: {destination_path}，是否继续？"):
                    destination_path = None
        
        # 确认操作
        self.console.print(f"\n[yellow]将要{op_name}:[/yellow]")
        self.console.print(f"从: [cyan]{source_path}[/cyan]")
        self.console.print(f"到: [cyan]{destination_path}[/cyan]")
        
        if Confirm.ask(f"\n确认{op_name}吗？"):
            start_time = time.time()
            success = self.migrate_with_progress(source_path, destination_path, operation)
            end_time = time.time()
            
            self.console.print(f"\n[cyan]操作耗时: {end_time - start_time:.2f} 秒[/cyan]")
            
            if success:
                self.console.print(f"[green]✅ {op_name}成功！[/green]")
            else:
                self.console.print(f"[red]❌ {op_name}完成，但有部分文件失败[/red]")
            
            # 显示汇总
            if source_path.is_dir():
                total_files = sum(len(files) for _, _, files in os.walk(source_path)) if source_path.exists() else 0
                if total_files == 0:  # 如果是移动操作，源目录可能已经不存在
                    total_files = len(self.failed_operations) + len(self.skipped_files) + 1  # 估算
                self.show_migration_summary(total_files, op_name)
        
        Prompt.ask("按回车继续")
    
    def preview_directory(self):
        """预览目录结构"""
        self.console.print("\n[bold cyan]预览目录结构[/bold cyan]")
        
        path_str = Prompt.ask("请输入要预览的目录路径")
        if path_str.lower() in ['q', 'quit', 'exit']:
            return
            
        path = self.validate_path(path_str, must_exist=True)
        
        if path and path.is_dir():
            self.console.print(f"\n[cyan]目录结构预览: {path}[/cyan]")
            tree = self.scan_directory_structure(path)
            self.console.print(tree)
            
            size_mb, file_count = self.get_directory_size(path)
            self.console.print(f"\n[green]总计: {size_mb:.2f} MB, {file_count} 个文件[/green]")
        elif path and path.is_file():
            self.console.print("[yellow]这是一个文件，不是目录[/yellow]")
        
        Prompt.ask("按回车继续")
    
    def batch_migration(self):
        """批量迁移多个目录"""
        self.console.print("\n[bold cyan]批量迁移多个目录[/bold cyan]")
        self.console.print("[dim]输入多个源目录路径，以空行结束[/dim]\n")
        
        source_paths = []
        while True:
            path_str = Prompt.ask(f"请输入第 {len(source_paths) + 1} 个源目录路径（直接回车结束输入）", default="")
            if not path_str:
                break
                
            path = self.validate_path(path_str, must_exist=True)
            if path and path.is_dir():
                source_paths.append(path)
                self.console.print(f"[green]✅ 已添加: {path}[/green]")
            elif path and path.is_file():
                self.console.print("[yellow]⚠️  只支持目录，跳过文件[/yellow]")
        
        if not source_paths:
            self.console.print("[red]没有有效的源目录[/red]")
            Prompt.ask("按回车继续")
            return
        
        # 输入基础目标目录
        base_dest_str = Prompt.ask("请输入基础目标目录")
        base_dest = self.validate_path(base_dest_str, must_exist=False)
        
        if not base_dest:
            Prompt.ask("按回车继续")
            return
        
        # 选择操作类型
        operation = Prompt.ask("选择操作类型", choices=["move", "copy"], default="move")
        op_name = "移动" if operation == "move" else "复制"
        
        # 显示批量操作预览
        self.console.print(f"\n[yellow]批量{op_name}预览:[/yellow]")
        for i, source in enumerate(source_paths, 1):
            target = base_dest / source.name
            self.console.print(f"{i}. {source} -> {target}")
        
        if not Confirm.ask(f"\n确认批量{op_name}这 {len(source_paths)} 个目录吗？"):
            return
        
        # 执行批量操作
        total_success = 0
        start_time = time.time()
        
        for i, source in enumerate(source_paths, 1):
            target = base_dest / source.name
            self.console.print(f"\n[cyan]正在处理 {i}/{len(source_paths)}: {source.name}[/cyan]")
            
            if self.migrate_with_progress(source, target, operation):
                total_success += 1
                self.console.print(f"[green]✅ {source.name} {op_name}成功[/green]")
            else:
                self.console.print(f"[red]❌ {source.name} {op_name}失败或部分失败[/red]")
        
        end_time = time.time()
        
        # 显示批量操作汇总
        self.console.print(f"\n[cyan]批量操作完成，耗时: {end_time - start_time:.2f} 秒[/cyan]")
        self.console.print(f"[green]成功: {total_success}/{len(source_paths)} 个目录[/green]")
        
        Prompt.ask("按回车继续")


def main():
    """主函数"""
    try:
        migrator = FileMigrator()
        migrator.main_menu()
    except KeyboardInterrupt:
        console.print("\n[yellow]程序被用户中断[/yellow]")
    except Exception as e:
        console.print(f"\n[red]程序发生错误: {e}[/red]")


if __name__ == "__main__":
    main()
