#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
软链接重定向工具 - 移动软链接目标并更新链接
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


class SymlinkRedirector:
    def __init__(self):
        self.console = console
    
    def check_admin_privileges(self) -> bool:
        """检查是否有管理员权限"""
        try:
            if os.name == 'nt':
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin()
            else:
                return os.geteuid() == 0
        except:
            return False
    
    def get_symlink_info(self, link_path: Path) -> Optional[Tuple[bool, Optional[Path]]]:
        """获取软链接信息"""
        try:
            if not link_path.exists():
                return False, None
            
            if link_path.is_symlink():
                target = link_path.readlink()
                return True, target
            else:
                return False, None
        except Exception as e:
            self.console.print(f"[red]获取软链接信息失败: {e}[/red]")
            return None, None
    
    def remove_symlink(self, link_path: Path) -> bool:
        """删除软链接"""
        try:
            if os.name == 'nt':
                # Windows
                cmd = f'rmdir "{link_path}"' if link_path.is_dir() else f'del "{link_path}"'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                return result.returncode == 0
            else:
                # Unix/Linux
                link_path.unlink()
                return True
        except Exception as e:
            self.console.print(f"[red]删除软链接失败: {e}[/red]")
            return False
    
    def create_symlink(self, target: Path, link_path: Path) -> bool:
        """创建软链接"""
        try:
            if os.name == 'nt':
                # Windows
                if target.is_dir():
                    cmd = f'mklink /D "{link_path}" "{target}"'
                else:
                    cmd = f'mklink "{link_path}" "{target}"'
                
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
                os.symlink(target, link_path)
                return True
        except Exception as e:
            self.console.print(f"[red]创建软链接失败: {e}[/red]")
            return False
    
    def move_with_retry(self, source: Path, target: Path) -> bool:
        """带重试的移动操作"""
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                # 确保目标目录的父目录存在
                target.parent.mkdir(parents=True, exist_ok=True)
                
                # 移动文件夹
                shutil.move(str(source), str(target))
                self.console.print(f"[green]✅ 成功移动到: {target}[/green]")
                return True
                
            except PermissionError as e:
                self.console.print(f"[red]权限错误 (尝试 {attempt + 1}/{max_attempts}): {e}[/red]")
                if attempt < max_attempts - 1:
                    self.console.print("[yellow]等待 2 秒后重试...[/yellow]")
                    import time
                    time.sleep(2)
            except Exception as e:
                self.console.print(f"[red]移动失败: {e}[/red]")
                break
        
        return False
    
    def redirect_symlink(self, link_path: Path, new_target: Path) -> bool:
        """重定向软链接到新目标"""
        try:
            # 检查软链接状态
            is_link, current_target = self.get_symlink_info(link_path)
            
            if is_link is None:
                return False
            
            if not is_link:
                self.console.print(f"[red]{link_path} 不是软链接[/red]")
                return False
            
            if not current_target or not current_target.exists():
                self.console.print(f"[red]当前目标不存在: {current_target}[/red]")
                return False
            
            self.console.print(f"[cyan]当前软链接: {link_path} -> {current_target}[/cyan]")
            self.console.print(f"[cyan]新目标位置: {new_target}[/cyan]")
            
            # 1. 删除软链接
            self.console.print("[yellow]步骤 1/3: 删除现有软链接...[/yellow]")
            if not self.remove_symlink(link_path):
                self.console.print("[red]删除软链接失败[/red]")
                return False
            
            # 2. 移动实际文件/目录
            self.console.print("[yellow]步骤 2/3: 移动文件到新位置...[/yellow]")
            if not self.move_with_retry(current_target, new_target):
                # 回滚：重新创建软链接
                self.console.print("[yellow]移动失败，尝试回滚...[/yellow]")
                self.create_symlink(current_target, link_path)
                return False
            
            # 3. 重新创建软链接指向新位置
            self.console.print("[yellow]步骤 3/3: 创建新软链接...[/yellow]")
            if not self.create_symlink(new_target, link_path):
                self.console.print("[red]创建新软链接失败[/red]")
                # 尝试回滚
                self.console.print("[yellow]尝试回滚移动操作...[/yellow]")
                try:
                    shutil.move(str(new_target), str(current_target))
                    self.create_symlink(current_target, link_path)
                except:
                    pass
                return False
            
            self.console.print("[green]✅ 软链接重定向成功！[/green]")
            return True
            
        except Exception as e:
            self.console.print(f"[red]重定向失败: {e}[/red]")
            return False
    
    def show_symlink_status(self, link_path: Path):
        """显示软链接状态"""
        table = Table(title=f"软链接状态: {link_path}")
        table.add_column("属性", style="cyan")
        table.add_column("值", style="green")
        
        if not link_path.exists():
            table.add_row("状态", "不存在")
        else:
            table.add_row("路径", str(link_path))
            table.add_row("存在", "是")
            
            if link_path.is_symlink():
                table.add_row("类型", "软链接")
                try:
                    target = link_path.readlink()
                    table.add_row("目标", str(target))
                    table.add_row("目标存在", "是" if target.exists() else "否")
                    
                    if target.exists():
                        if target.is_dir():
                            # 计算目录大小
                            try:
                                total_size = sum(f.stat().st_size for f in target.rglob('*') if f.is_file())
                                size_mb = total_size / (1024 * 1024)
                                table.add_row("目标大小", f"{size_mb:.2f} MB")
                            except:
                                table.add_row("目标大小", "无法计算")
                        else:
                            size_mb = target.stat().st_size / (1024 * 1024)
                            table.add_row("目标大小", f"{size_mb:.2f} MB")
                except Exception as e:
                    table.add_row("目标", f"无法读取: {e}")
            else:
                table.add_row("类型", "普通文件/目录")
        
        self.console.print(table)
    
    def main(self):
        """主函数"""
        self.console.print(Panel(
            "软链接重定向工具",
            subtitle="移动软链接目标并更新链接",
            border_style="blue"
        ))
        
        # 检查管理员权限
        if not self.check_admin_privileges():
            self.console.print("[red]⚠️  警告: 需要管理员权限来操作软链接[/red]")
            self.console.print("[yellow]请以管理员身份运行此脚本[/yellow]")
            return
        
        # 预设的操作：kingsoft 重定向
        link_path = Path("C:/Users/30902/AppData/Roaming/kingsoft")
        new_target = Path("D:/1SoftLink/Roaming/kingsoft")
        
        self.console.print("\n[bold cyan]当前任务: 重定向 kingsoft 软链接[/bold cyan]")
        
        # 显示当前状态
        self.show_symlink_status(link_path)
        
        # 确认操作
        self.console.print(f"\n[yellow]将要执行以下操作:[/yellow]")
        self.console.print(f"1. 将实际文件从当前位置移动到: [cyan]{new_target}[/cyan]")
        self.console.print(f"2. 更新软链接 [cyan]{link_path}[/cyan] 指向新位置")
        
        if Confirm.ask("\n确认执行重定向操作吗？"):
            success = self.redirect_symlink(link_path, new_target)
            
            if success:
                self.console.print("\n[green]🎉 操作完成！[/green]")
                self.show_symlink_status(link_path)
            else:
                self.console.print("\n[red]❌ 操作失败[/red]")
        else:
            self.console.print("[yellow]操作已取消[/yellow]")


def main():
    """程序入口"""
    try:
        redirector = SymlinkRedirector()
        redirector.main()
    except KeyboardInterrupt:
        console.print("\n[yellow]程序被用户中断[/yellow]")
    except Exception as e:
        console.print(f"\n[red]程序发生错误: {e}[/red]")


if __name__ == "__main__":
    main()
