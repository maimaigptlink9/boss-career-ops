import re
from pathlib import Path

DELETED_COMMANDS = [
    "agent-evaluate",
    "agent-save",
    "rag-index",
    "rag-search",
    "mcp-server",
    "ai-config",
    "ai-evaluate",
    "ai-evaluate-batch",
]

SRC_DIR = Path(__file__).resolve().parent.parent / "src" / "boss_career_ops"


class TestNoDeletedCommandReferences:
    def test_no_deleted_commands_in_source(self):
        violations = []
        for f in SRC_DIR.rglob("*"):
            if f.suffix not in (".py", ".html", ".js", ".css"):
                continue
            content = f.read_text(encoding="utf-8", errors="replace")
            for cmd in DELETED_COMMANDS:
                if re.search(rf"\b{re.escape(cmd)}\b", content):
                    rel = f.relative_to(SRC_DIR)
                    violations.append(f"{rel}: 引用已删除命令 '{cmd}'")
        assert not violations, "源码中存在已删除命令的残留引用:\n" + "\n".join(violations)

    def test_no_deleted_command_imports_in_cli(self):
        main_py = SRC_DIR / "cli" / "main.py"
        content = main_py.read_text(encoding="utf-8")
        deleted_modules = [
            "agent_cmd",
            "agent_evaluate",
            "agent_save",
            "rag",
            "mcp_server",
            "ai_config",
            "ai_evaluate",
            "ai_evaluate_batch",
        ]
        for mod in deleted_modules:
            assert mod not in content, f"cli/main.py 仍导入已删除模块: {mod}"
