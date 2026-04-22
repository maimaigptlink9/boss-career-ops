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
    """测试所有命令模块可从子模块导入"""
    from boss_career_ops.commands.doctor import run_doctor
    from boss_career_ops.commands.setup import run_setup
    from boss_career_ops.commands.login import run_login
    from boss_career_ops.commands.status import run_status
    from boss_career_ops.commands.search import run_search
    from boss_career_ops.commands.recommend import run_recommend
    from boss_career_ops.commands.evaluate import run_evaluate
    from boss_career_ops.commands.greet import run_greet, run_batch_greet
    from boss_career_ops.commands.apply import run_apply
    from boss_career_ops.commands.resume import run_resume
    from boss_career_ops.commands.chat import run_chat
    from boss_career_ops.commands.chatmsg import run_chatmsg, run_chat_summary
    from boss_career_ops.commands.mark import run_mark
    from boss_career_ops.commands.pipeline import run_pipeline
    from boss_career_ops.commands.export import run_export
    from boss_career_ops.commands.interview import run_interview
    from boss_career_ops.commands.dashboard import run_dashboard
    assert run_doctor is not None
    assert run_setup is not None
    assert run_login is not None
    assert run_status is not None
    assert run_search is not None
    assert run_recommend is not None
    assert run_evaluate is not None
    assert run_greet is not None
    assert run_batch_greet is not None
    assert run_apply is not None
    assert run_resume is not None
    assert run_chat is not None
    assert run_chatmsg is not None
    assert run_chat_summary is not None
    assert run_mark is not None
    assert run_pipeline is not None


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

    for dep in dep_names:
        assert dep.strip(), f"空依赖名: {dep}"


def test_doctor_package_list_consistency():
    """测试 doctor.py 中的包列表与 pyproject.toml 声明一致"""
    from boss_career_ops.commands.doctor import REQUIRED_PACKAGES

    assert "portalocker" in REQUIRED_PACKAGES, "doctor.py 应检查 portalocker"
    assert "click" in REQUIRED_PACKAGES, "doctor.py 应检查 click"
    assert "httpx" in REQUIRED_PACKAGES, "doctor.py 应检查 httpx"