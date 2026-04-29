import json
from unittest.mock import patch, MagicMock

import pytest

from boss_career_ops.agent.tools import (
    get_job_detail,
    get_chat_messages,
    get_profile,
    get_cv,
    list_pipeline_jobs,
    get_job_with_ai_result,
    write_evaluation,
    write_resume,
    write_chat_summary,
    write_interview_prep,
    search_jobs,
    greet_recruiter,
    apply_job,
    analyze_skill_gap,
    prepare_interview,
    evaluate_job,
    generate_resume,
)
from boss_career_ops.config.singleton import SingletonMeta
from boss_career_ops.pipeline.manager import PipelineManager
import boss_career_ops.agent.tools as _tools_mod


@pytest.fixture(autouse=True)
def _reset_pm_cache():
    _tools_mod._pm = None
    yield
    _tools_mod._pm = None


class TestGetJobDetail:
    @patch("boss_career_ops.agent.tools.PipelineManager")
    def test_existing_job(self, mock_pm_cls):
        mock_pm = MagicMock()
        mock_pm.__enter__ = MagicMock(return_value=mock_pm)
        mock_pm.__exit__ = MagicMock(return_value=False)
        mock_pm.get_job.return_value = {"job_id": "job1", "job_name": "Golang工程师"}
        mock_pm.get_ai_results.return_value = []
        mock_pm_cls.return_value = mock_pm
        result = get_job_detail("job1")
        assert result is not None
        assert result["job_id"] == "job1"

    @patch("boss_career_ops.agent.tools.PipelineManager")
    def test_nonexistent_job(self, mock_pm_cls):
        mock_pm = MagicMock()
        mock_pm.__enter__ = MagicMock(return_value=mock_pm)
        mock_pm.__exit__ = MagicMock(return_value=False)
        mock_pm.get_job.return_value = None
        mock_pm_cls.return_value = mock_pm
        result = get_job_detail("missing")
        assert result is None

    @patch("boss_career_ops.agent.tools.PipelineManager")
    def test_job_with_ai_results(self, mock_pm_cls):
        mock_pm = MagicMock()
        mock_pm.__enter__ = MagicMock(return_value=mock_pm)
        mock_pm.__exit__ = MagicMock(return_value=False)
        mock_pm.get_job.return_value = {"job_id": "job1"}
        mock_pm.get_ai_results.return_value = [{"task_type": "evaluate", "result": '{"score":4.2}'}]
        mock_pm_cls.return_value = mock_pm
        result = get_job_detail("job1")
        assert "ai_results" in result


class TestGetChatMessages:
    @patch("boss_career_ops.agent.tools.get_active_adapter")
    def test_with_messages(self, mock_adapter_fn):
        mock_adapter = MagicMock()
        mock_msg = MagicMock()
        mock_msg.sender_name = "HR"
        mock_msg.content = "你好"
        mock_msg.time = "10:00"
        mock_adapter.get_chat_messages.return_value = [mock_msg]
        mock_adapter_fn.return_value = mock_adapter
        result = get_chat_messages("sec1")
        assert len(result) == 1
        assert result[0]["sender_name"] == "HR"

    @patch("boss_career_ops.agent.tools.get_active_adapter")
    def test_adapter_error(self, mock_adapter_fn):
        mock_adapter_fn.side_effect = Exception("连接失败")
        result = get_chat_messages("sec1")
        assert result == []


class TestGetProfile:
    @patch("boss_career_ops.agent.tools.Settings")
    def test_returns_profile_dict(self, mock_settings_cls):
        mock_settings = MagicMock()
        mock_profile = MagicMock()
        mock_profile.name = "测试用户"
        mock_profile.title = "工程师"
        mock_profile.experience_years = 5
        mock_profile.skills = ["Python", "Go"]
        mock_profile.expected_salary.min = 20000
        mock_profile.expected_salary.max = 35000
        mock_profile.preferred_cities = ["深圳"]
        mock_profile.education = "本科"
        mock_profile.career_goals = "技术专家"
        mock_settings.profile = mock_profile
        mock_settings_cls.return_value = mock_settings
        result = get_profile()
        assert result["name"] == "测试用户"
        assert result["skills"] == ["Python", "Go"]


class TestGetCv:
    @patch("boss_career_ops.agent.tools.Settings")
    def test_with_content(self, mock_settings_cls):
        mock_settings = MagicMock()
        mock_settings.cv_content = "# 简历\n这是我的简历"
        mock_settings_cls.return_value = mock_settings
        result = get_cv()
        assert "简历" in result

    @patch("boss_career_ops.agent.tools.Settings")
    def test_empty_content(self, mock_settings_cls):
        mock_settings = MagicMock()
        mock_settings.cv_content = None
        mock_settings_cls.return_value = mock_settings
        result = get_cv()
        assert result == ""


class TestListPipelineJobs:
    @patch("boss_career_ops.agent.tools.PipelineManager")
    def test_list_all(self, mock_pm_cls):
        mock_pm = MagicMock()
        mock_pm.__enter__ = MagicMock(return_value=mock_pm)
        mock_pm.__exit__ = MagicMock(return_value=False)
        mock_pm.list_jobs.return_value = [{"job_id": "job1"}, {"job_id": "job2"}]
        mock_pm_cls.return_value = mock_pm
        result = list_pipeline_jobs()
        assert len(result) == 2

    @patch("boss_career_ops.agent.tools.PipelineManager")
    def test_list_by_stage(self, mock_pm_cls):
        mock_pm = MagicMock()
        mock_pm.__enter__ = MagicMock(return_value=mock_pm)
        mock_pm.__exit__ = MagicMock(return_value=False)
        mock_pm.list_jobs.return_value = [{"job_id": "job1"}]
        mock_pm_cls.return_value = mock_pm
        result = list_pipeline_jobs(stage="评估")
        mock_pm.list_jobs.assert_called_once_with(stage="评估", status=None)


class TestGetJobWithAiResult:
    @patch("boss_career_ops.agent.tools.PipelineManager")
    def test_with_ai_results(self, mock_pm_cls):
        mock_pm = MagicMock()
        mock_pm.__enter__ = MagicMock(return_value=mock_pm)
        mock_pm.__exit__ = MagicMock(return_value=False)
        mock_pm.get_job.return_value = {"job_id": "job1"}
        mock_pm.get_ai_results.return_value = [
            {"task_type": "evaluate", "result": '{"score":4.2}'},
            {"task_type": "resume", "result": '{"content":"cv"}'},
        ]
        mock_pm_cls.return_value = mock_pm
        result = get_job_with_ai_result("job1")
        assert "ai_results" in result
        assert "evaluate" in result["ai_results"]
        assert result["ai_results"]["evaluate"]["score"] == 4.2


class TestWriteEvaluation:
    @patch("boss_career_ops.agent.tools.PipelineManager")
    def test_write_evaluation(self, mock_pm_cls):
        mock_pm = MagicMock()
        mock_pm.__enter__ = MagicMock(return_value=mock_pm)
        mock_pm.__exit__ = MagicMock(return_value=False)
        mock_pm_cls.return_value = mock_pm
        write_evaluation("job1", 4.2, "B", "匹配度较高", scores_detail={"匹配度": 4.0})
        mock_pm.save_ai_result.assert_called_once()
        call_args = mock_pm.save_ai_result.call_args
        assert call_args[0][0] == "job1"
        assert call_args[0][1] == "evaluate"
        parsed = json.loads(call_args[0][2])
        assert parsed["score"] == 4.2
        assert parsed["grade"] == "B"
        mock_pm.update_score.assert_called_once_with("job1", 4.2, "B")


class TestWriteResume:
    @patch("boss_career_ops.agent.tools.PipelineManager")
    def test_write_resume(self, mock_pm_cls):
        mock_pm = MagicMock()
        mock_pm.__enter__ = MagicMock(return_value=mock_pm)
        mock_pm.__exit__ = MagicMock(return_value=False)
        mock_pm_cls.return_value = mock_pm
        write_resume("job1", "# 简历\n润色后内容")
        mock_pm.save_ai_result.assert_called_once()
        call_args = mock_pm.save_ai_result.call_args
        assert call_args[0][0] == "job1"
        assert call_args[0][1] == "resume"
        parsed = json.loads(call_args[0][2])
        assert "润色" in parsed["content"]


class TestWriteChatSummary:
    @patch("boss_career_ops.agent.tools.PipelineManager")
    def test_write_chat_summary(self, mock_pm_cls):
        mock_pm = MagicMock()
        mock_pm.__enter__ = MagicMock(return_value=mock_pm)
        mock_pm.__exit__ = MagicMock(return_value=False)
        mock_pm_cls.return_value = mock_pm
        write_chat_summary("sec1", {"summary": "HR 表示感兴趣", "sentiment": "positive"})
        mock_pm.save_ai_result.assert_called_once()
        call_args = mock_pm.save_ai_result.call_args
        assert call_args[0][0] == "sec1"
        assert call_args[0][1] == "chat_summary"


class TestWriteInterviewPrep:
    @patch("boss_career_ops.agent.tools.PipelineManager")
    def test_write_interview_prep(self, mock_pm_cls):
        mock_pm = MagicMock()
        mock_pm.__enter__ = MagicMock(return_value=mock_pm)
        mock_pm.__exit__ = MagicMock(return_value=False)
        mock_pm_cls.return_value = mock_pm
        write_interview_prep("job1", {"tech_questions": ["Go 并发"]})
        mock_pm.save_ai_result.assert_called_once()
        call_args = mock_pm.save_ai_result.call_args
        assert call_args[0][0] == "job1"
        assert call_args[0][1] == "interview_prep"


class TestSearchJobs:
    @patch("boss_career_ops.agent.tools.get_active_adapter")
    def test_search_jobs_returns_results(self, mock_adapter_fn):
        from boss_career_ops.platform.models import Job

        mock_adapter = MagicMock()
        job1 = Job(
            job_id="job1",
            job_name="Python开发",
            company_name="公司A",
            city_name="深圳",
            salary_desc="20K-40K",
            skills=["Python"],
            security_id="sec1",
        )
        mock_adapter.search.return_value = [job1]
        mock_adapter.build_search_params.return_value = {"keyword": "Python", "city": ""}
        mock_adapter_fn.return_value = mock_adapter
        result = search_jobs("Python")
        assert len(result) == 1
        assert result[0]["job_id"] == "job1"
        assert result[0]["job_name"] == "Python开发"
        assert result[0]["city"] == "深圳"

    @patch("boss_career_ops.agent.tools.get_active_adapter")
    def test_search_jobs_adapter_error(self, mock_adapter_fn):
        mock_adapter_fn.side_effect = Exception("连接失败")
        result = search_jobs("Python")
        assert result == []


class TestGreetRecruiter:
    @patch("boss_career_ops.agent.tools.get_active_adapter")
    def test_greet_success(self, mock_adapter_fn):
        mock_adapter = MagicMock()
        mock_result = MagicMock()
        mock_result.ok = True
        mock_result.message = "打招呼成功"
        mock_adapter.greet.return_value = mock_result
        mock_adapter_fn.return_value = mock_adapter
        result = greet_recruiter("sec1", "job1")
        assert result.ok is True
        assert result.data["message"] == "打招呼成功"

    @patch("boss_career_ops.agent.tools.get_active_adapter")
    def test_greet_error(self, mock_adapter_fn):
        mock_adapter_fn.side_effect = Exception("连接失败")
        result = greet_recruiter("sec1", "job1")
        assert result.ok is False
        assert "连接失败" in result.error


class TestApplyJob:
    @patch("boss_career_ops.agent.tools.get_active_adapter")
    def test_apply_success(self, mock_adapter_fn):
        mock_adapter = MagicMock()
        mock_result = MagicMock()
        mock_result.ok = True
        mock_result.message = "投递成功"
        mock_adapter.apply.return_value = mock_result
        mock_adapter_fn.return_value = mock_adapter
        result = apply_job("sec1", "job1")
        assert result.ok is True
        assert result.data["message"] == "投递成功"

    @patch("boss_career_ops.agent.tools.get_active_adapter")
    def test_apply_error(self, mock_adapter_fn):
        mock_adapter_fn.side_effect = Exception("投递失败")
        result = apply_job("sec1", "job1")
        assert result.ok is False


class TestAnalyzeSkillGap:
    @patch("boss_career_ops.agent.tools.list_pipeline_jobs")
    @patch("boss_career_ops.agent.tools.get_profile")
    def test_with_skills_and_jobs(self, mock_get_profile, mock_list_jobs):
        mock_get_profile.return_value = {
            "name": "测试用户",
            "skills": ["Python", "Go"],
        }
        mock_list_jobs.return_value = [{"job_id": "job1"}, {"job_id": "job2"}]
        result = analyze_skill_gap()
        assert result["skills"] == ["Python", "Go"]
        assert result["jd_count"] == 2
        assert result["analysis_available"] is True

    @patch("boss_career_ops.agent.tools.list_pipeline_jobs")
    @patch("boss_career_ops.agent.tools.get_profile")
    def test_no_data_available(self, mock_get_profile, mock_list_jobs):
        mock_get_profile.return_value = {"name": "测试用户", "skills": []}
        mock_list_jobs.return_value = []
        result = analyze_skill_gap()
        assert result["analysis_available"] is False


class TestPrepareInterview:
    @patch("boss_career_ops.agent.tools.PipelineManager")
    def test_prepare_interview_existing_job_no_agent(self, mock_pm_cls):
        mock_pm = MagicMock()
        mock_pm.__enter__ = MagicMock(return_value=mock_pm)
        mock_pm.__exit__ = MagicMock(return_value=False)
        mock_pm.get_job.return_value = {"job_id": "job1", "job_name": "Python开发", "company_name": "公司A"}
        mock_pm.get_ai_results.return_value = []
        mock_pm.get_ai_result.return_value = None
        mock_pm_cls.return_value = mock_pm
        result = prepare_interview("job1")
        assert result.ok is False
        assert result.code == "AI_RESULT_NOT_FOUND"

    @patch("boss_career_ops.agent.tools.PipelineManager")
    def test_prepare_interview_existing_job_with_agent(self, mock_pm_cls):
        mock_pm = MagicMock()
        mock_pm.__enter__ = MagicMock(return_value=mock_pm)
        mock_pm.__exit__ = MagicMock(return_value=False)
        mock_pm.get_job.return_value = {"job_id": "job1", "job_name": "Python开发", "company_name": "公司A"}
        mock_pm.get_ai_results.return_value = [{"task_type": "interview_prep", "result": '{"questions": ["Q1"], "source": "agent"}'}]
        mock_pm.get_ai_result.return_value = {"task_type": "interview_prep", "result": '{"questions": ["Q1"]}'}
        mock_pm_cls.return_value = mock_pm
        result = prepare_interview("job1")
        assert result.ok is True
        assert result.data["source"] == "agent"

    @patch("boss_career_ops.agent.tools.PipelineManager")
    def test_prepare_interview_nonexistent_job(self, mock_pm_cls):
        mock_pm = MagicMock()
        mock_pm.__enter__ = MagicMock(return_value=mock_pm)
        mock_pm.__exit__ = MagicMock(return_value=False)
        mock_pm.get_job.return_value = None
        mock_pm_cls.return_value = mock_pm
        result = prepare_interview("missing")
        assert result.ok is False


class TestEvaluateJobHighLevel:
    @patch("boss_career_ops.agent.tools.write_evaluation")
    @patch("boss_career_ops.evaluator.engine.EvaluationEngine")
    @patch("boss_career_ops.agent.tools.PipelineManager")
    def test_evaluate_job_persists_result(self, mock_pm_cls, mock_engine_cls, mock_write_eval):
        mock_pm = MagicMock()
        mock_pm.__enter__ = MagicMock(return_value=mock_pm)
        mock_pm.__exit__ = MagicMock(return_value=False)
        mock_pm.get_job.return_value = {"job_id": "job1", "job_name": "Python开发"}
        mock_pm.get_ai_results.return_value = []
        mock_pm_cls.return_value = mock_pm

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

        result = evaluate_job("job1")

        assert result is not None
        assert result["total_score"] == 4.2
        assert result["grade"] == "B"
        mock_engine.evaluate.assert_called_once()
        mock_write_eval.assert_called_once_with(
            job_id="job1",
            score=4.2,
            grade="B",
            analysis="匹配度较高",
            scores_detail={"匹配度": 4.0, "薪资": 5.0},
        )

    @patch("boss_career_ops.agent.tools.PipelineManager")
    def test_evaluate_job_not_found(self, mock_pm_cls):
        mock_pm = MagicMock()
        mock_pm.__enter__ = MagicMock(return_value=mock_pm)
        mock_pm.__exit__ = MagicMock(return_value=False)
        mock_pm.get_job.return_value = None
        mock_pm_cls.return_value = mock_pm

        result = evaluate_job("missing")
        assert result is None


class TestGenerateResumeHighLevel:
    @patch("boss_career_ops.agent.tools.write_resume")
    @patch("boss_career_ops.resume.generator.ResumeGenerator")
    @patch("boss_career_ops.agent.tools.PipelineManager")
    def test_generate_resume_persists_result(self, mock_pm_cls, mock_gen_cls, mock_write_resume):
        mock_pm = MagicMock()
        mock_pm.__enter__ = MagicMock(return_value=mock_pm)
        mock_pm.__exit__ = MagicMock(return_value=False)
        mock_pm.get_job.return_value = {"job_id": "job1", "job_name": "Python开发"}
        mock_pm.get_ai_results.return_value = []
        mock_pm_cls.return_value = mock_pm

        mock_gen = MagicMock()
        mock_gen.generate.return_value = "# 简历\n针对职位定制"
        mock_gen_cls.return_value = mock_gen

        result = generate_resume("job1")

        assert result is not None
        assert "简历" in result
        mock_gen.generate.assert_called_once()
        mock_write_resume.assert_called_once_with(
            job_id="job1",
            markdown_content="# 简历\n针对职位定制",
        )

    @patch("boss_career_ops.agent.tools.PipelineManager")
    def test_generate_resume_not_found(self, mock_pm_cls):
        mock_pm = MagicMock()
        mock_pm.__enter__ = MagicMock(return_value=mock_pm)
        mock_pm.__exit__ = MagicMock(return_value=False)
        mock_pm.get_job.return_value = None
        mock_pm_cls.return_value = mock_pm

        result = generate_resume("missing")
        assert result is None

    @patch("boss_career_ops.agent.tools.write_resume")
    @patch("boss_career_ops.resume.generator.ResumeGenerator")
    @patch("boss_career_ops.agent.tools.PipelineManager")
    def test_generate_resume_empty_skips_persist(self, mock_pm_cls, mock_gen_cls, mock_write_resume):
        mock_pm = MagicMock()
        mock_pm.__enter__ = MagicMock(return_value=mock_pm)
        mock_pm.__exit__ = MagicMock(return_value=False)
        mock_pm.get_job.return_value = {"job_id": "job1", "job_name": "Python开发"}
        mock_pm.get_ai_results.return_value = []
        mock_pm_cls.return_value = mock_pm

        mock_gen = MagicMock()
        mock_gen.generate.return_value = ""
        mock_gen_cls.return_value = mock_gen

        result = generate_resume("job1")

        assert result == ""
        mock_write_resume.assert_not_called()
