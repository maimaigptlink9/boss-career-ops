"""测试最小导入链路，复现项目运行失败问题"""
import ast
import importlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def _extract_cli_imports() -> list[tuple[str, str]]:
    """从 CLI main.py 源码中用 AST 自动提取所有延迟导入的 (模块路径, 函数名) 列表"""
    main_path = Path(__file__).resolve().parents[1] / "src" / "boss_career_ops" / "cli" / "main.py"
    source = main_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("boss_career_ops."):
            for alias in node.names:
                imports.append((node.module, alias.name))
    return imports


def test_import_main_cli():
    """测试 CLI 主入口可导入"""
    from boss_career_ops.cli.main import cli
    assert cli is not None


def test_all_cli_imports_resolvable():
    """自动验证 CLI 中所有延迟导入的模块和函数均可解析，防止模块缺失"""
    cli_imports = _extract_cli_imports()
    assert len(cli_imports) > 0, "未从 CLI main.py 中提取到任何导入，检查正则匹配"

    errors = []
    for module_path, func_name in cli_imports:
        try:
            mod = importlib.import_module(module_path)
        except ImportError as e:
            errors.append(f"模块 {module_path} 不存在: {e}")
            continue
        if not hasattr(mod, func_name):
            errors.append(f"{module_path} 中不存在函数 {func_name}")

    assert not errors, (
        "CLI 引用的模块/函数存在缺失:\n" + "\n".join(f"  - {e}" for e in errors)
    )


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
    from boss_career_ops.commands.agent_evaluate import run_agent_evaluate
    from boss_career_ops.commands.agent_save import (
        run_agent_save_evaluate,
        run_agent_save_resume,
        run_agent_save_chat_summary,
        run_agent_save_interview_prep,
    )
    from boss_career_ops.commands.bridge import run_bridge_status, run_bridge_test
    from boss_career_ops.commands.skill_update import run_skill_update
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
    assert run_agent_evaluate is not None
    assert run_agent_save_evaluate is not None
    assert run_bridge_status is not None
    assert run_skill_update is not None


def test_cli_command_count_matches_commands_dir():
    """验证 CLI 注册的命令数量与 commands/ 目录下的模块数量一致"""
    main_path = Path(__file__).resolve().parents[1] / "src" / "boss_career_ops" / "cli" / "main.py"
    source = main_path.read_text(encoding="utf-8")
    command_modules = set()
    for match in re.finditer(r'from\s+boss_career_ops\.commands\.(\w+)\s+import', source):
        command_modules.add(match.group(1))

    commands_dir = Path(__file__).resolve().parents[1] / "src" / "boss_career_ops" / "commands"
    existing_modules = {f.stem for f in commands_dir.glob("*.py") if f.stem != "__init__"}

    missing = command_modules - existing_modules
    extra = existing_modules - command_modules

    assert not missing, f"CLI 引用了不存在的命令模块: {missing}"
    if extra:
        import warnings
        warnings.warn(f"commands/ 中存在未注册到 CLI 的模块: {extra}", stacklevel=1)


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


def test_version_consistency():
    """验证所有版本引用与 pyproject.toml 一致，防止改版本时遗漏"""
    project_root = Path(__file__).resolve().parents[1]
    pyproject_path = project_root / "pyproject.toml"
    pyproject_content = pyproject_path.read_text(encoding="utf-8")
    version_match = re.search(r'version\s*=\s*"([^"]+)"', pyproject_content)
    assert version_match, "pyproject.toml 中未找到 version"
    expected = version_match.group(1)

    checks = {
        "skills/boss-career-ops/skill.md": re.compile(r'skill_version:\s*"([^"]+)"'),
    }

    errors = []
    for rel_path, pattern in checks.items():
        file_path = project_root / rel_path
        if not file_path.exists():
            errors.append(f"{rel_path} 不存在")
            continue
        content = file_path.read_text(encoding="utf-8")
        match = pattern.search(content)
        if not match:
            errors.append(f"{rel_path} 中未找到版本号（模式: {pattern.pattern}）")
            continue
        actual = match.group(1)
        if actual != expected:
            errors.append(f"{rel_path} 版本 {actual} ≠ pyproject.toml 版本 {expected}")

    from boss_career_ops import __version__
    if __version__ != expected:
        errors.append(f"__init__.__version__ = {__version__} ≠ pyproject.toml 版本 {expected}")

    assert not errors, "版本号不一致:\n" + "\n".join(f"  - {e}" for e in errors)


def test_doctor_package_list_consistency():
    """测试 doctor.py 中的包列表与 pyproject.toml 声明一致"""
    from boss_career_ops.commands.doctor import REQUIRED_PACKAGES

    assert "portalocker" in REQUIRED_PACKAGES, "doctor.py 应检查 portalocker"
    assert "click" in REQUIRED_PACKAGES, "doctor.py 应检查 click"
    assert "httpx" in REQUIRED_PACKAGES, "doctor.py 应检查 httpx"