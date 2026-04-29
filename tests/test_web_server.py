import asyncio
import importlib
import sys
import time
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from boss_career_ops.web.server import app

client = TestClient(app)


class TestWebApiAuth:
    def test_write_endpoint_rejects_without_api_key_header(self):
        with patch("boss_career_ops.web.server.API_KEY", "test-secret-key"):
            with patch("boss_career_ops.web.server.agent_tools"):
                res = client.post("/api/greet", json={"security_id": "abc", "job_id": "1"})
                assert res.status_code == 401
                data = res.json()
                assert data["ok"] is False
                assert data["code"] == "UNAUTHORIZED"

    def test_write_endpoint_rejects_wrong_api_key(self):
        with patch("boss_career_ops.web.server.API_KEY", "test-secret-key"):
            with patch("boss_career_ops.web.server.agent_tools"):
                res = client.post(
                    "/api/greet",
                    json={"security_id": "abc", "job_id": "1"},
                    headers={"Authorization": "Bearer wrong-key"},
                )
                assert res.status_code == 401
                data = res.json()
                assert data["code"] == "UNAUTHORIZED"

    def test_write_endpoint_succeeds_with_valid_api_key(self):
        with patch("boss_career_ops.web.server.API_KEY", "test-secret-key"):
            with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
                mock_tools.greet_recruiter.return_value = MagicMock(ok=True, data={"status": "sent"})
                res = client.post(
                    "/api/greet",
                    json={"security_id": "abc", "job_id": "1"},
                    headers={"Authorization": "Bearer test-secret-key"},
                )
                assert res.status_code == 200
                data = res.json()
                assert data["ok"] is True

    def test_read_endpoint_works_without_auth(self):
        with patch("boss_career_ops.web.server.API_KEY", "test-secret-key"):
            with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
                mock_tools.list_pipeline_jobs.return_value = []
                res = client.get("/api/pipeline")
                assert res.status_code == 200
                data = res.json()
                assert data["ok"] is True

    def test_no_api_key_means_no_auth_required(self):
        with patch("boss_career_ops.web.server.API_KEY", ""):
            with patch("boss_career_ops.web.server.agent_tools"):
                res = client.post("/api/greet", json={"security_id": "abc", "job_id": "1"})
                assert res.status_code == 200

    def test_apply_endpoint_requires_auth(self):
        with patch("boss_career_ops.web.server.API_KEY", "test-secret-key"):
            with patch("boss_career_ops.web.server.agent_tools"):
                res = client.post("/api/apply", json={"security_id": "abc", "job_id": "1"})
                assert res.status_code == 401

    def test_profile_update_requires_auth(self):
        with patch("boss_career_ops.web.server.API_KEY", "test-secret-key"):
            with patch("boss_career_ops.web.server.agent_tools"):
                res = client.put("/api/profile", json={"name": "test"})
                assert res.status_code == 401

    def test_settings_ai_save_requires_auth(self):
        with patch("boss_career_ops.web.server.API_KEY", "test-secret-key"):
            res = client.post("/api/settings/ai", json={"provider": "deepseek", "api_key": "sk-test"})
            assert res.status_code == 401

    def test_search_requires_auth(self):
        with patch("boss_career_ops.web.server.API_KEY", "test-secret-key"):
            with patch("boss_career_ops.web.server.agent_tools"):
                res = client.post("/api/search", json={"keyword": "Go"})
                assert res.status_code == 401


class TestNoAiConfigImport:
    def test_server_does_not_import_ai_config(self):
        import ast
        source = open(sys.modules["boss_career_ops.web.server"].__file__, encoding="utf-8").read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    assert alias.name != "ai_config", f"发现禁止的 ai_config 导入: from {node.module} import {alias.name}"


class TestApiResponseFormat:
    def test_success_response_format(self):
        with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
            mock_tools.list_pipeline_jobs.return_value = []
            res = client.get("/api/pipeline")
            data = res.json()
            assert "ok" in data
            assert data["ok"] is True
            assert "data" in data

    def test_error_response_format(self):
        with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
            mock_tools.list_pipeline_jobs.side_effect = Exception("test error")
            res = client.get("/api/pipeline")
            data = res.json()
            assert data["ok"] is False
            assert "error" in data
            assert "code" in data


class TestPipelineApi:
    def test_get_pipeline(self):
        with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
            mock_tools.list_pipeline_jobs.return_value = [{"job_id": "1", "job_name": "test"}]
            res = client.get("/api/pipeline")
            assert res.status_code == 200
            data = res.json()
            assert data["ok"] is True
            assert len(data["data"]) == 1

    def test_get_pipeline_with_stage(self):
        with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
            mock_tools.list_pipeline_jobs.return_value = []
            res = client.get("/api/pipeline?stage=evaluated")
            assert res.status_code == 200
            mock_tools.list_pipeline_jobs.assert_called_with(stage="evaluated", status=None)


class TestJobDetailApi:
    def test_get_job_detail(self):
        with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
            mock_tools.get_job_with_ai_result.return_value = {"job_id": "1", "job_name": "Go"}
            res = client.get("/api/jobs/1")
            assert res.status_code == 200
            data = res.json()
            assert data["ok"] is True
            assert data["data"]["job_id"] == "1"

    def test_get_job_not_found(self):
        with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
            mock_tools.get_job_with_ai_result.return_value = None
            res = client.get("/api/jobs/999")
            assert res.status_code == 200
            data = res.json()
            assert data["ok"] is False
            assert data["code"] == "NOT_FOUND"


class TestSearchApi:
    def test_search_jobs(self):
        with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
            mock_tools.search_jobs.return_value = [{"job_id": "1"}]
            res = client.post("/api/search", json={"keyword": "Go", "city": "gz"})
            assert res.status_code == 200
            data = res.json()
            assert data["ok"] is True

    def test_search_no_keyword(self):
        with patch("boss_career_ops.web.server.agent_tools"):
            res = client.post("/api/search", json={"keyword": ""})
            data = res.json()
            assert data["ok"] is False
            assert data["code"] == "VALIDATION_ERROR"


class TestStatsApi:
    def test_get_stats(self):
        with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
            mock_tools.list_pipeline_jobs.return_value = [
                {"stage": "evaluated"}, {"stage": "evaluated"}, {"stage": "applied"},
            ]
            res = client.get("/api/stats")
            data = res.json()
            assert data["ok"] is True
            assert data["data"]["total"] == 3
            assert data["data"]["by_stage"]["evaluated"] == 2


class TestSettingsAiApi:
    def test_get_ai_status_not_configured(self):
        with patch("boss_career_ops.web.server.is_llm_available", return_value=False):
            with patch.dict("os.environ", {"BCO_LLM_API_KEY": "", "BCO_LLM_PROVIDER": ""}, clear=False):
                res = client.get("/api/settings/ai")
                data = res.json()
                assert data["ok"] is True
                assert data["data"]["configured"] is False
                assert data["data"]["source"] == "none"

    def test_get_ai_status_configured_via_env(self):
        with patch("boss_career_ops.web.server.is_llm_available", return_value=True):
            with patch.dict("os.environ", {"BCO_LLM_API_KEY": "sk-test", "BCO_LLM_PROVIDER": "deepseek"}, clear=False):
                res = client.get("/api/settings/ai")
                data = res.json()
                assert data["ok"] is True
                assert data["data"]["configured"] is True
                assert data["data"]["source"] == "env"
                assert data["data"]["provider"] == "deepseek"

    def test_get_ai_status_configured_via_file(self):
        with patch("boss_career_ops.web.server.is_llm_available", return_value=True):
            with patch.dict("os.environ", {"BCO_LLM_API_KEY": "", "BCO_LLM_PROVIDER": ""}, clear=False):
                res = client.get("/api/settings/ai")
                data = res.json()
                assert data["ok"] is True
                assert data["data"]["configured"] is True
                assert data["data"]["source"] == "file"

    def test_save_ai_config(self):
        with patch("boss_career_ops.boss.auth.token_store.TokenStore") as mock_store_cls:
            mock_store = MagicMock()
            mock_store.fernet.encrypt.return_value = b"enc_key"
            mock_store_cls.return_value = mock_store
            with patch("boss_career_ops.web.server.reset_llm"):
                with patch("boss_career_ops.web.server.is_llm_available", return_value=True):
                    with patch.dict("os.environ", {"BCO_LLM_API_KEY": "sk-test"}, clear=False):
                        res = client.post("/api/settings/ai", json={"provider": "deepseek", "api_key": "sk-test"})
                        data = res.json()
                        assert data["ok"] is True
                        mock_store.fernet.encrypt.assert_called_once()
                        assert data["data"]["configured"] is True

    def test_save_ai_config_missing_fields(self):
        res = client.post("/api/settings/ai", json={"provider": "", "api_key": ""})
        data = res.json()
        assert data["ok"] is False
        assert data["code"] == "VALIDATION_ERROR"


class TestProvidersApi:
    def test_get_providers(self):
        res = client.get("/api/settings/providers")
        data = res.json()
        assert data["ok"] is True
        assert len(data["data"]) > 0
        provider_ids = [p["id"] for p in data["data"]]
        assert "deepseek" in provider_ids

    def test_providers_have_required_fields(self):
        res = client.get("/api/settings/providers")
        data = res.json()
        for provider in data["data"]:
            assert "id" in provider
            assert "name" in provider
            assert "base_url" in provider
            assert "default_model" in provider


class TestAuthStatusApi:
    def test_get_auth_status(self):
        with patch("boss_career_ops.boss.auth.token_store.TokenStore") as mock_store_cls:
            mock_store = MagicMock()
            mock_store.check_quality.return_value = {"ok": True, "missing": [], "message": "ok"}
            mock_store_cls.return_value = mock_store
            res = client.get("/api/auth/status")
            data = res.json()
            assert data["ok"] is True


class TestAiReplySuggestApi:
    def test_ai_not_configured(self):
        with patch("boss_career_ops.agent.llm.is_llm_available", return_value=False):
            res = client.post("/api/ai/reply-suggest", json={"security_id": "abc", "job_id": "1"})
            data = res.json()
            assert data["ok"] is False
            assert data["code"] == "AI_NOT_CONFIGURED"
            assert data["setup_url"] == "#/settings"

    def test_ai_configured(self):
        with patch("boss_career_ops.web.server.is_llm_available", return_value=True):
            with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
                mock_tools.get_chat_messages.return_value = []
                mock_tools.get_job_with_ai_result.return_value = {"job_id": "1"}
                res = client.post("/api/ai/reply-suggest", json={"security_id": "abc", "job_id": "1"})
                data = res.json()
                assert data["ok"] is True


class TestGreetApplyApi:
    def test_greet_missing_fields(self):
        with patch("boss_career_ops.web.server.agent_tools"):
            res = client.post("/api/greet", json={"security_id": "", "job_id": ""})
            data = res.json()
            assert data["ok"] is False
            assert data["code"] == "VALIDATION_ERROR"

    def test_apply_missing_fields(self):
        with patch("boss_career_ops.web.server.agent_tools"):
            res = client.post("/api/apply", json={"security_id": "", "job_id": ""})
            data = res.json()
            assert data["ok"] is False
            assert data["code"] == "VALIDATION_ERROR"


class TestProfileReloadUsesSingletonApi:
    def test_update_profile_calls_reload_instance(self):
        with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
            mock_tools.get_profile.return_value = {"name": "test"}
            with patch("boss_career_ops.config.singleton.SingletonMeta.reload_instance") as mock_reload:
                res = client.put("/api/profile", json={"name": "new_name"})
                assert res.status_code == 200
                mock_reload.assert_called_once()

    def test_reload_instance_updates_settings(self, tmp_path):
        from boss_career_ops.config.singleton import SingletonMeta
        from boss_career_ops.config.settings import Settings

        profile_path = tmp_path / "profile.yml"
        profile_path.write_text("name: old_name\n", encoding="utf-8")
        thresholds_path = tmp_path / "thresholds.yml"
        cv_path = tmp_path / "cv.md"

        SingletonMeta.reset(Settings)
        s1 = Settings(
            profile_path=str(profile_path),
            thresholds_path=str(thresholds_path),
            cv_path=str(cv_path),
        )
        assert s1.profile.name == "old_name"

        profile_path.write_text("name: new_name\n", encoding="utf-8")
        s2 = SingletonMeta.reload_instance(Settings)
        assert s2.profile.name == "new_name"
        assert s2 is not s1

        SingletonMeta.reset(Settings)


class TestAsyncEndpointsNonBlocking:
    def test_pipeline_endpoint_uses_to_thread(self):
        with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
            mock_tools.list_pipeline_jobs.return_value = [{"job_id": "1"}]
            res = client.get("/api/pipeline")
            assert res.status_code == 200
            mock_tools.list_pipeline_jobs.assert_called_once()

    def test_job_detail_endpoint_uses_to_thread(self):
        with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
            mock_tools.get_job_with_ai_result.return_value = {"job_id": "1"}
            res = client.get("/api/jobs/1")
            assert res.status_code == 200
            mock_tools.get_job_with_ai_result.assert_called_once_with("1")

    def test_chat_endpoint_uses_to_thread(self):
        with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
            mock_tools.get_chat_messages.return_value = [{"content": "hi"}]
            res = client.get("/api/chat/abc123")
            assert res.status_code == 200
            mock_tools.get_chat_messages.assert_called_once_with("abc123")

    def test_profile_get_endpoint_uses_to_thread(self):
        with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
            mock_tools.get_profile.return_value = {"name": "test"}
            res = client.get("/api/profile")
            assert res.status_code == 200
            mock_tools.get_profile.assert_called_once()

    def test_greet_endpoint_uses_to_thread(self):
        with patch("boss_career_ops.web.server.API_KEY", ""):
            with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
                mock_tools.greet_recruiter.return_value = MagicMock(ok=True, data={"status": "sent"})
                res = client.post("/api/greet", json={"security_id": "abc", "job_id": "1"})
                assert res.status_code == 200
                mock_tools.greet_recruiter.assert_called_once_with("abc", "1")

    def test_apply_endpoint_uses_to_thread(self):
        with patch("boss_career_ops.web.server.API_KEY", ""):
            with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
                mock_tools.apply_job.return_value = MagicMock(ok=True, data={"status": "applied"})
                res = client.post("/api/apply", json={"security_id": "abc", "job_id": "1"})
                assert res.status_code == 200
                mock_tools.apply_job.assert_called_once_with("abc", "1", "")

    def test_search_endpoint_uses_to_thread(self):
        with patch("boss_career_ops.web.server.API_KEY", ""):
            with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
                mock_tools.search_jobs.return_value = [{"job_id": "1"}]
                res = client.post("/api/search", json={"keyword": "Go", "city": "gz"})
                assert res.status_code == 200
                mock_tools.search_jobs.assert_called_once_with("Go", "gz", 1, "", True)


class TestEvaluateApi:
    def test_evaluate_success(self):
        with patch("boss_career_ops.web.server.API_KEY", ""):
            with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
                mock_tools.evaluate_job.return_value = {
                    "job_id": "1", "total_score": 3.8, "grade": "B",
                    "scores": {"匹配度": 4.0}, "match_reasons": ["技能匹配"],
                    "mismatch_reasons": [], "recommendation": "推荐投递", "source": "rule",
                }
                res = client.post("/api/evaluate", json={"job_id": "1"})
                data = res.json()
                assert data["ok"] is True
                assert data["data"]["grade"] == "B"
                mock_tools.evaluate_job.assert_called_once_with("1")

    def test_evaluate_missing_job_id(self):
        with patch("boss_career_ops.web.server.API_KEY", ""):
            res = client.post("/api/evaluate", json={"job_id": ""})
            data = res.json()
            assert data["ok"] is False
            assert data["code"] == "VALIDATION_ERROR"

    def test_evaluate_not_found(self):
        with patch("boss_career_ops.web.server.API_KEY", ""):
            with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
                mock_tools.evaluate_job.return_value = None
                res = client.post("/api/evaluate", json={"job_id": "999"})
                data = res.json()
                assert data["ok"] is False
                assert data["code"] == "NOT_FOUND"

    def test_evaluate_requires_auth(self):
        with patch("boss_career_ops.web.server.API_KEY", "test-secret-key"):
            res = client.post("/api/evaluate", json={"job_id": "1"})
            assert res.status_code == 401


class TestEvaluatePendingApi:
    def test_evaluate_pending_success(self):
        with patch("boss_career_ops.web.server.API_KEY", ""):
            with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
                mock_tools.evaluate_pending_jobs.return_value = {
                    "total": 5, "evaluated": 5,
                    "results": [{"job_id": "1", "grade": "A", "score": 4.2}],
                }
                res = client.post("/api/evaluate/pending", json={"limit": 50})
                data = res.json()
                assert data["ok"] is True
                assert data["data"]["evaluated"] == 5
                mock_tools.evaluate_pending_jobs.assert_called_once_with(50)

    def test_evaluate_pending_requires_auth(self):
        with patch("boss_career_ops.web.server.API_KEY", "test-secret-key"):
            res = client.post("/api/evaluate/pending", json={"limit": 50})
            assert res.status_code == 401


class TestChatListApi:
    def test_get_chat_list(self):
        with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
            mock_tools.get_chat_list.return_value = [
                {"security_id": "abc", "name": "张三", "last_message": "你好", "time": "10:30"},
            ]
            res = client.get("/api/chat-list")
            data = res.json()
            assert data["ok"] is True
            assert len(data["data"]) == 1
            assert data["data"][0]["name"] == "张三"

    def test_chat_list_no_auth_required(self):
        with patch("boss_career_ops.web.server.API_KEY", "test-secret-key"):
            with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
                mock_tools.get_chat_list.return_value = []
                res = client.get("/api/chat-list")
                assert res.status_code == 200


class TestChatSummaryApi:
    def test_get_chat_summary(self):
        with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
            mock_tools.generate_chat_summary.return_value = {
                "security_id": "abc", "summary": "讨论了薪资", "message_count": 5,
            }
            res = client.get("/api/chat/abc/summary")
            data = res.json()
            assert data["ok"] is True
            assert data["data"]["summary"] == "讨论了薪资"


class TestReplySuggestRealLlm:
    def test_reply_suggest_with_message(self):
        with patch("boss_career_ops.web.server.is_llm_available", return_value=True):
            with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
                mock_tools.get_chat_messages.return_value = [
                    {"sender_name": "HR", "content": "你好", "time": "10:00"},
                ]
                mock_tools.get_job_with_ai_result.return_value = {"job_id": "1", "company_name": "测试公司"}
                with patch("boss_career_ops.agent.llm.get_llm") as mock_get_llm:
                    mock_llm = MagicMock()
                    mock_llm.invoke.return_value = MagicMock(content="1. 感谢您的关注\n2. 期待进一步沟通")
                    mock_get_llm.return_value = mock_llm
                    res = client.post("/api/ai/reply-suggest", json={"security_id": "abc", "job_id": "1"})
                    data = res.json()
                    assert data["ok"] is True
                    assert len(data["data"]["suggestions"]) > 0

    def test_reply_suggest_no_security_id_no_message(self):
        with patch("boss_career_ops.web.server.is_llm_available", return_value=True):
            res = client.post("/api/ai/reply-suggest", json={"security_id": "", "message": ""})
            data = res.json()
            assert data["ok"] is False
            assert data["code"] == "VALIDATION_ERROR"

    def test_reply_suggest_llm_none(self):
        with patch("boss_career_ops.web.server.is_llm_available", return_value=True):
            with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
                mock_tools.get_chat_messages.return_value = []
                with patch("boss_career_ops.agent.llm.get_llm", return_value=None):
                    res = client.post("/api/ai/reply-suggest", json={"security_id": "abc"})
                    data = res.json()
                    assert data["ok"] is True
                    assert data["data"]["suggestions"] == []


class TestResumeApi:
    def test_resume_generate_success(self):
        with patch("boss_career_ops.web.server.API_KEY", ""):
            with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
                mock_tools.generate_resume.return_value = "# 张三 - 简历"
                res = client.post("/api/resume/generate", json={"job_id": "1"})
                data = res.json()
                assert data["ok"] is True
                assert data["data"]["content"] == "# 张三 - 简历"
                assert data["data"]["format"] == "markdown"
                mock_tools.generate_resume.assert_called_once_with("1", True)

    def test_resume_generate_missing_job_id(self):
        with patch("boss_career_ops.web.server.API_KEY", ""):
            res = client.post("/api/resume/generate", json={"job_id": ""})
            data = res.json()
            assert data["ok"] is False
            assert data["code"] == "VALIDATION_ERROR"

    def test_resume_generate_failure(self):
        with patch("boss_career_ops.web.server.API_KEY", ""):
            with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
                mock_tools.generate_resume.return_value = None
                res = client.post("/api/resume/generate", json={"job_id": "1"})
                data = res.json()
                assert data["ok"] is False
                assert data["code"] == "RESUME_ERROR"

    def test_resume_get(self):
        with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
            mock_tools.get_resume.return_value = "# 简历内容"
            res = client.get("/api/resume/1")
            data = res.json()
            assert data["ok"] is True
            assert data["data"]["content"] == "# 简历内容"

    def test_resume_get_not_found(self):
        with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
            mock_tools.get_resume.return_value = None
            res = client.get("/api/resume/999")
            data = res.json()
            assert data["ok"] is False
            assert data["code"] == "NOT_FOUND"

    def test_resume_generate_requires_auth(self):
        with patch("boss_career_ops.web.server.API_KEY", "test-secret-key"):
            res = client.post("/api/resume/generate", json={"job_id": "1"})
            assert res.status_code == 401


class TestInterviewApi:
    def test_interview_prepare_success(self):
        with patch("boss_career_ops.web.server.API_KEY", ""):
            with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
                mock_tools.prepare_interview.return_value = MagicMock(
                    ok=True,
                    data={"job_id": "1", "job_name": "Go", "company_name": "测试", "analysis_available": True},
                )
                res = client.post("/api/interview/prepare", json={"job_id": "1"})
                data = res.json()
                assert data["ok"] is True
                assert data["data"]["job_name"] == "Go"

    def test_interview_prepare_missing_job_id(self):
        with patch("boss_career_ops.web.server.API_KEY", ""):
            res = client.post("/api/interview/prepare", json={"job_id": ""})
            data = res.json()
            assert data["ok"] is False
            assert data["code"] == "VALIDATION_ERROR"

    def test_interview_prepare_not_found(self):
        with patch("boss_career_ops.web.server.API_KEY", ""):
            with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
                mock_tools.prepare_interview.return_value = MagicMock(
                    ok=False, error="职位不存在", code="NOT_FOUND",
                )
                res = client.post("/api/interview/prepare", json={"job_id": "999"})
                data = res.json()
                assert data["ok"] is False

    def test_interview_get(self):
        with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
            mock_tools.get_interview_prep.return_value = {"job_id": "1", "topics": ["Go 并发"]}
            res = client.get("/api/interview/1")
            data = res.json()
            assert data["ok"] is True
            assert data["data"]["job_id"] == "1"

    def test_interview_get_not_found(self):
        with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
            mock_tools.get_interview_prep.return_value = None
            res = client.get("/api/interview/999")
            data = res.json()
            assert data["ok"] is False
            assert data["code"] == "NOT_FOUND"

    def test_interview_prepare_requires_auth(self):
        with patch("boss_career_ops.web.server.API_KEY", "test-secret-key"):
            res = client.post("/api/interview/prepare", json={"job_id": "1"})
            assert res.status_code == 401


class TestAnalyticsApi:
    def test_analytics_overview(self):
        with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
            mock_tools.get_analytics_overview.return_value = {
                "total": 10, "avg_score": 3.5, "grade_counts": {"A": 2, "B": 3},
                "stage_counts": {"evaluated": 5}, "ab_ratio": 50.0, "apply_ratio": 20.0,
            }
            res = client.get("/api/analytics/overview")
            data = res.json()
            assert data["ok"] is True
            assert data["data"]["total"] == 10
            assert data["data"]["avg_score"] == 3.5

    def test_analytics_salary_distribution(self):
        with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
            mock_tools.get_salary_distribution.return_value = {
                "0-10k": 2, "10-20k": 5, "20-30k": 3, "30-50k": 1, "50k+": 0,
            }
            res = client.get("/api/analytics/salary-distribution")
            data = res.json()
            assert data["ok"] is True
            assert data["data"]["10-20k"] == 5

    def test_analytics_grade_distribution(self):
        with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
            mock_tools.get_analytics_overview.return_value = {
                "total": 10, "grade_counts": {"A": 2, "B": 3, "C": 5},
            }
            res = client.get("/api/analytics/grade-distribution")
            data = res.json()
            assert data["ok"] is True
            assert data["data"]["A"] == 2

    def test_analytics_stage_funnel(self):
        with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
            mock_tools.get_analytics_overview.return_value = {
                "total": 10, "stage_counts": {"discovered": 5, "evaluated": 3, "applied": 2},
            }
            res = client.get("/api/analytics/stage-funnel")
            data = res.json()
            assert data["ok"] is True
            assert data["data"]["discovered"] == 5

    def test_analytics_no_auth_required(self):
        with patch("boss_career_ops.web.server.API_KEY", "test-secret-key"):
            with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
                mock_tools.get_analytics_overview.return_value = {"total": 0}
                res = client.get("/api/analytics/overview")
                assert res.status_code == 200


class TestSkillGapApi:
    def test_skill_gap_analyze(self):
        with patch("boss_career_ops.web.server.API_KEY", ""):
            with patch("boss_career_ops.web.server.agent_tools") as mock_tools:
                mock_tools.analyze_skill_gap_detail.return_value = {
                    "user_skills": ["go", "k8s"],
                    "matched_skills": ["go"],
                    "missing_skills": [{"skill": "java", "count": 3}],
                    "jd_count": 10,
                }
                res = client.post("/api/skill-gap/analyze", json={})
                data = res.json()
                assert data["ok"] is True
                assert data["data"]["jd_count"] == 10
                assert len(data["data"]["missing_skills"]) == 1

    def test_skill_gap_requires_auth(self):
        with patch("boss_career_ops.web.server.API_KEY", "test-secret-key"):
            res = client.post("/api/skill-gap/analyze", json={})
            assert res.status_code == 401
