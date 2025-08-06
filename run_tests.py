#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试运行脚本 - 多策略交易跟踪系统

此脚本提供了运行不同类型测试的选项：
- 单元测试：测试单个方法和函数
- 功能测试：测试完整的业务流程
- 集成测试：测试系统各模块的集成
- 全部测试：运行所有测试

使用方法：
python run_tests.py [test_type]

test_type 选项：
- unit: 运行单元测试
- functional: 运行功能测试  
- integration: 运行集成测试
- all: 运行所有测试（默认）
"""

import sys
import unittest
import os
from datetime import datetime

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)


def print_banner(title):
    """打印测试横幅"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_summary(suite_name, result):
    """打印测试摘要"""
    print(f"\n{suite_name} 测试摘要:")
    print(f"  运行测试数: {result.testsRun}")
    print(f"  成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  失败: {len(result.failures)}")
    print(f"  错误: {len(result.errors)}")
    
    if result.failures:
        print(f"\n失败的测试:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print(f"\n错误的测试:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split('Exception:')[-1].strip()}")


def run_unit_tests():
    """运行单元测试"""
    print_banner("单元测试 - 核心功能测试")
    
    # 导入单元测试模块
    from tests.unit.test_trading_tracker import TestTradingTracker
    
    # 创建测试套件
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestTradingTracker))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print_summary("单元测试", result)
    return result.wasSuccessful()


def run_functional_tests():
    """运行功能测试"""
    print_banner("功能测试 - 业务流程测试")
    
    # 导入功能测试模块
    from tests.functional.test_trading_workflows import TestTradingWorkflows
    
    # 创建测试套件
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestTradingWorkflows))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print_summary("功能测试", result)
    return result.wasSuccessful()


def run_integration_tests():
    """运行集成测试"""
    print_banner("集成测试 - 系统集成测试")
    
    # 导入集成测试模块
    from tests.integration.test_system_integration import TestSystemIntegration
    
    # 创建测试套件
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestSystemIntegration))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print_summary("集成测试", result)
    return result.wasSuccessful()


def run_all_tests():
    """运行所有测试"""
    print_banner("多策略交易跟踪系统 - 完整测试套件")
    print(f"测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    overall_success = True
    
    # 运行各类测试
    test_types = [
        ("单元测试", run_unit_tests),
        ("功能测试", run_functional_tests),
        ("集成测试", run_integration_tests)
    ]
    
    for test_name, test_func in test_types:
        try:
            success = test_func()
            results[test_name] = "通过" if success else "失败"
            if not success:
                overall_success = False
        except Exception as e:
            results[test_name] = f"错误: {str(e)}"
            overall_success = False
    
    # 打印总体摘要
    print_banner("测试总体摘要")
    print(f"测试结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n各测试套件结果:")
    for test_name, result in results.items():
        status_icon = "✅" if result == "通过" else "❌"
        print(f"  {status_icon} {test_name}: {result}")
    
    print(f"\n整体测试结果: {'✅ 全部通过' if overall_success else '❌ 存在失败'}")
    
    if overall_success:
        print("\n🎉 恭喜！所有测试都通过了！")
        print("系统功能正常，质量达标。")
    else:
        print("\n⚠️  部分测试失败，请检查上述错误信息。")
        print("建议修复失败的测试后重新运行。")
    
    return overall_success


def print_help():
    """打印帮助信息"""
    print(__doc__)


def main():
    """主函数"""
    # 解析命令行参数
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
    else:
        test_type = 'all'
    
    # 检查参数有效性
    valid_types = ['unit', 'functional', 'integration', 'all', 'help', '-h', '--help']
    if test_type not in valid_types:
        print(f"错误: 无效的测试类型 '{test_type}'")
        print(f"有效选项: {', '.join(valid_types[:-3])}")
        return 1
    
    # 显示帮助
    if test_type in ['help', '-h', '--help']:
        print_help()
        return 0
    
    # 检查是否在虚拟环境中
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  警告: 建议在虚拟环境中运行测试")
        print("可以运行: source venv/bin/activate")
        print()
    
    # 运行相应的测试
    success = True
    
    if test_type == 'unit':
        success = run_unit_tests()
    elif test_type == 'functional':
        success = run_functional_tests()
    elif test_type == 'integration':
        success = run_integration_tests()
    elif test_type == 'all':
        success = run_all_tests()
    
    # 返回适当的退出代码
    return 0 if success else 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)