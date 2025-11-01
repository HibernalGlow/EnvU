#!/usr/bin/env python3
"""
Python环境配置测试脚本
测试Python环境是否正确配置到 D:\1Dev\Python\ 下
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

def test_directories() -> List[Tuple[str, bool, str]]:
    """测试目录结构"""
    print("🏗️  测试目录结构...")
    
    expected_dirs = {
        "基础目录": Path("D:/Dev/Python"),
        "用户包目录": Path("D:/Dev/Python/packages"),
        "pipx主目录": Path("D:/Dev/Python/pipx"),
        "pipx二进制目录": Path("D:/Dev/Python/pipx/bin"),
        "UV缓存目录": Path("D:/Dev/Python/uv_cache"),
        "pip缓存目录": Path("D:/Dev/Python/pip_cache"),
        "虚拟环境目录": Path("D:/Dev/Python/virtualenvs"),
    }
    
    results = []
    for name, path in expected_dirs.items():
        exists = path.exists()
        status = "✅ 存在" if exists else "❌ 不存在"
        print(f"   {name}: {path} - {status}")
        results.append((f"目录: {name}", exists, str(path)))
    
    return results

def test_environment_variables() -> List[Tuple[str, bool, str]]:
    """测试环境变量"""
    print("\n🔧 测试环境变量...")
    
    expected_vars = {
        "PYTHONUSERBASE": "D:\\1Dev\\Python\\packages",
        "PIP_USER": "1",
        "PIPX_HOME": "D:\\1Dev\\Python\\pipx",
        "PIPX_BIN_DIR": "D:\\1Dev\\Python\\pipx\\bin",
        "UV_CACHE_DIR": "D:\\1Dev\\Python\\uv_cache",
        "PIP_CACHE_DIR": "D:\\1Dev\\Python\\pip_cache",
        "WORKON_HOME": "D:\\1Dev\\Python\\virtualenvs",
    }
    
    results = []
    for var_name, expected_value in expected_vars.items():
        actual_value = os.environ.get(var_name)
        is_correct = actual_value == expected_value
        
        if is_correct:
            print(f"   ✅ {var_name} = {actual_value}")
        else:
            print(f"   ❌ {var_name} = {actual_value} (期望: {expected_value})")
        
        results.append((f"环境变量: {var_name}", is_correct, f"{actual_value} (期望: {expected_value})"))
    
    return results

def test_python_site() -> List[Tuple[str, bool, str]]:
    """测试Python站点配置"""
    print("\n🐍 测试Python站点配置...")
    
    results = []
    
    try:
        # 测试用户基础目录
        import site
        user_base = site.getusersitepackages().replace('site-packages', '').rstrip('\\/')
        expected_base = "D:\\1Dev\\Python\\packages"
        
        is_correct = user_base.lower() == expected_base.lower()
        status = "✅ 正确" if is_correct else "❌ 错误"
        print(f"   Python用户基础目录: {user_base} - {status}")
        results.append(("Python用户基础目录", is_correct, f"{user_base} (期望: {expected_base})"))
        
        # 测试用户站点包目录
        user_site = site.getusersitepackages()
        expected_site = "D:\\1Dev\\Python\\packages\\Lib\\site-packages"
        
        is_correct = user_site.lower() == expected_site.lower()
        status = "✅ 正确" if is_correct else "❌ 错误"
        print(f"   Python用户站点包目录: {user_site} - {status}")
        results.append(("Python用户站点包目录", is_correct, f"{user_site} (期望: {expected_site})"))
        
    except Exception as e:
        print(f"   ❌ Python站点配置测试失败: {e}")
        results.append(("Python站点配置", False, str(e)))
    
    return results

def test_command_availability() -> List[Tuple[str, bool, str]]:
    """测试命令可用性"""
    print("\n⚡ 测试命令可用性...")
    
    commands = ["python", "pip", "uv", "pipx"]
    results = []
    
    for cmd in commands:
        try:
            # 测试命令是否可用
            result = subprocess.run([cmd, "--version"], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=10)
            
            if result.returncode == 0:
                version = result.stdout.strip().split('\n')[0]
                print(f"   ✅ {cmd}: {version}")
                results.append((f"命令: {cmd}", True, version))
            else:
                print(f"   ❌ {cmd}: 执行失败")
                results.append((f"命令: {cmd}", False, "执行失败"))
                
        except FileNotFoundError:
            print(f"   ❌ {cmd}: 未找到命令")
            results.append((f"命令: {cmd}", False, "未找到命令"))
        except subprocess.TimeoutExpired:
            print(f"   ❌ {cmd}: 执行超时")
            results.append((f"命令: {cmd}", False, "执行超时"))
        except Exception as e:
            print(f"   ❌ {cmd}: {e}")
            results.append((f"命令: {cmd}", False, str(e)))
    
    return results

def test_path_priority() -> List[Tuple[str, bool, str]]:
    """测试PATH优先级"""
    print("\n🛤️  测试PATH优先级...")
    
    results = []
    
    try:
        # 测试Python可执行文件位置
        python_path = shutil.which("python")
        if python_path:
            print(f"   Python路径: {python_path}")
            # 检查是否使用了正确的Python
            if "scoop" in python_path.lower():
                results.append(("Python路径", True, f"使用Scoop Python: {python_path}"))
            else:
                results.append(("Python路径", False, f"可能不是Scoop Python: {python_path}"))
        else:
            results.append(("Python路径", False, "未找到Python"))
        
        # 测试pip路径
        pip_path = shutil.which("pip")
        if pip_path:
            print(f"   pip路径: {pip_path}")
            results.append(("pip路径", True, pip_path))
        else:
            results.append(("pip路径", False, "未找到pip"))
            
    except Exception as e:
        print(f"   ❌ PATH测试失败: {e}")
        results.append(("PATH测试", False, str(e)))
    
    return results

def run_functional_tests() -> List[Tuple[str, bool, str]]:
    """运行功能测试"""
    print("\n🧪 运行功能测试...")
    
    results = []
    
    try:
        # 测试pip用户安装
        print("   测试pip用户安装...")
        result = subprocess.run([
            "pip", "install", "--user", "requests", "--quiet", "--no-warn-script-location"
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("   ✅ pip用户安装测试成功")
            results.append(("pip用户安装", True, "成功安装requests"))
            
            # 尝试卸载
            subprocess.run(["pip", "uninstall", "requests", "-y", "--quiet"], 
                         capture_output=True, timeout=30)
        else:
            print(f"   ❌ pip用户安装测试失败: {result.stderr}")
            results.append(("pip用户安装", False, result.stderr))
            
    except subprocess.TimeoutExpired:
        print("   ❌ pip用户安装测试超时")
        results.append(("pip用户安装", False, "测试超时"))
    except Exception as e:
        print(f"   ❌ pip用户安装测试异常: {e}")
        results.append(("pip用户安装", False, str(e)))
    
    return results

def generate_report(all_results: List[List[Tuple[str, bool, str]]]) -> None:
    """生成测试报告"""
    print("\n📊 生成测试报告...")
    
    # 合并所有结果
    flat_results = []
    for result_group in all_results:
        flat_results.extend(result_group)
    
    # 统计
    total_tests = len(flat_results)
    passed_tests = sum(1 for _, passed, _ in flat_results if passed)
    failed_tests = total_tests - passed_tests
    
    # 生成报告内容
    report_content = f"""Python环境配置测试报告
==========================

测试时间: {os.popen('date /t').read().strip()} {os.popen('time /t').read().strip()}

测试概况:
---------
总测试数: {total_tests}
通过: {passed_tests}
失败: {failed_tests}
成功率: {(passed_tests/total_tests*100):.1f}%

详细结果:
---------
"""
    
    for test_name, passed, details in flat_results:
        status = "✅ PASS" if passed else "❌ FAIL"
        report_content += f"{status} {test_name}\n"
        if not passed:
            report_content += f"     详情: {details}\n"
    
    # 保存报告
    report_file = Path("D:/Dev/Python/test_report.txt")
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(report_content, encoding='utf-8')
    
    print(f"   ✅ 测试报告已保存: {report_file}")
    
    # 显示摘要
    print(f"\n📈 测试摘要:")
    print(f"   总测试数: {total_tests}")
    print(f"   通过: {passed_tests}")
    print(f"   失败: {failed_tests}")
    print(f"   成功率: {(passed_tests/total_tests*100):.1f}%")
    
    if failed_tests > 0:
        print(f"\n⚠️  发现 {failed_tests} 个问题，请检查配置！")
        return False
    else:
        print(f"\n🎉 所有测试通过！Python环境配置正确。")
        return True

def main():
    """主函数"""
    print("🧪 Python环境配置测试")
    print("=" * 50)
    
    try:
        all_results = []
        
        # 运行各项测试
        all_results.append(test_directories())
        all_results.append(test_environment_variables())
        all_results.append(test_python_site())
        all_results.append(test_command_availability())
        all_results.append(test_path_priority())
        all_results.append(run_functional_tests())
        
        # 生成报告
        success = generate_report(all_results)
        
        if not success:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
