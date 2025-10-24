#!/usr/bin/env python3
"""
交互式菜单界面
"""

from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt

console = Console()


def interactive_menu():
    """显示交互式主菜单"""
    
    while True:
        # 创建菜单表格
        table = Table(title="🎯 Scoolp 主菜单", show_header=True, border_style="cyan")
        table.add_column("选项", style="cyan", justify="center", width=6)
        table.add_column("功能", style="green", width=22)
        table.add_column("说明", style="white")

        table.add_row("0", "检查 Scoop 状态", "检查 Scoop 是否已安装 (init check)")
        table.add_row("", "", "")
        table.add_row("1", "安装包", "安装 Scoop 包 (install)")
        table.add_row("2", "列出可用包", "显示所有可用的包 (install list)")
        table.add_row("3", "查看包信息", "查看指定包的详细信息 (install info)")
        table.add_row("", "", "")
        table.add_row("4", "同步 buckets", "同步 buckets 和配置 (sync)")
        table.add_row("", "", "")
        table.add_row("5", "列出过期缓存", "显示所有过期的缓存文件 (clean list)")
        table.add_row("6", "备份过期缓存", "备份过期缓存到时间戳目录 (clean backup)")
        table.add_row("7", "删除过期缓存", "直接删除过期缓存文件 (clean delete)")
        table.add_row("", "", "")
        table.add_row("q", "退出", "退出程序")

        console.print("\n")
        console.print(table)
        console.print("\n")

        # 获取用户选择
        choice = Prompt.ask(
            "[bold cyan]请选择操作[/bold cyan]",
            default="1"
        )

        if choice.lower() in ['q', 'quit', 'exit']:
            console.print("[yellow]再见! 👋[/yellow]")
            break

        # 处理选择
        try:
            if choice == "0":
                # 检查 Scoop
                from .init import check
                check()
                
            elif choice == "1":
                # 安装包
                from .install import ScoopPackageInstaller
                installer = ScoopPackageInstaller()
                installer.show_menu()
                
            elif choice == "2":
                # 列出可用包
                from .install import list
                list()
                
            elif choice == "3":
                # 查看包信息
                from .install import ScoopPackageInstaller
                package = Prompt.ask("[bold cyan]请输入包名[/bold cyan]")
                if package:
                    installer = ScoopPackageInstaller()
                    installer.show_package_info(package)
            
            elif choice == "4":
                # 同步 buckets
                from .sync import sync
                sync()
                
            elif choice == "5":
                # 列出过期缓存
                from .clean import list_obsolete
                list_obsolete()
                
            elif choice == "6":
                # 备份过期缓存
                from .clean import backup_obsolete
                backup_obsolete()
                
            elif choice == "7":
                # 删除过期缓存
                from .clean import delete_obsolete
                delete_obsolete()
                
            else:
                console.print("[red]无效的选项，请重新选择[/red]")
                
        except KeyboardInterrupt:
            console.print("\n[yellow]操作已取消[/yellow]")
            continue
        except Exception as e:
            console.print(f"[red]错误: {e}[/red]")
            continue

        # 询问是否继续
        console.print("\n")
        continue_choice = Prompt.ask(
            "[dim]按 Enter 返回主菜单, 或输入 'q' 退出[/dim]",
            default=""
        )
        
        if continue_choice.lower() in ['q', 'quit', 'exit']:
            console.print("[yellow]再见! 👋[/yellow]")
            break


if __name__ == "__main__":
    interactive_menu()

