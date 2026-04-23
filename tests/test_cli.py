from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from boss_career_ops.cli.main import cli


class TestCLI:
    def test_cli_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "BOSS直聘" in result.output

    def test_cli_version(self):
        from boss_career_ops import __version__
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_search_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["search", "--help"])
        assert result.exit_code == 0
        assert "keyword" in result.output.lower() or "KEYWORD" in result.output
        assert "--output" in result.output or "-o" in result.output

    def test_evaluate_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["evaluate", "--help"])
        assert result.exit_code == 0

    def test_greet_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["greet", "--help"])
        assert result.exit_code == 0

    def test_export_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["export", "--help"])
        assert result.exit_code == 0

    def test_doctor_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["doctor", "--help"])
        assert result.exit_code == 0
        assert "环境诊断" in result.output

    def test_status_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "--help"])
        assert result.exit_code == 0

    def test_login_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["login", "--help"])
        assert result.exit_code == 0
        assert "--profile" in result.output

    def test_pipeline_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["pipeline", "--help"])
        assert result.exit_code == 0

    def test_recommend_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["recommend", "--help"])
        assert result.exit_code == 0

    def test_resume_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["resume", "--help"])
        assert result.exit_code == 0

    def test_chat_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["chat", "--help"])
        assert result.exit_code == 0

    def test_bridge_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["bridge", "--help"])
        assert result.exit_code == 0

    def test_bridge_status_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["bridge", "status", "--help"])
        assert result.exit_code == 0

    def test_bridge_test_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["bridge", "test", "--help"])
        assert result.exit_code == 0

    def test_apply_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["apply", "--help"])
        assert result.exit_code == 0

    def test_interview_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["interview", "--help"])
        assert result.exit_code == 0

    def test_mark_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["mark", "--help"])
        assert result.exit_code == 0

    def test_setup_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["setup", "--help"])
        assert result.exit_code == 0

    def test_dashboard_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["dashboard", "--help"])
        assert result.exit_code == 0

    def test_agent_evaluate_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["agent-evaluate", "--help"])
        assert result.exit_code == 0

    def test_agent_save_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["agent-save", "--help"])
        assert result.exit_code == 0


class TestDoctorCommand:
    @patch("boss_career_ops.platform.registry.get_active_adapter")
    def test_doctor_runs_with_mocked_adapter(self, mock_get_adapter):
        mock_adapter = MagicMock()
        mock_adapter.check_auth_status.return_value = MagicMock(ok=True, message="Token 有效")
        mock_get_adapter.return_value = mock_adapter
        runner = CliRunner()
        result = runner.invoke(cli, ["doctor"])
        assert result.exit_code == 0
        assert "Python 版本" in result.output

    @patch("boss_career_ops.platform.registry.get_active_adapter")
    def test_doctor_detects_not_logged_in(self, mock_get_adapter):
        mock_adapter = MagicMock()
        mock_adapter.check_auth_status.return_value = MagicMock(ok=False, message="Token 无效", missing=[])
        mock_get_adapter.return_value = mock_adapter
        runner = CliRunner()
        result = runner.invoke(cli, ["doctor"])
        assert result.exit_code == 0
        assert "未登录" in result.output

    @patch("boss_career_ops.platform.registry.get_active_adapter")
    def test_doctor_handles_adapter_error(self, mock_get_adapter):
        mock_get_adapter.side_effect = ValueError("不支持的平台: boss，已注册平台: []")
        runner = CliRunner()
        result = runner.invoke(cli, ["doctor"])
        assert result.exit_code == 0
        assert "不支持的平台" in result.output


class TestRegistrySmoke:
    def test_boss_adapter_auto_register(self):
        from boss_career_ops.platform.registry import reset_adapter, get_registered_platforms, _auto_register
        reset_adapter()
        _auto_register()
        platforms = get_registered_platforms()
        assert "boss" in platforms

    def test_get_active_adapter_returns_boss(self):
        from boss_career_ops.platform.registry import reset_adapter, get_active_adapter
        from boss_career_ops.platform.adapters.boss.adapter import BossAdapter
        reset_adapter()
        adapter = get_active_adapter()
        assert isinstance(adapter, BossAdapter)
