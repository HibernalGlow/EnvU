#!/usr/bin/env python3
"""
Scoolp 模块测试脚本
用于验证模块结构和导入是否正常
"""

def test_imports():
    """测试所有模块是否可以正常导入"""
    print("🧪 测试 Scoolp 模块导入...")
    
    try:
        # 测试主模块
        print("  ✓ 导入 scoolp")
        import scoolp
        
        # 测试子模块
        print("  ✓ 导入 scoolp.__main__")
        from scoolp import __main__
        
        print("  ✓ 导入 scoolp.init")
        from scoolp import init
        
        print("  ✓ 导入 scoolp.clean")
        from scoolp import clean
        
        print("  ✓ 导入 scoolp.interactive")
        from scoolp import interactive
        
        print("\n✅ 所有模块导入成功！\n")
        return True
        
    except ImportError as e:
        print(f"\n❌ 导入失败: {e}\n")
        print("💡 提示: 请先安装依赖:")
        print("   cd LazyCommand/EnvU")
        print("   pip install -e .")
        return False


def test_structure():
    """测试模块结构"""
    print("📁 检查模块结构...")
    
    from pathlib import Path
    
    # 测试脚本在 src/scoolp/ 目录下，所以 parent 就是 scoolp 目录
    scoolp_dir = Path(__file__).parent
    
    required_files = [
        "__init__.py",
        "__main__.py",
        "init.py",
        "install.py",
        "sync.py",
        "clean.py",
        "interactive.py",
        "README.md"
    ]
    
    all_exist = True
    for file in required_files:
        file_path = scoolp_dir / file
        if file_path.exists():
            print(f"  ✓ {file}")
        else:
            print(f"  ✗ {file} (缺失)")
            all_exist = False
    
    if all_exist:
        print("\n✅ 所有必需文件都存在！\n")
    else:
        print("\n❌ 部分文件缺失\n")
    
    return all_exist


def test_typer_apps():
    """测试 Typer 应用是否正确配置"""
    print("🎯 检查 Typer 应用配置...")
    
    try:
        from scoolp.__main__ import app as main_app
        from scoolp.init import app as init_app
        from scoolp.install import app as install_app
        from scoolp.sync import app as sync_app
        from scoolp.clean import app as clean_app
        
        print("  ✓ main_app")
        print("  ✓ init_app")
        print("  ✓ install_app")
        print("  ✓ sync_app")
        print("  ✓ clean_app")
        
        print("\n✅ Typer 应用配置正确！\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Typer 应用配置错误: {e}\n")
        return False


def test_cli_entry():
    """测试 CLI 入口点"""
    print("🚀 检查 CLI 入口点...")
    
    try:
        from scoolp.__main__ import cli
        print("  ✓ cli() 函数存在")
        
        print("\n✅ CLI 入口点配置正确！\n")
        return True
        
    except Exception as e:
        print(f"\n❌ CLI 入口点错误: {e}\n")
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("Scoolp 模块验证测试")
    print("=" * 60)
    print()
    
    results = []
    
    # 测试模块结构
    results.append(("模块结构", test_structure()))
    
    # 测试导入
    results.append(("模块导入", test_imports()))
    
    # 如果导入成功，继续测试其他功能
    if results[-1][1]:
        results.append(("Typer 应用", test_typer_apps()))
        results.append(("CLI 入口点", test_cli_entry()))
    
    # 总结
    print("=" * 60)
    print("测试总结")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{name:20} {status}")
    
    print()
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("🎉 所有测试通过！")
        print()
        print("📝 下一步:")
        print("   1. 安装依赖: pip install -e .")
        print("   2. 运行命令: scoolp")
        print("   3. 查看帮助: scoolp --help")
        print()
    else:
        print("⚠️  部分测试失败，请检查上述错误信息")
        print()
    
    return all_passed


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)

