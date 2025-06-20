#!/usr/bin/env python3
"""
winget到scoop迁移工具
自动获取winget安装的包，在scoop bucket中搜索匹配项，并提供交互式安装
"""

import subprocess
import json
import re
import sys
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

try:
    from rich.console import Console
    from rich.table import Table
    from rich.prompt import Confirm, Prompt
    from rich.text import Text
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.style import Style
except ImportError:
    print("需要安装rich库: pip install rich")
    sys.exit(1)

console = Console()

@dataclass
class WingetPackage:
    """winget包信息"""
    name: str
    id: str
    version: str
    source: str

@dataclass
class ScoopPackage:
    """scoop包信息"""
    name: str
    bucket: str
    description: str = ""
    version: str = ""

def search_package_in_scoop(winget_pkg: WingetPackage) -> Tuple[WingetPackage, List[ScoopPackage]]:
    """
    独立的搜索函数，用于多进程调用
    搜索单个winget包在scoop中的匹配项
    """
    def search_scoop_command(package_name: str) -> List[ScoopPackage]:
        """执行scoop搜索命令"""
        matches = []
        
        # 尝试多种scoop搜索命令
        search_commands = [
            ["scoop", "search", package_name],
            ["powershell", "-c", f"scoop search {package_name}"],
            ["pwsh", "-c", f"scoop search {package_name}"]
        ]
        
        for cmd in search_commands:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=15,
                    shell=True if len(cmd) == 3 else False
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    lines = result.stdout.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and package_name.lower() in line.lower() and '/' in line:
                            # 解析scoop search的输出
                            parts = line.split()
                            if len(parts) >= 1:
                                full_name = parts[0]  # 格式通常是 bucket/package
                                if '/' in full_name:
                                    bucket_name, pkg_name = full_name.split('/', 1)
                                    description = ' '.join(parts[1:]) if len(parts) > 1 else ""
                                    
                                    matches.append(ScoopPackage(
                                        name=pkg_name,
                                        bucket=bucket_name,
                                        description=description
                                    ))
                    break  # 如果成功搜索到结果，就退出循环
                        
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
                continue
        
        return matches
    
    scoop_matches = []
    
    # 搜索完整名称
    scoop_matches = search_scoop_command(winget_pkg.name)
    
    # 如果没找到，尝试搜索ID
    if not scoop_matches and winget_pkg.id != winget_pkg.name:
        scoop_matches = search_scoop_command(winget_pkg.id)
    
    # 如果还没找到，尝试搜索名称的一部分
    if not scoop_matches:
        # 移除版本号和特殊字符
        clean_name = re.sub(r'[\d\.\-_]+$', '', winget_pkg.name).strip()
        if clean_name and clean_name != winget_pkg.name:
            scoop_matches = search_scoop_command(clean_name)
    
    # 去重
    unique_matches = []
    seen = set()
    for match in scoop_matches:
        key = (match.name, match.bucket)
        if key not in seen:
            seen.add(key)
            unique_matches.append(match)
    
    return (winget_pkg, unique_matches)

class WingetToScoopMigrator:
    """winget到scoop迁移器"""
    
    def __init__(self):
        self.console = Console()
        self.winget_packages: List[WingetPackage] = []
        self.scoop_packages: List[ScoopPackage] = []
        self.matches: List[Tuple[WingetPackage, List[ScoopPackage]]] = []
        
    def check_prerequisites(self) -> bool:
        """检查必要工具是否可用"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("检查必要工具...", total=None)
            
            # 检查winget
            try:
                result = subprocess.run(
                    ["winget", "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True
                )
                progress.update(task, description="✓ winget可用")
            except (subprocess.CalledProcessError, FileNotFoundError):
                self.console.print("❌ winget不可用", style="red")
                return False
            
            # 检查scoop - 尝试多种方式
            scoop_available = False
            scoop_commands = [
                ["scoop", "-v"],
                ["powershell", "-c", "scoop -v"],
                ["pwsh", "-c", "scoop -v"]
            ]
            
            for cmd in scoop_commands:
                try:
                    result = subprocess.run(
                        cmd, 
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        check=True,
                        shell=True if len(cmd) == 3 else False,
                        timeout=10
                    )
                    if result.returncode == 0:
                        scoop_available = True
                        progress.update(task, description="✓ scoop可用")
                        break
                except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                    continue
            
            if not scoop_available:
                self.console.print("❌ scoop不可用", style="red")
                return False
                
        return True
    
    def get_winget_packages(self) -> List[WingetPackage]:
        """获取winget安装的包列表"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("获取winget包列表...", total=None)
            
            try:
                # 使用winget list命令获取已安装的包
                result = subprocess.run(
                    ["winget", "list", "--accept-source-agreements"],
                    capture_output=True,
                    text=True,
                    check=True,
                    encoding='utf-8',
                    errors='ignore'
                )
                
                packages = []
                lines = result.stdout.split('\n')
                
                # 跳过标题行，找到数据开始位置
                data_start = -1
                for i, line in enumerate(lines):
                    if '名称' in line or 'Name' in line:
                        data_start = i + 1
                        break
                
                if data_start == -1:
                    # 如果找不到标题，尝试其他方法
                    for i, line in enumerate(lines):
                        if line.strip() and not line.startswith('-'):
                            data_start = i
                            break
                
                # 解析包信息
                for line in lines[data_start:]:
                    if not line.strip() or line.startswith('-'):
                        continue
                    
                    # 使用正则表达式解析包信息
                    # winget list的输出格式通常是: Name  Id  Version  Available  Source
                    parts = line.split()
                    if len(parts) >= 3:
                        name = parts[0]
                        id_part = parts[1] if len(parts) > 1 else name
                        version = parts[2] if len(parts) > 2 else "unknown"
                        source = parts[-1] if len(parts) > 3 else "winget"
                        
                        packages.append(WingetPackage(
                            name=name,
                            id=id_part,
                            version=version,
                            source=source
                        ))
                
                progress.update(task, description=f"✓ 获取到 {len(packages)} 个winget包")
                self.winget_packages = packages
                return packages                
            except subprocess.CalledProcessError as e:
                self.console.print(f"❌ 获取winget包列表失败: {e}", style="red")
                return []
    
    def get_scoop_buckets(self) -> List[str]:
        """获取scoop所有bucket列表"""
        # 尝试多种方式调用scoop
        scoop_commands = [
            ["scoop", "bucket", "list"],
            ["powershell", "-c", "scoop bucket list"],
            ["pwsh", "-c", "scoop bucket list"]
        ]
        
        for cmd in scoop_commands:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=True,
                    shell=True if len(cmd) == 1 else False,
                    timeout=10
                )
                
                buckets = []
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if line and not line.startswith('-') and 'bucket' not in line.lower():
                        bucket_name = line.split()[0]
                        if bucket_name and bucket_name != 'Name':  # 跳过标题行
                            buckets.append(bucket_name)
                
                if buckets:
                    return buckets
                    
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
                continue
          # 如果所有方法都失败，返回常用的bucket列表
        self.console.print("⚠️ 无法获取scoop bucket列表，使用默认bucket", style="yellow")
        return ["main", "extras", "versions", "nonportable"]
    
    def search_in_scoop(self, package_name: str) -> List[ScoopPackage]:
        """在scoop中搜索匹配的包"""
        matches = []
        buckets = self.get_scoop_buckets()
        
        # 添加常用的bucket（如果没有的话）
        common_buckets = ["main", "extras", "versions", "nerd-fonts", "nonportable"]
        for bucket in common_buckets:
            if bucket not in buckets:
                buckets.append(bucket)
        
        # 尝试多种scoop搜索命令
        search_commands = [
            ["scoop", "search", package_name],
            ["powershell", "-c", f"scoop search {package_name}"],
            ["pwsh", "-c", f"scoop search {package_name}"]
        ]
        
        for cmd in search_commands:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=15,
                    shell=True if len(cmd) == 3 else False
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    lines = result.stdout.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and package_name.lower() in line.lower() and '/' in line:
                            # 解析scoop search的输出
                            parts = line.split()
                            if len(parts) >= 1:
                                full_name = parts[0]  # 格式通常是 bucket/package
                                if '/' in full_name:
                                    bucket_name, pkg_name = full_name.split('/', 1)
                                    description = ' '.join(parts[1:]) if len(parts) > 1 else ""
                                    
                                    matches.append(ScoopPackage(
                                        name=pkg_name,
                                        bucket=bucket_name,
                                        description=description
                                    ))
                    break  # 如果成功搜索到结果，就退出循环
                        
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
                continue
        
        # 去重
        unique_matches = []
        seen = set()
        for match in matches:
            key = (match.name, match.bucket)
            if key not in seen:
                seen.add(key)
                unique_matches.append(match)
        
        return unique_matches
    def find_matches(self) -> List[Tuple[WingetPackage, List[ScoopPackage]]]:
        """查找winget包在scoop中的匹配项（使用多进程）"""
        matches = []
        
        if not self.winget_packages:
            return matches
        
        # 获取CPU核心数，限制最大进程数
        max_workers = min(multiprocessing.cpu_count(), len(self.winget_packages), 8)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("多进程搜索匹配的包...", total=len(self.winget_packages))
            
            # 使用进程池进行并行搜索
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有搜索任务
                future_to_pkg = {
                    executor.submit(search_package_in_scoop, pkg): pkg 
                    for pkg in self.winget_packages
                }
                
                # 收集结果
                for future in as_completed(future_to_pkg):
                    winget_pkg = future_to_pkg[future]
                    try:
                        pkg_result, scoop_matches = future.result()
                        progress.update(task, advance=1, description=f"搜索完成: {winget_pkg.name}")
                        
                        if scoop_matches:
                            matches.append((pkg_result, scoop_matches))
                            
                    except Exception as exc:
                        progress.update(task, advance=1, description=f"搜索失败: {winget_pkg.name}")
                        self.console.print(f"⚠️ 搜索 {winget_pkg.name} 时出错: {exc}", style="yellow")
        
        self.console.print(f"🔍 多进程搜索完成，使用了 {max_workers} 个进程", style="blue")
        self.matches = matches
        return matches
    
    def display_matches(self):
        """显示找到的匹配项"""
        if not self.matches:
            self.console.print("❌ 没有找到任何匹配的包", style="red")
            return
        
        self.console.print(f"\n🎯 找到 {len(self.matches)} 个包有匹配项:", style="green bold")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Winget包", style="cyan", no_wrap=True)
        table.add_column("版本", style="yellow")
        table.add_column("Scoop匹配", style="green")
        table.add_column("Bucket", style="blue")
        table.add_column("描述", style="dim")
        
        for winget_pkg, scoop_matches in self.matches:
            for i, scoop_pkg in enumerate(scoop_matches):
                winget_name = winget_pkg.name if i == 0 else ""
                winget_version = winget_pkg.version if i == 0 else ""
                
                table.add_row(
                    winget_name,
                    winget_version,
                    scoop_pkg.name,
                    scoop_pkg.bucket,
                    scoop_pkg.description[:50] + "..." if len(scoop_pkg.description) > 50 else scoop_pkg.description
                )
        
        self.console.print(table)
    
    def interactive_install(self):
        """交互式安装选择的包"""
        if not self.matches:
            return
        
        self.console.print("\n🔧 开始交互式安装过程", style="blue bold")
        
        for winget_pkg, scoop_matches in self.matches:
            # 显示当前包信息
            panel_content = f"Winget包: [cyan]{winget_pkg.name}[/cyan] (版本: {winget_pkg.version})\n"
            panel_content += f"找到 {len(scoop_matches)} 个Scoop匹配项:"
            
            for i, scoop_pkg in enumerate(scoop_matches, 1):
                panel_content += f"\n{i}. [green]{scoop_pkg.bucket}/{scoop_pkg.name}[/green]"
                if scoop_pkg.description:
                    panel_content += f" - {scoop_pkg.description[:80]}"
            
            self.console.print(Panel(panel_content, title="包匹配信息", border_style="blue"))
            
            # 询问是否要安装
            if not Confirm.ask(f"是否要安装 [cyan]{winget_pkg.name}[/cyan] 的Scoop版本?"):
                continue
            
            # 如果有多个匹配项，让用户选择
            if len(scoop_matches) > 1:
                self.console.print("请选择要安装的版本:")
                for i, scoop_pkg in enumerate(scoop_matches, 1):
                    self.console.print(f"{i}. {scoop_pkg.bucket}/{scoop_pkg.name}")
                
                while True:
                    try:
                        choice = Prompt.ask("请输入选择 (1-{})".format(len(scoop_matches)), default="1")
                        choice_idx = int(choice) - 1
                        if 0 <= choice_idx < len(scoop_matches):
                            selected_pkg = scoop_matches[choice_idx]
                            break
                        else:
                            self.console.print("❌ 无效选择", style="red")
                    except ValueError:
                        self.console.print("❌ 请输入数字", style="red")
            else:
                selected_pkg = scoop_matches[0]
              # 安装选择的包
            self.install_scoop_package(selected_pkg, winget_pkg)
    
    def install_scoop_package(self, scoop_pkg: ScoopPackage, winget_pkg: WingetPackage):
        """安装scoop包"""
        package_name = f"{scoop_pkg.bucket}/{scoop_pkg.name}"
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task(f"安装 {package_name}...", total=None)
            
            try:
                # 首先确保bucket已添加，尝试多种命令方式
                bucket_commands = [
                    ["scoop", "bucket", "add", scoop_pkg.bucket],
                    ["powershell", "-c", f"scoop bucket add {scoop_pkg.bucket}"],
                    ["pwsh", "-c", f"scoop bucket add {scoop_pkg.bucket}"]
                ]
                
                for cmd in bucket_commands:
                    try:
                        subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True,
                            timeout=30,
                            shell=True if len(cmd) == 3 else False
                        )
                        break  # 如果成功就退出循环
                    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
                        continue
                
                # 安装包，也尝试多种命令方式
                install_commands = [
                    ["scoop", "install", package_name],
                    ["powershell", "-c", f"scoop install {package_name}"],
                    ["pwsh", "-c", f"scoop install {package_name}"]
                ]
                
                result = None
                for cmd in install_commands:
                    try:
                        result = subprocess.run(
                            cmd,
                            capture_output=True,
                            text=True,
                            timeout=300,
                            shell=True if len(cmd) == 3 else False
                        )
                        break  # 如果成功就退出循环
                    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
                        continue
                
                if result and result.returncode == 0:
                    progress.update(task, description=f"✓ {package_name} 安装成功")
                    self.console.print(f"✅ [green]{package_name}[/green] 安装成功!", style="green")
                    
                    # 询问是否卸载winget版本
                    if Confirm.ask(f"是否卸载winget版本的 [cyan]{winget_pkg.name}[/cyan]?"):
                        self.uninstall_winget_package(winget_pkg)
                else:
                    self.console.print(f"❌ [red]{package_name}[/red] 安装失败:", style="red")
                    if result:
                        self.console.print(result.stderr)
                    
            except subprocess.TimeoutExpired:
                self.console.print(f"❌ 安装 {package_name} 超时", style="red")
            except Exception as e:
                self.console.print(f"❌ 安装 {package_name} 失败: {e}", style="red")
    
    def uninstall_winget_package(self, winget_pkg: WingetPackage):
        """卸载winget包"""
        try:
            result = subprocess.run(
                ["winget", "uninstall", winget_pkg.id, "--silent"],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                self.console.print(f"✅ Winget版本的 [cyan]{winget_pkg.name}[/cyan] 卸载成功!", style="green")
            else:
                self.console.print(f"❌ 卸载winget版本的 {winget_pkg.name} 失败", style="red")
                self.console.print(result.stderr)
                
        except subprocess.TimeoutExpired:
            self.console.print(f"❌ 卸载 {winget_pkg.name} 超时", style="red")
        except subprocess.CalledProcessError as e:
            self.console.print(f"❌ 卸载 {winget_pkg.name} 失败: {e}", style="red")
    
    def run(self):
        """运行迁移过程"""
        self.console.print("🚀 Winget到Scoop迁移工具", style="bold blue")
        self.console.print("=" * 50)
          # 检查必要工具
        if not self.check_prerequisites():
            return
        
        # 获取winget包列表
        packages = self.get_winget_packages()
        if not packages:
            self.console.print("❌ 没有找到winget安装的包", style="red")
            return
        
        self.console.print(f"📦 找到 {len(packages)} 个winget包")
        
        # 查找匹配项
        matches = self.find_matches()
        
        # 显示匹配结果
        self.display_matches()
        
        # 交互式安装
        if matches and Confirm.ask("\n是否开始交互式安装过程?"):
            self.interactive_install()
        
        self.console.print("\n🎉 迁移过程完成!", style="green bold")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Winget到Scoop迁移工具")
    parser.add_argument("--dry-run", action="store_true", help="只显示匹配项，不进行安装")
    args = parser.parse_args()
    
    migrator = WingetToScoopMigrator()
    
    try:
        migrator.run()
    except KeyboardInterrupt:
        console.print("\n❌ 用户取消操作", style="yellow")
    except Exception as e:
        console.print(f"❌ 发生错误: {e}", style="red")
        raise

if __name__ == "__main__":
    main()