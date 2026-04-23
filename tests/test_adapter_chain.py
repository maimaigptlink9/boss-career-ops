"""
防御性测试：防止适配器注册链路断裂导致 bco doctor 等基础命令崩溃

历史 bug：boss/search_filters.py 缺失 → BossAdapter 导入失败 → registry 静默吞错
→ 注册表空 → get_active_adapter() 抛 ValueError → bco doctor 崩溃

本测试文件覆盖三个防御层：
1. BossAdapter 顶层导入链完整性（任何 import 缺失立即暴露）
2. 适配器注册表非空断言（_auto_register 后必须有 boss）
3. registry 不再静默吞错（ImportError 必须有 warning 级别日志）
"""
import ast
import importlib
import logging
from pathlib import Path
from unittest.mock import patch

import pytest


class TestBossAdapterImportChain:
    """验证 BossAdapter 的所有顶层 import 均可解析"""

    @pytest.fixture
    def adapter_imports(self):
        adapter_path = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "boss_career_ops"
            / "platform"
            / "adapters"
            / "boss"
            / "adapter.py"
        )
        source = adapter_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("boss_career_ops."):
                imports.append(node.module)
        return imports

    def test_adapter_top_level_imports_resolvable(self, adapter_imports):
        """BossAdapter 中所有顶层 from boss_career_ops.xxx import 均可导入"""
        assert adapter_imports, "未从 adapter.py 提取到任何导入"
        errors = []
        for module_path in adapter_imports:
            try:
                importlib.import_module(module_path)
            except ImportError as e:
                errors.append(f"模块 {module_path} 导入失败: {e}")
        assert not errors, "BossAdapter 导入链断裂:\n" + "\n".join(f"  - {e}" for e in errors)

    def test_boss_adapter_directly_importable(self):
        """BossAdapter 本身可直接导入（最关键的断言）"""
        from boss_career_ops.platform.adapters.boss.adapter import BossAdapter
        assert BossAdapter is not None

    def test_search_filters_module_importable(self):
        """boss.search_filters 模块可导入且导出关键函数"""
        from boss_career_ops.boss.search_filters import (
            build_search_params,
            filter_by_welfare,
            get_city_code,
            CITY_MAP,
            EXPERIENCE_MAP,
            EDUCATION_MAP,
            JOB_TYPE_MAP,
            SCALE_MAP,
            FINANCE_MAP,
            SALARY_MAP,
        )
        assert len(CITY_MAP) > 0
        assert callable(build_search_params)
        assert callable(filter_by_welfare)
        assert callable(get_city_code)


class TestAdapterRegistryIntegrity:
    """验证适配器注册表在正常情况下必须非空"""

    def test_auto_register_populates_boss(self):
        """_auto_register 后注册表必须包含 boss 平台"""
        from boss_career_ops.platform.registry import reset_adapter, get_registered_platforms, _auto_register
        reset_adapter()
        _auto_register()
        platforms = get_registered_platforms()
        assert "boss" in platforms, f"自动注册后注册表缺少 boss，当前: {platforms}"

    def test_get_active_adapter_succeeds(self):
        """get_active_adapter 在正常环境下必须成功返回 BossAdapter 实例"""
        from boss_career_ops.platform.registry import reset_adapter, get_active_adapter
        from boss_career_ops.platform.adapters.boss.adapter import BossAdapter
        reset_adapter()
        adapter = get_active_adapter()
        assert isinstance(adapter, BossAdapter)

    def test_registry_not_empty_after_auto_register(self):
        """注册表在 _auto_register 后不能为空（防御性断言）"""
        from boss_career_ops.platform.registry import reset_adapter, get_registered_platforms, _auto_register
        reset_adapter()
        _auto_register()
        platforms = get_registered_platforms()
        assert len(platforms) >= 1, "自动注册后注册表为空，说明适配器导入链断裂"

    def test_auto_register_idempotent(self):
        """重复调用 _auto_register 不会重复注册"""
        from boss_career_ops.platform.registry import reset_adapter, get_registered_platforms, _auto_register
        reset_adapter()
        _auto_register()
        count_before = len(get_registered_platforms())
        _auto_register()
        count_after = len(get_registered_platforms())
        assert count_before == count_after


class TestRegistryImportErrorVisibility:
    """验证 registry.py 不再静默吞掉 ImportError"""

    def test_auto_register_logs_warning_on_import_error(self, caplog):
        """当 BossAdapter 导入失败时，必须产生 warning 级别日志"""
        from boss_career_ops.platform.registry import reset_adapter, _auto_register
        reset_adapter()
        with patch("boss_career_ops.platform.adapters.boss.adapter.BossAdapter", create=True) as mock:
            with patch.dict("sys.modules", {"boss_career_ops.platform.adapters.boss.adapter": None}):
                with patch("importlib.import_module", side_effect=ImportError("模拟模块缺失")):
                    with caplog.at_level(logging.WARNING, logger="boss_career_ops.platform.registry"):
                        _auto_register()
        assert any("导入失败" in r.message for r in caplog.records), (
            "BossAdapter 导入失败时未产生 warning 日志，可能被静默吞掉"
        )

    def test_get_active_adapter_raises_value_error_on_empty_registry(self):
        """注册表为空且无法自动注册时 get_active_adapter 必须抛 ValueError"""
        from boss_career_ops.platform.registry import reset_adapter, get_active_adapter, _registry
        reset_adapter()
        _registry.clear()
        with patch("boss_career_ops.platform.registry._auto_register"):
            with pytest.raises(ValueError, match="不支持的平台"):
                get_active_adapter()


class TestAdapterTopLevelDependencies:
    """验证 BossAdapter 依赖的关键子模块均存在且可导入"""

    @pytest.mark.parametrize("module_path", [
        "boss_career_ops.boss.api.client",
        "boss_career_ops.boss.auth.manager",
        "boss_career_ops.boss.browser_client",
        "boss_career_ops.boss.search_filters",
        "boss_career_ops.bridge.client",
        "boss_career_ops.display.error_codes",
        "boss_career_ops.display.logger",
        "boss_career_ops.hooks.manager",
        "boss_career_ops.platform.adapter",
        "boss_career_ops.platform.field_mapper",
        "boss_career_ops.platform.models",
        "boss_career_ops.resume.upload",
    ])
    def test_dependency_module_importable(self, module_path):
        """BossAdapter 的每个顶层依赖模块必须可导入"""
        mod = importlib.import_module(module_path)
        assert mod is not None


class TestCommandsModuleCompleteness:
    """验证 CLI 引用的每个 commands 子模块都存在且包含所需的 run_* 函数"""

    @pytest.fixture
    def cli_command_modules(self):
        main_path = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "boss_career_ops"
            / "cli"
            / "main.py"
        )
        source = main_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("boss_career_ops.commands."):
                for alias in node.names:
                    modules.add((node.module, alias.name))
        return modules

    def test_all_command_modules_importable(self, cli_command_modules):
        """CLI 中每个延迟导入的 commands 模块必须可导入"""
        assert cli_command_modules, "未从 CLI main.py 提取到任何 commands 导入"
        errors = []
        for module_path, func_name in cli_command_modules:
            try:
                mod = importlib.import_module(module_path)
            except ImportError as e:
                errors.append(f"模块 {module_path} 不存在: {e}")
                continue
            if not hasattr(mod, func_name):
                errors.append(f"{module_path} 中不存在函数 {func_name}")
        assert not errors, "CLI 命令模块缺失:\n" + "\n".join(f"  - {e}" for e in errors)

    def test_commands_dir_no_orphan_modules(self, cli_command_modules):
        """commands/ 目录下不应有未注册到 CLI 的孤立模块（警告而非失败）"""
        commands_dir = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "boss_career_ops"
            / "commands"
        )
        existing = {f.stem for f in commands_dir.glob("*.py") if f.stem != "__init__"}
        referenced = {mod.split(".")[-1] for mod, _ in cli_command_modules}
        orphans = existing - referenced
        if orphans:
            import warnings
            warnings.warn(f"commands/ 中存在未注册到 CLI 的模块: {orphans}", stacklevel=1)
