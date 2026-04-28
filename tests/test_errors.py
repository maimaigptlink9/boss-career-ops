from boss_career_ops.errors import (
    BCOError,
    ConfigError,
    PlatformError,
    PipelineError,
    AuthError,
    EvaluationError,
    Result,
)
from boss_career_ops.web.server import app
from fastapi.testclient import TestClient


class TestBCOError:
    def test_bco_error_carries_message_and_code(self):
        err = BCOError("出错了", "TEST_ERROR")
        assert err.message == "出错了"
        assert err.code == "TEST_ERROR"
        assert str(err) == "出错了"

    def test_bco_error_default_code(self):
        err = BCOError("默认")
        assert err.code == "UNKNOWN"

    def test_config_error_is_bco_error(self):
        err = ConfigError("配置错误", "CONFIG_MISSING")
        assert isinstance(err, BCOError)
        assert err.message == "配置错误"
        assert err.code == "CONFIG_MISSING"

    def test_platform_error_is_bco_error(self):
        err = PlatformError("平台错误", "PLATFORM_DOWN")
        assert isinstance(err, BCOError)

    def test_pipeline_error_is_bco_error(self):
        err = PipelineError("流水线错误", "PIPELINE_FAIL")
        assert isinstance(err, BCOError)

    def test_auth_error_is_bco_error(self):
        err = AuthError("认证错误", "AUTH_EXPIRED")
        assert isinstance(err, BCOError)

    def test_evaluation_error_is_bco_error(self):
        err = EvaluationError("评估错误", "EVAL_FAIL")
        assert isinstance(err, BCOError)


class TestResult:
    def test_success_result(self):
        r = Result.success(data={"score": 4.2})
        assert r.ok is True
        assert r.data == {"score": 4.2}
        assert r.error is None
        assert r.code is None

    def test_failure_result(self):
        r = Result.failure(error="职位不存在", code="NOT_FOUND")
        assert r.ok is False
        assert r.error == "职位不存在"
        assert r.code == "NOT_FOUND"
        assert r.data is None

    def test_failure_default_code(self):
        r = Result.failure(error="未知错误")
        assert r.code == "INTERNAL_ERROR"

    def test_success_to_dict(self):
        r = Result.success(data=[1, 2, 3])
        d = r.to_dict()
        assert d == {"ok": True, "data": [1, 2, 3]}

    def test_failure_to_dict(self):
        r = Result.failure(error="失败", code="BAD")
        d = r.to_dict()
        assert d == {"ok": False, "error": "失败", "code": "BAD"}

    def test_failure_to_dict_without_code(self):
        r = Result(ok=False, error="无代码")
        d = r.to_dict()
        assert "code" not in d
        assert d == {"ok": False, "error": "无代码"}

    def test_success_no_data(self):
        r = Result.success()
        assert r.data is None
        d = r.to_dict()
        assert d == {"ok": True, "data": None}


class TestFastAPIExceptionHandler:
    def test_bco_error_returns_400(self):
        from boss_career_ops.web.server import bco_error_handler
        from unittest.mock import MagicMock
        import json
        import asyncio

        exc = BCOError("测试异常", "TEST_CODE")
        response = asyncio.run(bco_error_handler(MagicMock(), exc))
        body = json.loads(response.body.decode())
        assert response.status_code == 400
        assert body["ok"] is False
        assert body["error"] == "测试异常"
        assert body["code"] == "TEST_CODE"

    def test_subclass_error_returns_400(self):
        from boss_career_ops.web.server import bco_error_handler
        from unittest.mock import MagicMock
        import json
        import asyncio

        exc = AuthError("Token 过期", "AUTH_EXPIRED")
        response = asyncio.run(bco_error_handler(MagicMock(), exc))
        body = json.loads(response.body.decode())
        assert response.status_code == 400
        assert body["ok"] is False
        assert body["error"] == "Token 过期"
        assert body["code"] == "AUTH_EXPIRED"
