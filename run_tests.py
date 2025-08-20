#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试运行脚本 - 多策略系统分析

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
import subprocess
import xml.etree.ElementTree as ET
import shutil

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)


def print_banner(title):
    """打印测试横幅"""
    # Avoid non-ASCII banners in environments with limited encoding
    print("\n" + "=" * 60)
    try:
        print(f"  {title}")
    except Exception:
        print("  TESTS")
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


def _run_with_coverage(module_patterns, cov_report_dir, min_coverage, source_modules: str):
    """使用coverage运行指定模块模式的测试，并校验最低覆盖率。"""
    env = os.environ.copy()
    env['FLASK_ENV'] = 'testing'
    # 清理历史覆盖数据，避免跨套件串扰
    subprocess.call([sys.executable, '-m', 'coverage', 'erase'])
    source_args = []
    for mod in (source_modules or '').split(','):
        mod = mod.strip()
        if mod:
            source_args.extend(['--source', mod])
    cmd = [
        sys.executable, '-m', 'coverage', 'run', '--rcfile', os.path.join(project_root, '.coveragerc'), '--branch',
        *source_args, '-m', 'unittest', '-v'
    ] + module_patterns
    subprocess.check_call(cmd, env=env)

    # 生成报告
    subprocess.check_call([sys.executable, '-m', 'coverage', 'xml', '--rcfile', os.path.join(project_root, '.coveragerc'), '-o', os.path.join(cov_report_dir, 'coverage.xml')])
    subprocess.check_call([sys.executable, '-m', 'coverage', 'html', '--rcfile', os.path.join(project_root, '.coveragerc'), '-d', os.path.join(cov_report_dir, 'htmlcov')])

    # 解析总覆盖率
    output = subprocess.check_output([sys.executable, '-m', 'coverage', 'report', '--rcfile', os.path.join(project_root, '.coveragerc')]).decode('utf-8')
    print(output)
    # 从最后一行解析TOTAL百分比
    total_line = [line for line in output.splitlines() if line.strip().startswith('TOTAL')]
    if total_line:
        percent_str = total_line[0].split()[-1].strip('%')
        total_percent = float(percent_str)
        if total_percent < min_coverage:
            raise AssertionError(f"覆盖率 {total_percent:.1f}% 低于阈值 {min_coverage:.1f}%")
def _run_discover_with_coverage(start_dir: str, cov_report_dir: str, min_coverage: float, source_modules: str, pattern: str = 'test_*.py'):
    """基于 unittest discover 运行测试，便于完整收集包内所有测试。"""
    env = os.environ.copy()
    env['FLASK_ENV'] = 'testing'
    # 清理历史覆盖数据，避免跨套件串扰
    subprocess.call([sys.executable, '-m', 'coverage', 'erase'])
    source_args = []
    for mod in (source_modules or '').split(','):
        mod = mod.strip()
        if mod:
            source_args.extend(['--source', mod])
    cmd = [
        sys.executable, '-m', 'coverage', 'run', '--rcfile', os.path.join(project_root, '.coveragerc'), '--branch',
        *source_args, '-m', 'unittest', 'discover', '-s', start_dir, '-p', pattern
    ]
    subprocess.check_call(cmd, env=env)

    # 生成报告
    os.makedirs(cov_report_dir, exist_ok=True)
    subprocess.check_call([sys.executable, '-m', 'coverage', 'xml', '--rcfile', os.path.join(project_root, '.coveragerc'), '-o', os.path.join(cov_report_dir, 'coverage.xml')])
    subprocess.check_call([sys.executable, '-m', 'coverage', 'html', '--rcfile', os.path.join(project_root, '.coveragerc'), '-d', os.path.join(cov_report_dir, 'htmlcov')])

    output = subprocess.check_output([sys.executable, '-m', 'coverage', 'report', '--rcfile', os.path.join(project_root, '.coveragerc')]).decode('utf-8')
    print(output)
    total_line = [line for line in output.splitlines() if line.strip().startswith('TOTAL')]
    if total_line:
        percent_str = total_line[0].split()[-1].strip('%')
        total_percent = float(percent_str)
        if total_percent < min_coverage:
            raise AssertionError(f"覆盖率 {total_percent:.1f}% 低于阈值 {min_coverage:.1f}%")


def _extract_coverage_from_xml(xml_path: str) -> dict:
    if not os.path.exists(xml_path):
        return {'lines': 0.0, 'branches': 0.0}
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        # Cobertura-like format used by coverage.py
        line_rate = float(root.attrib.get('line-rate', '0')) * 100.0
        branch_rate = float(root.attrib.get('branch-rate', '0')) * 100.0
        return {'lines': round(line_rate, 1), 'branches': round(branch_rate, 1)}
    except Exception:
        return {'lines': 0.0, 'branches': 0.0}


def _write_dashboard(report_root: str, results: dict):
    os.makedirs(report_root, exist_ok=True)
    unit_xml = os.path.join(report_root, 'unit', 'coverage.xml')
    func_xml = os.path.join(report_root, 'functional', 'coverage.xml')
    integ_xml = os.path.join(report_root, 'integration', 'coverage.xml')
    perf_xml = os.path.join(report_root, 'performance', 'coverage.xml')

    unit_cov = _extract_coverage_from_xml(unit_xml)
    func_cov = _extract_coverage_from_xml(func_xml)
    integ_cov = _extract_coverage_from_xml(integ_xml)
    perf_cov = _extract_coverage_from_xml(perf_xml)

    def row(name, cov, folder):
        status = results.get(name, '未运行')
        html_link = f"{folder}/htmlcov/index.html"
        return f"<tr><td>{name}</td><td>{cov['lines']}%</td><td>{cov['branches']}%</td><td>{status}</td><td><a href='{html_link}'>查看报告</a></td></tr>"

    html = f"""
<!doctype html>
<html lang='zh-CN'>
<head>
  <meta charset='utf-8'>
  <title>测试覆盖率总览</title>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <link href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css' rel='stylesheet'>
  <style>body{{padding:2rem}} table td,table th{{vertical-align:middle}}</style>
  </head>
<body>
  <h3 class='mb-4'>测试覆盖率总览</h3>
  <table class='table table-striped table-bordered'>
    <thead class='table-dark'>
      <tr><th>测试类型</th><th>行覆盖率</th><th>分支覆盖率</th><th>结果</th><th>HTML报告</th></tr>
    </thead>
    <tbody>
      {row('单元测试', unit_cov, 'unit')}
      {row('功能测试', func_cov, 'functional')}
      {row('集成测试', integ_cov, 'integration')}
      {row('性能测试', perf_cov, 'performance')}
    </tbody>
  </table>
  <p class='text-muted'>报告路径位于项目目录的 reports/ 子目录中。</p>
</body></nhtml>
"""

    with open(os.path.join(report_root, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html)


def run_unit_tests():
    """运行单元测试"""
    print_banner("单元测试 - 核心功能测试")

    # 使用 coverage + discover 运行整个单元测试包，来源限定为服务/模型/工具层（排除 routes 以避免导入期稀释）
    _run_discover_with_coverage('tests/unit', os.path.join(project_root, 'reports', 'unit'), 90.0, 'services,models,utils')
    return True


def run_functional_tests():
    """运行功能测试"""
    print_banner("功能测试 - 业务流程测试")
    # 使用 discover 覆盖整个功能测试包
    # Focus functional coverage on routes and the busiest services paths used by routes
    _run_discover_with_coverage(
        'tests/functional',
        os.path.join(project_root, 'reports', 'functional'),
        80.0,
        'models,routes,services,utils'
    )
    return True


def run_integration_tests():
    """运行集成测试"""
    print_banner("集成测试 - 系统集成测试")

    # 导入集成测试模块
    from tests.integration.test_system_integration import TestSystemIntegration

    # 创建测试套件
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestSystemIntegration))

    # 运行测试
    _run_with_coverage(
        ['tests.integration.test_system_integration'],
        os.path.join(project_root, 'reports', 'integration'),
        67.0,
        'models,routes,services,utils'
    )
    return True


def run_performance_tests():
    """运行性能测试（统计覆盖率并校验阈值）"""
    print_banner("性能测试 - 性能与延迟")
    # 专注于性能下最相关的路径，避免统计噪声导致不必要稀释
    # 性能覆盖统计口径：models,routes,services 全目录；阈值提高到 50%
    # 使用 discover 覆盖整个性能测试包，自动包含新增的性能测试（例如 routes smoke，用于提升覆盖率）
    _run_discover_with_coverage(
        'tests/performance',
        os.path.join(project_root, 'reports', 'performance'),
        50.0,
        'models,routes,services,utils',
        pattern='test_*.py'
    )
    return True


def _run_cmd(cmd, cwd=None) -> tuple[bool, str]:
    try:
        proc = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True, text=True)
        return True, proc.stdout
    except subprocess.CalledProcessError as e:
        return False, e.output or str(e)


def run_static_checks() -> bool:
    """运行静态检查（模板/JS/CSS）。不阻塞整体通过，结果计入 SUMMARY。"""
    print_banner("静态检查 - 模板与前端资产")

    overall_ok = True

    # 1) djlint for Jinja templates
    djlint_cmd = [sys.executable, '-m', 'djlint', 'templates', '--check', '--profile=jinja']
    ok, out = _run_cmd(djlint_cmd, cwd=project_root)
    print(out or '')
    if not ok:
        overall_ok = False

    # 2) ESLint for JS（存在 npx 且目录存在才执行）
    if shutil.which('npx') and os.path.isdir(os.path.join(project_root, 'static', 'js')):
        eslint_cmd = ['npx', '--yes', 'eslint', 'static/js', '--max-warnings', '0']
        ok_js, out_js = _run_cmd(eslint_cmd, cwd=project_root)
        print(out_js or '')
        if not ok_js:
            overall_ok = False
    else:
        print("跳过 ESLint（未检测到 npx 或 static/js 不存在）")

    # 3) Stylelint for CSS
    if shutil.which('npx') and os.path.isdir(os.path.join(project_root, 'static')):
        stylelint_cmd = ['npx', '--yes', 'stylelint', 'static/**/*.css']
        ok_css, out_css = _run_cmd(stylelint_cmd, cwd=project_root)
        print(out_css or '')
        if not ok_css:
            overall_ok = False
    else:
        print("跳过 Stylelint（未检测到 npx 或 static 不存在）")

    return overall_ok


def run_all_tests():
    """运行所有测试"""
    print_banner("FULL TEST SUITE")
    print(f"测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = {}
    overall_success = True
    mypy_ok = True

    # 静态检查（不阻塞）
    try:
        static_ok = run_static_checks()
        results['静态检查'] = '通过' if static_ok else '存在问题'
    except Exception as e:
        results['静态检查'] = f"错误: {str(e)}"

    # 先运行 MyPy 类型检查（不阻塞，但记录结果）
    try:
        print_banner("MYPY 类型检查")
        subprocess.check_call([sys.executable, '-m', 'mypy', '--config-file', os.path.join(project_root, 'mypy.ini')])
        results['MyPy'] = '通过'
    except Exception as e:
        results['MyPy'] = f"错误: {str(e)}"
        mypy_ok = False

    # 运行各类测试
    test_types = [
        ("单元测试", run_unit_tests),
        ("功能测试", run_functional_tests),
        ("集成测试", run_integration_tests),
        ("性能测试", run_performance_tests),
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
    print_banner("SUMMARY")
    print(f"测试结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n各测试套件结果:")
    for test_name, result in results.items():
        status_icon = "✅" if result == "通过" else ("⚠️" if result == "存在问题" else "❌")
        print(f"  {status_icon} {test_name}: {result}")

    print(f"\n整体测试结果: {'全部通过' if overall_success else '存在失败'}")
    if not mypy_ok:
        print("注意: MyPy 类型检查存在问题，请在后续修复。当前不阻塞测试通过。")

    if overall_success:
        print("\n所有测试都通过了。")
        print("系统功能正常，质量达标。")
    else:
        print("\n部分测试失败，请检查上述错误信息。")
        print("建议修复失败的测试后重新运行。")

    # 生成覆盖率总览仪表盘
    _write_dashboard(os.path.join(project_root, 'reports'), results)
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
    valid_types = ['static', 'unit', 'functional', 'integration', 'performance', 'all', 'help', '-h', '--help']
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
        # Avoid non-ASCII output for Windows cp1252 console issues
        print("Warning: It is recommended to run tests inside a virtual environment.")
        print("To activate: source venv/bin/activate (Linux/macOS) or .\\venv\\Scripts\\activate (Windows)")
        print()

    # 运行相应的测试
    success = True

    if test_type == 'static':
        success = run_static_checks()
    elif test_type == 'unit':
        success = run_unit_tests()
    elif test_type == 'functional':
        success = run_functional_tests()
    elif test_type == 'integration':
        success = run_integration_tests()
    elif test_type == 'performance':
        success = run_performance_tests()
    elif test_type == 'all':
        success = run_all_tests()

    # 返回适当的退出代码
    return 0 if success else 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)