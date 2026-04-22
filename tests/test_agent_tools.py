import json
from unittest.mock import patch, MagicMock

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
)
from boss_career_ops.config.singleton import SingletonMeta
from boss_career_ops.pipeline.manager import PipelineManager


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
        mock_pm.list_jobs.assert_called_once_with(stage="评估")


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
