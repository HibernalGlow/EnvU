#!/usr/bin/env python3
"""
Registry file generator for Windows context menu integration.
根据模板生成注册表文件，用于Windows右键菜单集成。
"""

import os
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.text import Text
from rich.table import Table


class RegistryGenerator:
    """注册表文件生成器"""
    
    def __init__(self):
        self.console = Console()
        self.template = """Windows Registry Editor Version 5.00

[HKEY_CLASSES_ROOT\\*\\shell\\{keyword}]
@="Open with {display_name}"
"Icon"="{exe_path}"

[HKEY_CLASSES_ROOT\\*\\shell\\{keyword}\\command]
@="\\"{exe_path}\\" \\"%1\\""

Windows Registry Editor Version 5.00

[HKEY_CLASSES_ROOT\\Directory\\shell\\{keyword}]
@="Open with {display_name}"
"Icon"="{exe_path}"

[HKEY_CLASSES_ROOT\\Directory\\shell\\{keyword}\\command]
@="\\"{exe_path}\\" \\"%V\\""

Windows Registry Editor Version 5.00

[HKEY_CLASSES_ROOT\\Directory\\Background\\shell\\{keyword}]
@="Open with {display_name}"
"Icon"="{exe_path}"

[HKEY_CLASSES_ROOT\\Directory\\Background\\shell\\{keyword}\\command]
@="\\"{exe_path}\\" \\"%V\\""
"""

    def generate_registry_file(self, exe_path: str, keyword: str, display_name: Optional[str] = None) -> str:
        """
        生成注册表文件内容
        
        Args:
            exe_path: 可执行文件的完整路径
            keyword: 注册表键名（如 VSCode, PotPlayer 等）
            display_name: 显示名称（如果不提供，则使用keyword）
        
        Returns:
            生成的注册表文件内容
        """
        if display_name is None:
            display_name = keyword
            
        # 确保路径使用双反斜杠
        formatted_path = exe_path.replace('\\', '\\\\')
        
        return self.template.format(
            keyword=keyword,
            display_name=display_name,
            exe_path=formatted_path
        )
    
    def save_registry_file(self, content: str, output_path: str) -> None:
        """
        保存注册表文件
        
        Args:
            content: 注册表文件内容
            output_path: 输出文件路径        """
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        self.console.print(f"[green]✅ 注册表文件已生成:[/green] {output_path}")
    
    def generate_and_save(self, exe_path: str, keyword: str, output_dir: str = ".", display_name: Optional[str] = None) -> str:
        """
        生成并保存注册表文件
        
        Args:
            exe_path: 可执行文件的完整路径
            keyword: 注册表键名
            output_dir: 输出目录
            display_name: 显示名称
        
        Returns:
            生成的文件路径
        """
        content = self.generate_registry_file(exe_path, keyword, display_name)
        
        # 生成输出文件名
        output_filename = f"Open with {display_name or keyword}.reg"
        output_path = os.path.join(output_dir, output_filename)        
        self.save_registry_file(content, output_path)
        return output_path
    
    def interactive_generate(self) -> str:
        """
        交互式生成注册表文件
        
        Returns:
            生成的文件路径
        """
        self.console.print(Panel.fit(
            "[bold blue]Windows 注册表文件生成器[/bold blue]\n"
            "用于生成右键菜单集成的注册表文件",
            title="🚀 Registry Generator",
            border_style="blue"
        ))
        
        # 输入可执行文件路径
        while True:
            exe_path = Prompt.ask(
                "[yellow]请输入可执行文件的完整路径[/yellow]",
                console=self.console
            )
            
            if os.path.exists(exe_path):
                self.console.print(f"[green]✅ 文件存在:[/green] {exe_path}")
                break
            else:
                if Confirm.ask(f"[red]⚠️ 文件不存在: {exe_path}\n是否继续?[/red]", console=self.console):
                    break
        
        # 输入关键词
        keyword = Prompt.ask(
            "[yellow]请输入注册表键名 (如: VSCode, PotPlayer)[/yellow]",
            console=self.console
        )
        
        # 输入显示名称（可选）
        display_name = Prompt.ask(
            f"[yellow]请输入显示名称 (默认: {keyword})[/yellow]",
            default=keyword,
            console=self.console
        )
        
        # 输入输出目录（可选）
        output_dir = Prompt.ask(
            "[yellow]请输入输出目录 (默认: 当前目录)[/yellow]",
            default=".",
            console=self.console
        )
        
        # 显示预览
        self.console.print("\n[bold cyan]配置预览:[/bold cyan]")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("参数", style="cyan", no_wrap=True)
        table.add_column("值", style="white")
        
        table.add_row("可执行文件路径", exe_path)
        table.add_row("注册表键名", keyword)
        table.add_row("显示名称", display_name)
        table.add_row("输出目录", output_dir)
        
        self.console.print(table)
        
        # 确认生成
        if not Confirm.ask("\n[bold green]确认生成注册表文件?[/bold green]", console=self.console):
            self.console.print("[yellow]❌ 操作已取消[/yellow]")
            return ""
        
        # 生成文件
        try:
            output_path = self.generate_and_save(exe_path, keyword, output_dir, display_name)
            
            self.console.print(f"\n[bold green]🎉 成功生成注册表文件![/bold green]")
            self.console.print(f"[blue]📁 文件位置:[/blue] {output_path}")
            self.console.print(f"[blue]💡 使用方法:[/blue] 双击该文件导入注册表")
            
            # 询问是否立即导入
            if Confirm.ask("[yellow]是否立即导入注册表?[/yellow]", console=self.console):
                os.system(f'regedit /s "{output_path}"')
                self.console.print("[green]✅ 注册表已导入![/green]")
            
            return output_path
            
        except Exception as e:
            self.console.print(f"[red]❌ 生成失败: {e}[/red]")
            return ""


def main():
    """主函数"""
    generator = RegistryGenerator()
    
    # 如果没有提供命令行参数，则进入交互式模式
    if len(sys.argv) == 1:
        generator.interactive_generate()
        return
    
    # 命令行模式
    if len(sys.argv) < 3:
        generator.console.print(Panel.fit(
            "[bold red]用法错误![/bold red]\n\n"
            "[yellow]命令行模式:[/yellow]\n"
            "python registry_generator.py <exe_path> <keyword> [display_name] [output_dir]\n\n"
            "[yellow]交互式模式:[/yellow]\n"
            "python registry_generator.py\n\n"
            "[cyan]示例:[/cyan]\n"
            "python registry_generator.py 'D:\\\\scoop\\\\apps\\\\vscode\\\\current\\\\Code.exe' VSCode 'Code' ./config\n"
            "python registry_generator.py 'C:\\\\Program Files\\\\PotPlayer\\\\PotPlayerMini64.exe' PotPlayer",
            title="❌ 错误",
            border_style="red"
        ))
        return
    
    exe_path = sys.argv[1]
    keyword = sys.argv[2]
    display_name = sys.argv[3] if len(sys.argv) > 3 else None
    output_dir = sys.argv[4] if len(sys.argv) > 4 else "."
    
    # 检查可执行文件是否存在
    if not os.path.exists(exe_path):
        generator.console.print(f"[yellow]⚠️ 警告: 可执行文件不存在:[/yellow] {exe_path}")
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        output_path = generator.generate_and_save(exe_path, keyword, output_dir, display_name)
        
        generator.console.print(f"[bold green]🎉 成功生成注册表文件![/bold green]")
        generator.console.print(f"[blue]📁 文件位置:[/blue] {output_path}")
        generator.console.print(f"[blue]💡 使用方法:[/blue] 双击该文件导入注册表")
        
    except Exception as e:
        generator.console.print(f"[red]❌ 生成失败: {e}[/red]")


if __name__ == "__main__":
    main()
