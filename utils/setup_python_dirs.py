#!/usr/bin/env python3
"""
Python环境目录统一配置脚本
将pip、pipx、uv等工具的缓存和安装目录统一配置到 D:\1Dev\Python\ 下
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, List

def set_environment_variable(name: str, value: str, scope: str = "User") -> bool:
    """设置Windows环境变量"""
    try:
        # 使用PowerShell设置环境变量
        cmd = f'[Environment]::SetEnvironmentVariable("{name}", "{value}", "{scope}")'
        result = subprocess.run(
            ["powershell", "-Command", cmd], 
            capture_output=True, 
            text=True, 
            check=True
        )
        print(f"✓ 设置环境变量: {name} = {value}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ 设置环境变量失败 {name}: {e}")
        return False

def create_directory(path: str) -> bool:
    """创建目录"""
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        print(f"✓ 创建目录: {path}")
        return True
    except Exception as e:
        print(f"✗ 创建目录失败 {path}: {e}")
        return False

def main():
    """主函数"""
    print("🐍 Python环境目录统一配置脚本")
    print("=" * 50)
    
    # 基础目录
    base_dir = "D:\\1Dev\\Python"
    
    # 目录配置
    directories = {
        # pip相关
        "packages": f"{base_dir}\\packages",      # pip用户包目录
        "cache": f"{base_dir}\\cache",            # pip缓存目录
        
        # pipx相关  
        "pipx": f"{base_dir}\\pipx",              # pipx主目录
        "pipx_bin": f"{base_dir}\\pipx\\bin",     # pipx二进制目录
        
        # uv相关
        "uv_cache": f"{base_dir}\\uv_cache",      # uv缓存目录
        "uv_tool": f"{base_dir}\\uv_tool",        # uv工具目录
        
        # 虚拟环境
        "venvs": f"{base_dir}\\venvs",            # 虚拟环境目录
        
        # 临时目录
        "temp": f"{base_dir}\\temp",              # 临时目录
    }
    
    # 环境变量配置
    env_vars = {
        # pip配置
        "PYTHONUSERBASE": directories["packages"],
        "PIP_USER": "1",
        "PIP_CACHE_DIR": directories["cache"],
        
        # pipx配置
        "PIPX_HOME": directories["pipx"],
        "PIPX_BIN_DIR": directories["pipx_bin"],
        
        # uv配置
        "UV_CACHE_DIR": directories["uv_cache"],
        "UV_TOOL_DIR": directories["uv_tool"],
        
        # 虚拟环境配置
        "WORKON_HOME": directories["venvs"],
        
        # 临时目录
        "TMPDIR": directories["temp"],
        "TEMP": directories["temp"],
        "TMP": directories["temp"],
    }
    
    print("📁 创建目录结构...")
    success_dirs = 0
    for name, path in directories.items():
        if create_directory(path):
            success_dirs += 1
    
    print(f"\n📁 目录创建完成: {success_dirs}/{len(directories)}")
    
    print("\n🔧 设置环境变量...")
    success_vars = 0
    for name, value in env_vars.items():
        if set_environment_variable(name, value):
            success_vars += 1
    
    print(f"\n🔧 环境变量设置完成: {success_vars}/{len(env_vars)}")
    
    # 添加pipx bin目录到PATH
    pipx_bin = directories["pipx_bin"]
    print(f"\n🛤️  添加 {pipx_bin} 到 PATH...")
    
    try:
        # 获取当前PATH
        get_path_cmd = '[Environment]::GetEnvironmentVariable("PATH", "User")'
        result = subprocess.run(
            ["powershell", "-Command", get_path_cmd],
            capture_output=True,
            text=True,
            check=True
        )
        current_path = result.stdout.strip()
        
        # 检查是否已经在PATH中
        if pipx_bin not in current_path:
            new_path = f"{current_path};{pipx_bin}" if current_path else pipx_bin
            set_environment_variable("PATH", new_path)
            print(f"✓ 已添加到PATH: {pipx_bin}")
        else:
            print(f"✓ 已存在于PATH: {pipx_bin}")
    except Exception as e:
        print(f"✗ PATH设置失败: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 配置完成!")
    print(f"📂 Python开发目录: {base_dir}")
    print("\n📋 目录说明:")
    for name, path in directories.items():
        print(f"  {name:12}: {path}")
    
    print("\n⚠️  注意事项:")
    print("1. 请重启终端或重新加载环境变量")
    print("2. 可以使用 'refreshenv' 命令刷新环境变量")
    print("3. 旧的缓存文件可能需要手动清理")
    
    print("\n🧪 验证命令:")
    print("  python -m site --user-base")
    print("  pip config list")
    print("  uv cache dir")
    print("  pipx --help")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 程序执行出错: {e}")
        sys.exit(1)
