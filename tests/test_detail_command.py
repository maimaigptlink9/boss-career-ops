import json
from unittest.mock import patch

from click.testing import CliRunner

from boss_career_ops.cli.main import cli
from boss_career_ops.commands.detail import run_detail


class TestDetailCLIRegistration:
    def test_detail_command_registered(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["detail", "--help"])
        assert result.exit_code == 0
        assert "查看职位详情" in result.output
        assert "JOB_ID" in result.output or "job_id" in result.output.lower()


class TestDetailCommandNotFound:
    @patch("boss_career_ops.commands.detail.get_job_detail", return_value=None)
    def test_detail_outputs_error_when_job_not_found(self, mock_get_detail):
        runner = CliRunner()
        result = runner.invoke(cli, ["detail", "nonexistent_id"])
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["ok"] is False
        assert output["error"]["code"] == "NOT_FOUND"
        assert "职位不存在" in output["error"]["message"]
        mock_get_detail.assert_called_once_with("nonexistent_id")


class TestDetailCommandSuccess:
    @patch("boss_career_ops.commands.detail.get_job_detail")
    def test_detail_outputs_job_data_when_found(self, mock_get_detail):
        fake_job = {
            "job_id": "12345",
            "job_name": "Golang工程师",
            "company_name": "测试公司",
            "city": "深圳",
        }
        mock_get_detail.return_value = fake_job
        runner = CliRunner()
        result = runner.invoke(cli, ["detail", "12345"])
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["ok"] is True
        assert output["command"] == "detail"
        assert output["data"]["job_id"] == "12345"
        assert output["data"]["job_name"] == "Golang工程师"
        mock_get_detail.assert_called_once_with("12345")


class TestRunDetailDirect:
    @patch("boss_career_ops.commands.detail.get_job_detail", return_value=None)
    @patch("boss_career_ops.commands.detail.output_error")
    def test_run_detail_calls_output_error_on_none(self, mock_output_error, mock_get_detail):
        run_detail("missing_id")
        mock_get_detail.assert_called_once_with("missing_id")
        mock_output_error.assert_called_once_with(
            command="detail", message="职位不存在", code="NOT_FOUND"
        )

    @patch("boss_career_ops.commands.detail.get_job_detail")
    @patch("boss_career_ops.commands.detail.output_json")
    def test_run_detail_calls_output_json_on_success(self, mock_output_json, mock_get_detail):
        fake_job = {"job_id": "abc", "job_name": "Python开发"}
        mock_get_detail.return_value = fake_job
        run_detail("abc")
        mock_get_detail.assert_called_once_with("abc")
        mock_output_json.assert_called_once_with(command="detail", data=fake_job)
