import json
from unittest.mock import patch, MagicMock

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from boss_career_ops.web.server import app

client = TestClient(app)


def _mock_pm_ctx(mock_pm):
    mock_pm.__enter__ = MagicMock(return_value=mock_pm)
    mock_pm.__exit__ = MagicMock(return_value=False)
    return mock_pm


class TestWebApiAuth:
    def test_write_endpoint_rejects_without_api_key_header(self):
        with patch("boss_career_ops.web.server.API_KEY", "test-secret-key"):
            res = client.post("/api/greet", json={"security_id": "abc", "job_id": "1"})
            assert res.status_code == 401
            assert res.json()["code"] == "UNAUTHORIZED"

    def test_write_endpoint_rejects_wrong_api_key(self):
        with patch("boss_career_ops.web.server.API_KEY", "test-secret-key"):
            res = client.post("/api/greet", json={"security_id": "abc", "job_id": "1"}, headers={"Authorization": "Bearer wrong-key"})
            assert res.status_code == 401

    def test_read_endpoint_works_without_auth(self):
        with patch("boss_career_ops.web.server.API_KEY", "test-secret-key"):
            with patch("boss_career_ops.web.server.PipelineManager") as MockPM:
                _mock_pm_ctx(MockPM.return_value).list_jobs.return_value = []
                res = client.get("/api/pipeline")
                assert res.status_code == 200

    def test_no_api_key_means_no_auth_required(self):
        with patch("boss_career_ops.web.server.API_KEY", ""):
            with patch("boss_career_ops.web.server.get_active_adapter") as mock_adapter_fn:
                mock_adapter = MagicMock()
                mock_result = MagicMock()
                mock_result.ok = True
                mock_result.message = "ok"
                mock_adapter.greet.return_value = mock_result
                mock_adapter_fn.return_value = mock_adapter
                res = client.post("/api/greet", json={"security_id": "abc", "job_id": "1"})
                assert res.status_code == 200

    def test_apply_endpoint_requires_auth(self):
        with patch("boss_career_ops.web.server.API_KEY", "test-secret-key"):
            res = client.post("/api/apply", json={"security_id": "abc", "job_id": "1"})
            assert res.status_code == 401

    def test_profile_update_requires_auth(self):
        with patch("boss_career_ops.web.server.API_KEY", "test-secret-key"):
            res = client.put("/api/profile", json={"name": "test"})
            assert res.status_code == 401

    def test_settings_ai_save_requires_auth(self):
        with patch("boss_career_ops.web.server.API_KEY", "test-secret-key"):
            res = client.post("/api/settings/ai", json={"provider": "deepseek", "api_key": "sk-test"})
            assert res.status_code == 401

    def test_search_requires_auth(self):
        with patch("boss_career_ops.web.server.API_KEY", "test-secret-key"):
            res = client.post("/api/search", json={"keyword": "Go"})
            assert res.status_code == 401


class TestApiResponseFormat:
    def test_success_response_format(self):
        with patch("boss_career_ops.web.server.PipelineManager") as MockPM:
            _mock_pm_ctx(MockPM.return_value).list_jobs.return_value = []
            res = client.get("/api/pipeline")
            data = res.json()
            assert data["ok"] is True
            assert "data" in data

    def test_error_response_format(self):
        with patch("boss_career_ops.web.server.PipelineManager") as MockPM:
            _mock_pm_ctx(MockPM.return_value).list_jobs.side_effect = Exception("test error")
            res = client.get("/api/pipeline")
            data = res.json()
            assert data["ok"] is False
            assert "error" in data


class TestPipelineApi:
    def test_get_pipeline(self):
        with patch("boss_career_ops.web.server.PipelineManager") as MockPM:
            _mock_pm_ctx(MockPM.return_value).list_jobs.return_value = [{"job_id": "1", "job_name": "test"}]
            res = client.get("/api/pipeline")
            assert res.json()["ok"] is True
            assert len(res.json()["data"]) == 1

    def test_get_pipeline_with_stage(self):
        with patch("boss_career_ops.web.server.PipelineManager") as MockPM:
            _mock_pm_ctx(MockPM.return_value).list_jobs.return_value = []
            res = client.get("/api/pipeline?stage=evaluated")
            assert res.status_code == 200


class TestJobDetailApi:
    def test_get_job_detail(self):
        with patch("boss_career_ops.web.server.PipelineManager") as MockPM:
            _mock_pm_ctx(MockPM.return_value).get_job_detail.return_value = {"job_id": "1", "job_name": "Go"}
            res = client.get("/api/jobs/1")
            assert res.json()["ok"] is True
            assert res.json()["data"]["job_id"] == "1"

    def test_get_job_not_found(self):
        with patch("boss_career_ops.web.server.PipelineManager") as MockPM:
            _mock_pm_ctx(MockPM.return_value).get_job_detail.return_value = None
            res = client.get("/api/jobs/999")
            assert res.json()["ok"] is False
            assert res.json()["code"] == "NOT_FOUND"


class TestSearchApi:
    def test_search_no_keyword(self):
        with patch("boss_career_ops.web.server.API_KEY", ""):
            res = client.post("/api/search", json={"keyword": ""})
            assert res.json()["ok"] is False
            assert res.json()["code"] == "VALIDATION_ERROR"


class TestStatsApi:
    def test_get_stats(self):
        with patch("boss_career_ops.web.server.PipelineManager") as MockPM:
            _mock_pm_ctx(MockPM.return_value).list_jobs.return_value = [
                {"stage": "evaluated"}, {"stage": "evaluated"}, {"stage": "applied"},
            ]
            res = client.get("/api/stats")
            assert res.json()["data"]["total"] == 3


class TestSettingsAiApi:
    def test_get_ai_status_removed(self):
        res = client.get("/api/settings/ai")
        assert res.json()["data"]["configured"] is False
        assert res.json()["data"]["source"] == "removed"

    def test_save_ai_config_removed(self):
        with patch("boss_career_ops.web.server.API_KEY", ""):
            res = client.post("/api/settings/ai", json={"provider": "deepseek", "api_key": "sk-test"})
            assert res.json()["ok"] is False
            assert res.json()["code"] == "AGENT_REMOVED"


class TestProvidersApi:
    def test_get_providers_returns_empty(self):
        res = client.get("/api/settings/providers")
        assert res.json()["data"] == []


class TestAuthStatusApi:
    def test_get_auth_status(self):
        with patch("boss_career_ops.boss.auth.token_store.TokenStore") as MockStore:
            MockStore.return_value.check_quality.return_value = {"ok": True, "missing": [], "message": "ok"}
            res = client.get("/api/auth/status")
            assert res.json()["ok"] is True


class TestAiReplySuggestApi:
    def test_reply_suggest_removed(self):
        with patch("boss_career_ops.web.server.API_KEY", ""):
            res = client.post("/api/ai/reply-suggest", json={"security_id": "abc", "job_id": "1"})
            assert res.json()["ok"] is False
            assert res.json()["code"] == "AGENT_REMOVED"


class TestGreetApplyApi:
    def test_greet_missing_fields(self):
        with patch("boss_career_ops.web.server.API_KEY", ""):
            res = client.post("/api/greet", json={"security_id": "", "job_id": ""})
            assert res.json()["ok"] is False
            assert res.json()["code"] == "VALIDATION_ERROR"

    def test_apply_missing_fields(self):
        with patch("boss_career_ops.web.server.API_KEY", ""):
            res = client.post("/api/apply", json={"security_id": "", "job_id": ""})
            assert res.json()["ok"] is False
            assert res.json()["code"] == "VALIDATION_ERROR"


class TestResumeApi:
    def test_resume_generate_returns_use_cli(self):
        with patch("boss_career_ops.web.server.API_KEY", ""):
            res = client.post("/api/resume/generate", json={"job_id": "1"})
            assert res.json()["ok"] is False
            assert res.json()["code"] == "USE_CLI"

    def test_resume_upload_returns_use_cli(self):
        with patch("boss_career_ops.web.server.API_KEY", ""):
            res = client.post("/api/resume/upload", json={"job_id": "1"})
            assert res.json()["ok"] is False
            assert res.json()["code"] == "USE_CLI"

    def test_resume_pdf_returns_use_cli(self):
        res = client.get("/api/resume/1/pdf")
        assert res.json()["ok"] is False
        assert res.json()["code"] == "USE_CLI"

    def test_resume_get(self):
        with patch("boss_career_ops.web.server.PipelineManager") as MockPM:
            mock_pm = _mock_pm_ctx(MockPM.return_value)
            mock_pm.get_ai_result.return_value = {"result": json.dumps({"content": "# 简历"})}
            res = client.get("/api/resume/1")
            assert res.json()["ok"] is True
            assert res.json()["data"]["content"] == "# 简历"

    def test_resume_get_not_found(self):
        with patch("boss_career_ops.web.server.PipelineManager") as MockPM:
            _mock_pm_ctx(MockPM.return_value).get_ai_result.return_value = None
            res = client.get("/api/resume/999")
            assert res.json()["ok"] is False
            assert res.json()["code"] == "NOT_FOUND"


class TestInterviewApi:
    def test_interview_prepare_missing_job_id(self):
        with patch("boss_career_ops.web.server.API_KEY", ""):
            res = client.post("/api/interview/prepare", json={"job_id": ""})
            assert res.json()["ok"] is False
            assert res.json()["code"] == "VALIDATION_ERROR"

    def test_interview_prepare_not_found(self):
        with patch("boss_career_ops.web.server.API_KEY", ""):
            with patch("boss_career_ops.web.server.PipelineManager") as MockPM:
                _mock_pm_ctx(MockPM.return_value).get_ai_result.return_value = None
                res = client.post("/api/interview/prepare", json={"job_id": "999"})
                assert res.json()["ok"] is False
                assert res.json()["code"] == "NOT_FOUND"

    def test_interview_get(self):
        with patch("boss_career_ops.web.server.PipelineManager") as MockPM:
            _mock_pm_ctx(MockPM.return_value).get_ai_result.return_value = {"result": json.dumps({"topics": ["Go 并发"]})}
            res = client.get("/api/interview/1")
            assert res.json()["ok"] is True

    def test_interview_get_not_found(self):
        with patch("boss_career_ops.web.server.PipelineManager") as MockPM:
            _mock_pm_ctx(MockPM.return_value).get_ai_result.return_value = None
            res = client.get("/api/interview/999")
            assert res.json()["ok"] is False
            assert res.json()["code"] == "NOT_FOUND"


class TestAnalyticsApi:
    def test_analytics_overview(self):
        with patch("boss_career_ops.web.server.PipelineManager") as MockPM:
            _mock_pm_ctx(MockPM.return_value).list_jobs.return_value = [
                {"score": 4.0, "grade": "A", "stage": "evaluated"},
                {"score": 3.0, "grade": "B", "stage": "applied"},
            ]
            res = client.get("/api/analytics/overview")
            assert res.json()["ok"] is True
            assert res.json()["data"]["total"] == 2

    def test_analytics_salary_distribution(self):
        with patch("boss_career_ops.web.server.PipelineManager") as MockPM:
            _mock_pm_ctx(MockPM.return_value).list_jobs.return_value = [
                {"data": json.dumps({"salary_min": 15000, "salary_max": 25000})},
            ]
            res = client.get("/api/analytics/salary-distribution")
            assert res.json()["ok"] is True

    def test_analytics_grade_distribution(self):
        with patch("boss_career_ops.web.server.PipelineManager") as MockPM:
            _mock_pm_ctx(MockPM.return_value).list_jobs.return_value = [
                {"grade": "A"}, {"grade": "B"}, {"grade": "A"},
            ]
            res = client.get("/api/analytics/grade-distribution")
            assert res.json()["ok"] is True
            assert res.json()["data"]["A"] == 2

    def test_analytics_stage_funnel(self):
        with patch("boss_career_ops.web.server.PipelineManager") as MockPM:
            _mock_pm_ctx(MockPM.return_value).list_jobs.return_value = [
                {"stage": "evaluated"}, {"stage": "applied"},
            ]
            res = client.get("/api/analytics/stage-funnel")
            assert res.json()["ok"] is True

    def test_analytics_no_auth_required(self):
        with patch("boss_career_ops.web.server.API_KEY", "test-secret-key"):
            with patch("boss_career_ops.web.server.PipelineManager") as MockPM:
                _mock_pm_ctx(MockPM.return_value).list_jobs.return_value = []
                res = client.get("/api/analytics/overview")
                assert res.status_code == 200


class TestSkillGapApi:
    def test_skill_gap_analyze(self):
        with patch("boss_career_ops.web.server.API_KEY", ""):
            with patch("boss_career_ops.web.server.PipelineManager") as MockPM:
                with patch("boss_career_ops.web.server.Settings") as MockSettings:
                    _mock_pm_ctx(MockPM.return_value).list_jobs.return_value = [
                        {"skills": ["Go", "Kubernetes"]},
                    ]
                    MockSettings.return_value.profile.skills = ["Go", "Docker"]
                    res = client.post("/api/skill-gap/analyze", json={})
                    assert res.json()["ok"] is True
                    assert res.json()["data"]["jd_count"] == 1

    def test_skill_gap_requires_auth(self):
        with patch("boss_career_ops.web.server.API_KEY", "test-secret-key"):
            res = client.post("/api/skill-gap/analyze", json={})
            assert res.status_code == 401
