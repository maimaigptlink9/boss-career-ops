"""验证 dashboard 模块导入正常"""

import subprocess
import sys


def test_import_dashboard_direct():
    """测试直接从 app.py 导入"""
    result = subprocess.run(
        [sys.executable, "-c", "from boss_career_ops.dashboard.app import BossCareerOpsApp; print('OK')"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Expected successful import, got:\nstderr={result.stderr}"
    assert "OK" in result.stdout


def test_init_exports_correct_name():
    """验证 __init__.py 能正确导出 BossCareerOpsApp"""
    result = subprocess.run(
        [sys.executable, "-c", "from boss_career_ops.dashboard import BossCareerOpsApp; print('OK')"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Expected successful import, got:\nstderr={result.stderr}"
    assert "OK" in result.stdout
