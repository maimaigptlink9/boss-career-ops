import json
import io
import tempfile
from pathlib import Path
from unittest.mock import patch

from boss_career_ops.display.output import format_envelope, output_json, output_error, SCHEMA_VERSION
from boss_career_ops.display.logger import get_logger, mask_sensitive, _mask_value, _is_sensitive_key, SensitiveFilter


class TestFormatEnvelope:
    def test_success_envelope(self):
        result = format_envelope(ok=True, command="search", data=[1, 2, 3])
        assert result["ok"] is True
        assert result["command"] == "search"
        assert result["data"] == [1, 2, 3]
        assert result["schema_version"] == SCHEMA_VERSION
        assert result["error"] is None
        assert result["pagination"] is None

    def test_error_envelope(self):
        result = format_envelope(
            ok=False,
            command="login",
            error={"message": "failed", "code": "AUTH_ERROR"},
        )
        assert result["ok"] is False
        assert result["error"]["code"] == "AUTH_ERROR"

    def test_with_pagination(self):
        result = format_envelope(
            ok=True,
            command="search",
            data=[],
            pagination={"page": 1, "has_more": True},
        )
        assert result["pagination"]["page"] == 1

    def test_default_hints(self):
        result = format_envelope(ok=True, command="test")
        assert result["hints"] == {}


class TestOutputJson:
    def test_output_json_prints(self, capsys):
        output_json(command="test", data={"key": "val"})
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["ok"] is True
        assert parsed["command"] == "test"
        assert parsed["data"]["key"] == "val"

    def test_output_json_to_file(self, tmp_path):
        out_file = tmp_path / "result.json"
        output_json(command="search", data=[{"name": "测试职位"}], output=str(out_file))
        assert out_file.exists()
        parsed = json.loads(out_file.read_text(encoding="utf-8"))
        assert parsed["ok"] is True
        assert parsed["data"][0]["name"] == "测试职位"

    def test_output_json_to_file_creates_parent_dirs(self, tmp_path):
        out_file = tmp_path / "sub" / "dir" / "result.json"
        output_json(command="test", data=[], output=str(out_file))
        assert out_file.exists()

    def test_output_json_no_file_still_prints(self, capsys):
        output_json(command="test", data="hello")
        captured = capsys.readouterr()
        assert "hello" in captured.out


class TestOutputError:
    def test_output_error_prints_stdout(self, capsys):
        output_error(command="test", message="error msg", code="ERR")
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["ok"] is False
        assert parsed["error"]["message"] == "error msg"

    def test_output_error_to_file(self, tmp_path):
        out_file = tmp_path / "error.json"
        output_error(command="search", message="风控拦截", code="RISK_BLOCKED", output=str(out_file))
        assert out_file.exists()
        parsed = json.loads(out_file.read_text(encoding="utf-8"))
        assert parsed["ok"] is False
        assert parsed["error"]["message"] == "风控拦截"


class TestMaskSensitive:
    def test_mask_dict(self):
        data = {"token": "abc123456", "name": "张三"}
        result = mask_sensitive(data)
        assert result["name"] == "张三"
        assert "abc1" in result["token"]
        assert "***" in result["token"]

    def test_mask_nested(self):
        data = {"outer": {"cookie": "secret_val"}}
        result = mask_sensitive(data)
        assert "***" in result["outer"]["cookie"]

    def test_mask_list(self):
        data = [{"password": "mypass123"}, {"safe": "ok"}]
        result = mask_sensitive(data)
        assert "***" in result[0]["password"]
        assert result[1]["safe"] == "ok"

    def test_non_dict_passthrough(self):
        assert mask_sensitive("string") == "string"
        assert mask_sensitive(42) == 42


class TestMaskValue:
    def test_short_value(self):
        assert _mask_value("ab") == "***"

    def test_long_value(self):
        result = _mask_value("abcdefgh")
        assert result.startswith("abcd")
        assert result.endswith("***")


class TestIsSensitiveKey:
    def test_sensitive_keys(self):
        assert _is_sensitive_key("token")
        assert _is_sensitive_key("Cookie")
        assert _is_sensitive_key("Authorization")

    def test_safe_key(self):
        assert not _is_sensitive_key("name")
        assert not _is_sensitive_key("city")


class TestGetLogger:
    def test_returns_logger(self):
        logger = get_logger("test_module")
        assert logger.name == "test_module"

    def test_logger_has_handler(self):
        logger = get_logger("test_handler")
        assert len(logger.handlers) > 0


class TestSensitiveFilter:
    def test_filter_mask_string(self):
        f = SensitiveFilter()
        import logging
        record = logging.LogRecord("t", 0, "", 0, "token=abc123", (), None)
        f.filter(record)
        assert "abc123" not in record.msg
