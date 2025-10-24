#!/usr/bin/env python3
"""Scoop 管理工具主入口"""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.align import Align

from .init import app as init_app
from .install import app as install_app
from .clean import app as clean_app
from .sync import app as sync_app
from .interactive import interactive_menu

console = Console()
app = typer.Typer(
    name="scoolp",
    help="Scoop 管理工具",
    no_args_is_help=False,
    add_completion=False,
)

app.add_typer(init_app, name="init", help="初始化和安装 Scoop")
app.add_typer(install_app, name="install", help="安装 Scoop 包")
app.add_typer(sync_app, name="sync", help="同步 Scoop buckets")
app.add_typer(clean_app, name="clean", help="清理 Scoop 缓存")


@app.callback(invoke_without_command=True)
def callback(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        welcome_text = Text("Scoop 管理工具", style="bold magenta")
        welcome_panel = Panel.fit(
            Align.center(welcome_text),
            title="欢迎使用 Scoolp",
            border_style="green"
        )
        console.print(welcome_panel)
        interactive_menu()


def main():
    app()


if __name__ == "__main__":
    main()