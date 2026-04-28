import json
from unittest.mock import patch, MagicMock

import pytest

from boss_career_ops.mcp.tools import register_tools
from boss_career_ops.errors import Result
from mcp.types import TextContent


def _make_decorator_mock():
    captured = {}

    def decorator(*args, **kwargs):
        def wrapper(fn):
            captured["handler"] = fn
            return fn
        return wrapper

    decorator.captured = captured
    return decorator


def _setup_app():
    mock_app = MagicMock()
    call_tool_dec = _make_decorator_mock()
    list_tools_dec = _make_decorator_mock()
    mock_app.call_tool = call_tool_dec
    mock_app.list_tools = list_tools_dec
    register_tools(mock_app)
    return call_tool_dec.captured["handler"]


class TestRegisterTools:
    def test_registers_handlers(self):
        mock_app = MagicMock()
        register_tools(mock_app)
        assert mock_app.list_tools.called
        assert mock_app.call_tool.called

    @pytest.mark.asyncio
    @patch("boss_career_ops.agent.tools.search_jobs")
    async def test_call_tool_with_search_jobs(self, mock_search_jobs):
        mock_search_jobs.return_value = [
            {"job_id": "job1", "job_name": "Python开发", "company_name": "公司A"}
        ]
        handler = _setup_app()
        result = await handler("search_jobs", {"keyword": "Python", "city": ""})
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        parsed = json.loads(result[0].text)
        assert parsed[0]["job_id"] == "job1"
        mock_search_jobs.assert_called_once_with("Python", "")

    @pytest.mark.asyncio
    @patch("boss_career_ops.agent.tools.evaluate_job")
    async def test_call_tool_with_evaluate_job(self, mock_evaluate_job):
        mock_evaluate_job.return_value = {
            "total_score": 4.2,
            "grade": "B",
            "grade_label": "推荐",
            "recommendation": "匹配度较高",
            "scores": {"匹配度": 4.0, "薪资": 5.0},
            "job_name": "Python开发",
            "company_name": "公司A",
        }
        handler = _setup_app()
        result = await handler("evaluate_job", {"job_id": "job1"})
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        parsed = json.loads(result[0].text)
        assert parsed["total_score"] == 4.2
        assert parsed["grade"] == "B"
        mock_evaluate_job.assert_called_once_with("job1")

    @pytest.mark.asyncio
    @patch("boss_career_ops.agent.tools.evaluate_job")
    async def test_call_tool_with_evaluate_job_not_found(self, mock_evaluate_job):
        mock_evaluate_job.return_value = None
        handler = _setup_app()
        result = await handler("evaluate_job", {"job_id": "missing"})
        assert len(result) == 1
        parsed = json.loads(result[0].text)
        assert "error" in parsed

    @pytest.mark.asyncio
    @patch("boss_career_ops.agent.tools.generate_resume")
    async def test_call_tool_with_generate_resume(self, mock_generate_resume):
        mock_generate_resume.return_value = "# 简历\n针对职位定制"
        handler = _setup_app()
        result = await handler("generate_resume", {"job_id": "job1"})
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "简历" in result[0].text
        mock_generate_resume.assert_called_once_with("job1")

    @pytest.mark.asyncio
    @patch("boss_career_ops.agent.tools.generate_resume")
    async def test_call_tool_with_generate_resume_not_found(self, mock_generate_resume):
        mock_generate_resume.return_value = None
        handler = _setup_app()
        result = await handler("generate_resume", {"job_id": "missing"})
        assert len(result) == 1
        parsed = json.loads(result[0].text)
        assert "error" in parsed

    @pytest.mark.asyncio
    @patch("boss_career_ops.agent.tools.greet_recruiter")
    async def test_call_tool_with_greet_recruiter(self, mock_greet):
        mock_greet.return_value = Result.success(data={"message": "打招呼成功"})
        handler = _setup_app()
        result = await handler("greet_recruiter", {"security_id": "sec1", "job_id": "job1"})
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        parsed = json.loads(result[0].text)
        assert parsed["ok"] is True
        assert parsed["data"]["message"] == "打招呼成功"
        mock_greet.assert_called_once_with("sec1", "job1")

    @pytest.mark.asyncio
    @patch("boss_career_ops.agent.tools.greet_recruiter")
    async def test_call_tool_with_greet_recruiter_failure(self, mock_greet):
        mock_greet.return_value = Result.failure(error="打招呼失败", code="GREET_FAILED")
        handler = _setup_app()
        result = await handler("greet_recruiter", {"security_id": "sec1", "job_id": "job1"})
        assert len(result) == 1
        parsed = json.loads(result[0].text)
        assert parsed["ok"] is False
        assert "打招呼失败" in parsed["error"]

    @pytest.mark.asyncio
    @patch("boss_career_ops.agent.tools.apply_job")
    async def test_call_tool_with_apply_job(self, mock_apply):
        mock_apply.return_value = Result.success(data={"message": "投递成功"})
        handler = _setup_app()
        result = await handler("apply_job", {"security_id": "sec1", "job_id": "job1"})
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        parsed = json.loads(result[0].text)
        assert parsed["ok"] is True
        assert parsed["data"]["message"] == "投递成功"
        mock_apply.assert_called_once_with("sec1", "job1")

    @pytest.mark.asyncio
    @patch("boss_career_ops.agent.tools.apply_job")
    async def test_call_tool_with_apply_job_failure(self, mock_apply):
        mock_apply.return_value = Result.failure(error="投递失败", code="APPLY_FAILED")
        handler = _setup_app()
        result = await handler("apply_job", {"security_id": "sec1", "job_id": "job1"})
        assert len(result) == 1
        parsed = json.loads(result[0].text)
        assert parsed["ok"] is False

    @pytest.mark.asyncio
    @patch("boss_career_ops.agent.tools.list_pipeline_jobs")
    async def test_call_tool_with_get_pipeline(self, mock_list_jobs):
        mock_list_jobs.return_value = [
            {"job_id": "job1", "job_name": "Python开发", "stage": "evaluated"},
        ]
        handler = _setup_app()
        result = await handler("get_pipeline", {"stage": "evaluated"})
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        parsed = json.loads(result[0].text)
        assert len(parsed) == 1
        assert parsed[0]["job_id"] == "job1"
        mock_list_jobs.assert_called_once_with(stage="evaluated")

    @pytest.mark.asyncio
    @patch("boss_career_ops.agent.tools.list_pipeline_jobs")
    async def test_call_tool_with_get_pipeline_no_stage(self, mock_list_jobs):
        mock_list_jobs.return_value = [
            {"job_id": "job1"}, {"job_id": "job2"},
        ]
        handler = _setup_app()
        result = await handler("get_pipeline", {"stage": ""})
        assert len(result) == 1
        parsed = json.loads(result[0].text)
        assert len(parsed) == 2
        mock_list_jobs.assert_called_once_with(stage=None)

    @pytest.mark.asyncio
    @patch("boss_career_ops.agent.tools.get_job_detail")
    async def test_call_tool_with_get_job_detail(self, mock_get_detail):
        mock_get_detail.return_value = {
            "job_id": "job1",
            "job_name": "Python开发",
            "company_name": "公司A",
            "ai_results": [{"task_type": "evaluate", "result": '{"score":4.2}'}],
        }
        handler = _setup_app()
        result = await handler("get_job_detail", {"job_id": "job1"})
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        parsed = json.loads(result[0].text)
        assert parsed["job_id"] == "job1"
        assert "ai_results" in parsed
        mock_get_detail.assert_called_once_with("job1")

    @pytest.mark.asyncio
    @patch("boss_career_ops.agent.tools.get_job_detail")
    async def test_call_tool_with_get_job_detail_not_found(self, mock_get_detail):
        mock_get_detail.return_value = None
        handler = _setup_app()
        result = await handler("get_job_detail", {"job_id": "missing"})
        assert len(result) == 1
        parsed = json.loads(result[0].text)
        assert "error" in parsed

    @pytest.mark.asyncio
    @patch("boss_career_ops.agent.tools.analyze_skill_gap")
    async def test_call_tool_with_analyze_skill_gap(self, mock_analyze):
        mock_analyze.return_value = {
            "skills": ["Python", "Go"],
            "jd_count": 3,
            "analysis_available": True,
        }
        handler = _setup_app()
        result = await handler("analyze_skill_gap", {})
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        parsed = json.loads(result[0].text)
        assert parsed["skills"] == ["Python", "Go"]
        assert parsed["jd_count"] == 3
        assert parsed["analysis_available"] is True
        mock_analyze.assert_called_once()

    @pytest.mark.asyncio
    @patch("boss_career_ops.agent.tools.prepare_interview")
    async def test_call_tool_with_prepare_interview(self, mock_prepare):
        mock_prepare.return_value = Result.success(data={
            "job_id": "job1",
            "job_name": "Python开发",
            "company_name": "公司A",
            "analysis_available": True,
        })
        handler = _setup_app()
        result = await handler("prepare_interview", {"job_id": "job1"})
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        parsed = json.loads(result[0].text)
        assert parsed["ok"] is True
        assert parsed["data"]["job_id"] == "job1"
        mock_prepare.assert_called_once_with("job1")

    @pytest.mark.asyncio
    @patch("boss_career_ops.agent.tools.prepare_interview")
    async def test_call_tool_with_prepare_interview_not_found(self, mock_prepare):
        mock_prepare.return_value = Result.failure(error="职位不存在", code="NOT_FOUND")
        handler = _setup_app()
        result = await handler("prepare_interview", {"job_id": "missing"})
        assert len(result) == 1
        parsed = json.loads(result[0].text)
        assert parsed["ok"] is False

    @pytest.mark.asyncio
    async def test_call_tool_with_unknown_tool(self):
        handler = _setup_app()
        result = await handler("unknown_tool", {})
        assert len(result) == 1
        parsed = json.loads(result[0].text)
        assert "error" in parsed

    @pytest.mark.asyncio
    @patch("boss_career_ops.agent.tools.search_jobs")
    async def test_call_tool_exception_returns_error(self, mock_search):
        mock_search.side_effect = RuntimeError("意外错误")
        handler = _setup_app()
        result = await handler("search_jobs", {"keyword": "Python", "city": ""})
        assert len(result) == 1
        parsed = json.loads(result[0].text)
        assert "error" in parsed
        assert "意外错误" in parsed["error"]


class TestMcpToolEvaluateJobPersistence:
    @pytest.mark.asyncio
    async def test_evaluate_job_persists_to_ai_results(self, tmp_path):
        from boss_career_ops.config.singleton import SingletonMeta
        from boss_career_ops.pipeline.manager import PipelineManager

        SingletonMeta._instances.clear()
        db_path = tmp_path / "test_pipeline.db"
        pm = PipelineManager(db_path=str(db_path))
        with pm:
            pm.upsert_job(
                "job_persist",
                job_name="Python开发",
                company_name="公司A",
                salary_desc="20K-40K",
                security_id="sec1",
            )

        import boss_career_ops.agent.tools as tools_mod
        tools_mod._pm = pm

        with patch("boss_career_ops.evaluator.engine.EvaluationEngine") as mock_engine_cls:
            mock_engine = MagicMock()
            mock_engine.evaluate.return_value = {
                "total_score": 4.2,
                "grade": "B",
                "recommendation": "匹配度较高",
                "scores": {"匹配度": 4.0, "薪资": 5.0},
                "job_name": "Python开发",
                "company_name": "公司A",
            }
            mock_engine_cls.return_value = mock_engine

            handler = _setup_app()
            result = await handler("evaluate_job", {"job_id": "job_persist"})

        assert len(result) == 1
        parsed = json.loads(result[0].text)
        assert parsed["total_score"] == 4.2

        import sqlite3
        conn = sqlite3.connect(str(db_path))
        row = conn.execute(
            "SELECT job_id, task_type, result FROM ai_results WHERE job_id = ? AND task_type = ?",
            ("job_persist", "evaluate"),
        ).fetchone()
        conn.close()

        assert row is not None
        assert row[0] == "job_persist"
        assert row[1] == "evaluate"
        saved = json.loads(row[2])
        assert saved["score"] == 4.2
        assert saved["grade"] == "B"

        tools_mod._pm = None
        SingletonMeta._instances.clear()
