#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""linku 入口，仅委托到 manager 模块"""

try:
    # 正常包内相对导入
    from .manager import SymlinkManager, console  # type: ignore
except Exception:
    # 作为脚本直接运行（开发场景）的退化导入
    from manager import SymlinkManager  # type: ignore
    from rich.console import Console  # type: ignore
    console = Console()


def main() -> None:
    try:
        manager = SymlinkManager()
        manager.main_menu()
    except KeyboardInterrupt:
        console.print("\n[yellow]程序被用户中断[/yellow]")
    except Exception as e:
        console.print(f"\n[red]程序发生错误: {e}[/red]")


if __name__ == "__main__":
    main()
