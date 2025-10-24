#!/usr/bin/env python3
"""
Scoop Bucket 本地安装工具
使用 rich 美化输出，支持安装 Extras-Glow bucket 中的包
"""

import subprocess
import sys
import argparse
from pathlib import Path
from typing import Optional, List
import json

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.prompt import Prompt, Confirm
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.columns import Columns
    from rich.align import Align
except ImportError:
    print("错误: 需要安装 rich 库")
    print("运行: pip install rich")
    sys.exit(1)

console = Console()

class ScoopInstaller:
    def __init__(self, bucket_path: str = "."):
        self.bucket_path = Path(bucket_path).resolve()
        self.bucket_name = "Extras-Glow"
        self.console = console

    def run_command(self, cmd: List[str], cwd: Optional[Path] = None) -> tuple[int, str, str]:
        """运行命令并返回结果"""
        try:
            # 如果是 scoop 命令，使用 PowerShell
            if cmd[0] == "scoop":
                ps_cmd = ["powershell", "-Command"] + cmd
                result = subprocess.run(
                    ps_cmd,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    encoding='utf-8'
                )
            else:
                result = subprocess.run(
                    cmd,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    encoding='utf-8'
                )
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return 1, "", str(e)

    def get_package_info(self, package_name: str) -> Optional[dict]:
        """获取包信息"""
        manifest_path = self.bucket_path / "bucket" / f"{package_name}.json"
        if not manifest_path.exists():
            return None

        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None

    def list_packages(self) -> List[str]:
        """列出所有可用包"""
        bucket_dir = self.bucket_path / "bucket"
        if not bucket_dir.exists():
            return []

        packages = []
        for manifest_file in bucket_dir.glob("*.json"):
            if manifest_file.name != "test.json":  # 排除测试文件
                packages.append(manifest_file.stem)

        return sorted(packages)

    def install_package(self, package_name: str) -> bool:
        """安装包"""
        with console.status(f"[bold green]正在安装 {package_name}...[/bold green]") as status:
            manifest_path = self.bucket_path / "bucket" / f"{package_name}.json"

            if not manifest_path.exists():
                console.print(f"[red]错误: 找不到包 {package_name}[/red]")
                return False

            # 构建 scoop 命令
            cmd = ["scoop", "install", str(manifest_path)]

            returncode, stdout, stderr = self.run_command(cmd)

            if returncode == 0:
                console.print(f"[green]✓ {package_name} 安装成功![/green]")
                return True
            else:
                console.print(f"[red]✗ {package_name} 安装失败[/red]")
                if stderr:
                    console.print(f"[dim red]{stderr}[/dim red]")
                return False

    def show_package_info(self, package_name: str):
        """显示包信息"""
        info = self.get_package_info(package_name)
        if not info:
            console.print(f"[red]找不到包: {package_name}[/red]")
            return

        # 创建信息表格
        table = Table(title=f"📦 {package_name} 信息", show_header=False)
        table.add_column("属性", style="cyan", no_wrap=True)
        table.add_column("值", style="white")

        table.add_row("版本", info.get("version", "未知"))
        table.add_row("描述", info.get("description", "无描述"))
        table.add_row("主页", info.get("homepage", "无"))
        table.add_row("许可证", info.get("license", "未知"))

        if "bin" in info:
            bin_info = info["bin"]
            if isinstance(bin_info, list):
                bin_list = []
                for item in bin_info:
                    if isinstance(item, list):
                        bin_list.append(item[0])
                    else:
                        bin_list.append(item)
                table.add_row("可执行文件", ", ".join(bin_list))
            else:
                table.add_row("可执行文件", str(bin_info))

        console.print(table)

        # 显示备注
        if "notes" in info:
            notes = info["notes"]
            if isinstance(notes, list):
                notes_text = "\n".join(notes)
            else:
                notes_text = notes

            panel = Panel.fit(
                notes_text,
                title="📝 备注",
                border_style="blue"
            )
            console.print(panel)

    def show_menu(self):
        """显示主菜单"""
        packages = self.list_packages()

        if not packages:
            console.print("[red]错误: 找不到任何包[/red]")
            return

        # 创建包列表表格
        table = Table(title=f"📂 {self.bucket_name} Bucket 可用包", show_header=True)
        table.add_column("序号", style="cyan", justify="right", width=4)
        table.add_column("包名", style="green", width=20)
        table.add_column("版本", style="yellow", width=12)
        table.add_column("描述", style="white")

        for i, package in enumerate(packages, 1):
            info = self.get_package_info(package)
            version = info.get("version", "未知") if info else "未知"
            description = info.get("description", "无描述") if info else "无描述"

            # 截断过长的描述
            if len(description) > 50:
                description = description[:47] + "..."

            table.add_row(str(i), package, version, description)

        console.print(table)

        # 默认安装 emm
        default_choice = "emm"
        if default_choice in packages:
            console.print(f"\n[bold blue]默认包: {default_choice}[/bold blue]")
            if Confirm.ask(f"是否安装默认包 {default_choice}?", default=True):
                self.install_package(default_choice)
                return

        # 让用户选择
        while True:
            choice = Prompt.ask(
                "\n请输入包名或序号 (q 退出)",
                default="emm"
            )

            if choice.lower() in ['q', 'quit', 'exit']:
                break

            # 尝试按序号选择
            try:
                index = int(choice) - 1
                if 0 <= index < len(packages):
                    selected_package = packages[index]
                else:
                    console.print("[red]无效的序号[/red]")
                    continue
            except ValueError:
                # 按包名选择
                if choice in packages:
                    selected_package = choice
                else:
                    console.print("[red]找不到包: {choice}[/red]")
                    continue

            # 显示包信息
            self.show_package_info(selected_package)

            # 确认安装
            if Confirm.ask(f"是否安装 {selected_package}?", default=True):
                self.install_package(selected_package)

            if not Confirm.ask("是否继续选择其他包?", default=False):
                break

def main():
    parser = argparse.ArgumentParser(
        description="Scoop Bucket 本地安装工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python install.py                    # 交互式安装 (默认 emm)
  python install.py -p lanraragi       # 安装指定包
  python install.py -l                 # 列出所有包
  python install.py -i lanraragi       # 显示包信息
        """
    )

    parser.add_argument(
        "-p", "--package",
        help="指定要安装的包名"
    )

    parser.add_argument(
        "-l", "--list",
        action="store_true",
        help="列出所有可用包"
    )

    parser.add_argument(
        "-i", "--info",
        help="显示指定包的信息"
    )

    parser.add_argument(
        "--bucket-path",
        default=".",
        help="Bucket 路径 (默认: 当前目录)"
    )

    args = parser.parse_args()

    installer = ScoopInstaller(args.bucket_path)

    # 显示欢迎信息
    welcome_text = Text("🎯 Scoop Bucket 安装工具", style="bold magenta")
    welcome_panel = Panel.fit(
        Align.center(welcome_text),
        title="🚀 欢迎使用",
        border_style="green"
    )
    console.print(welcome_panel)

    try:
        if args.list:
            # 列出所有包
            packages = installer.list_packages()
            if packages:
                table = Table(title="📦 可用包列表")
                table.add_column("包名", style="cyan")
                table.add_column("版本", style="yellow")
                table.add_column("描述", style="white")

                for package in packages:
                    info = installer.get_package_info(package)
                    version = info.get("version", "未知") if info else "未知"
                    description = info.get("description", "无描述") if info else "无描述"
                    if len(description) > 60:
                        description = description[:57] + "..."

                    table.add_row(package, version, description)

                console.print(table)
            else:
                console.print("[red]没有找到任何包[/red]")

        elif args.info:
            # 显示包信息
            installer.show_package_info(args.info)

        elif args.package:
            # 安装指定包
            console.print(f"[bold blue]正在安装包: {args.package}[/bold blue]")
            success = installer.install_package(args.package)
            if success:
                console.print("[green]安装完成![/green]")
            else:
                console.print("[red]安装失败![/red]")
                sys.exit(1)

        else:
            # 交互式模式
            installer.show_menu()

    except KeyboardInterrupt:
        console.print("\n[yellow]用户取消操作[/yellow]")
    except Exception as e:
        console.print(f"[red]发生错误: {e}[/red]")
        sys.exit(1)

if __name__ == "__main__":
    main()