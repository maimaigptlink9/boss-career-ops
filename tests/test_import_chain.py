"""测试最小导入链路，复现项目运行失败问题"""
import sys
from pathlib import Path

# 确保 src 在路径中
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def test_import_main_cli():
    """测试 CLI 主入口可导入"""
    from boss_career_ops.cli.main import cli
    assert cli is not None


def test_import_all_commands():
    """测试所有命令模块可从包导入"""
    from boss_career_ops.commands import (
        run_doctor, run_setup, run_login, run_status, run_search, run_recommend,
        run_evaluate, run_auto_action, run_greet, run_batch_greet, run_apply,
        run_resume, run_chat, run_chatmsg, run_chat_summary, run_mark,
        run_exchange, run_pipeline, run_follow_up, run_digest, run_watch_add,
        run_watch_list, run_watch_remove, run_watch_run, run_shortlist,
        run_export, run_interview, run_negotiate, run_dashboard, run_ai_config,
    )
    assert run_doctor is not None
    assert run_setup is not None
    assert run_login is not None
    assert run_status is not None
    assert run_search is not None
    assert run_recommend is not None
    assert run_evaluate is not None
    assert run_auto_action is not None
    assert run_greet is not None
    assert run_batch_greet is not None
    assert run_apply is not None
    assert run_resume is not None
    assert run_chat is not None
    assert run_chatmsg is not None
    assert run_chat_summary is not None
    assert run_mark is not None
    assert run_exchange is not None
    assert run_pipeline is not None
    assert run_follow_up is not None
    assert run_digest is not None
    assert run_watch_add is not None
    assert run_watch_list is not None
    assert run_watch_remove is not None
    assert run_watch_run is not None


def test_evaluation_engine_init():
    """测试 EvaluationEngine 可初始化并评估"""
    from unittest.mock import patch
    from boss_career_ops.evaluator.engine import EvaluationEngine
    from boss_career_ops.config.settings import Settings, Profile
    with patch.object(Settings, '__init__', lambda self, *a, **kw: None):
        settings = Settings()
        settings.profile = Profile()
        settings.cv_content = ""
        engine = EvaluationEngine()
        engine._settings = settings
        result = engine.evaluate({"jobName": "测试"})
        assert "total_score" in result
        assert 0.0 <= result["total_score"] <= 5.0


def test_dependency_declaration_consistency():
    """测试 pyproject.toml 中的依赖声明与实际代码使用一致"""
    import re
    project_root = Path(__file__).resolve().parents[1]
    pyproject_path = project_root / "pyproject.toml"
    with open(pyproject_path, "r", encoding="utf-8") as f:
        pyproject_content = f.read()

    deps_section = re.search(r'dependencies\s*=\s*\[(.*?)\]', pyproject_content, re.DOTALL)
    assert deps_section, "pyproject.toml 中未找到 dependencies"
    deps_text = deps_section.group(1)

    dep_names = re.findall(r'"([^">=]+)', deps_text)

    assert "rookiepy" in dep_names, "pyproject.toml 应声明 rookiepy（代码中使用 rookiepy）"
    assert "browser-cookie3" not in dep_names, "pyproject.toml 不应声明 browser-cookie3（代码中未使用）"


def test_doctor_package_list_consistency():
    """测试 doctor.py 中的包列表与 pyproject.toml 声明一致"""
    from boss_career_ops.commands.doctor import REQUIRED_PACKAGES

    assert "rookiepy" in REQUIRED_PACKAGES, "doctor.py 应检查 rookiepy"
    assert "browser_cookie3" not in REQUIRED_PACKAGES, "doctor.py 不应检查 browser_cookie3"
    assert "portalocker" in REQUIRED_PACKAGES, "doctor.py 应检查 portalocker"