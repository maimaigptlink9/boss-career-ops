"""验证 dashboard 模块导入错误的根因分析"""

import subprocess
import sys


def test_import_dashboard_before_fix():
    """复现修复前的 ImportError"""
    # 当前 __init__.py 中 import DashboardApp（不存在），应抛出 ImportError
    result = subprocess.run(
        [sys.executable, "-c", "from boss_career_ops.dashboard import DashboardApp"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, "Expected ImportError, but import succeeded"
    assert "ImportError" in result.stderr or "cannot import name" in result.stderr, (
        f"Expected ImportError, got:\nstderr={result.stderr}\nstdout={result.stdout}"
    )


def test_import_dashboard_direct():
    """测试直接从 app.py 导入（绕过 __init__.py）"""
    result = subprocess.run(
        [sys.executable, "-c", "from boss_career_ops.dashboard.app import BossCareerOpsApp; print('OK')"],
        capture_output=True,
        text=True,
    )
    # 由于 __init__.py 先执行且报错，这个也会失败
    assert result.returncode != 0, "Expected import to fail due to __init__.py"


def test_init_exports_correct_name():
    """验证修复后：__init__.py 能正确导出 BossCareerOpsApp"""
    result = subprocess.run(
        [sys.executable, "-c", "from boss_career_ops.dashboard import BossCareerOpsApp; print('OK')"],
        capture_output=True,
        text=True,
    )
    if "OK" not in result.stdout:
        print(f"STILL FAILING: stderr={result.stderr}")
    assert result.returncode == 0, f"Expected successful import, got:\nstderr={result.stderr}"


if __name__ == "__main__":
    print("=== Test 1: Reproduce ImportError (should fail) ===")
    try:
        test_import_dashboard_before_fix()
        print("PASS: ImportError reproduced as expected\n")
    except AssertionError as e:
        print(f"SKIP: {e}\n")

    print("=== Test 2: Direct import also fails due to __init__.py ===")
    try:
        test_import_dashboard_direct()
        print("PASS: Direct import also blocked by __init__.py\n")
    except AssertionError as e:
        print(f"SKIP: {e}\n")

    print("=== Test 3: __init__.py exports correct name (should pass after fix) ===")
    try:
        test_init_exports_correct_name()
        print("PASS: __init__.py correctly exports BossCareerOpsApp\n")
    except AssertionError as e:
        print(f"FAIL: {e}\n")
