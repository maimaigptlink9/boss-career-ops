from unittest.mock import patch, MagicMock

from boss_career_ops.commands.interview import _generate_interview_prep


def _make_job(job_id="123", job_name="Golang工程师", company_name="测试公司", skills=None):
    job = MagicMock()
    job.job_id = job_id
    job.job_name = job_name
    job.company_name = company_name
    job.skills = skills if skills is not None else ["Go", "Kubernetes", "MySQL"]
    return job


class TestGenerateInterviewPrep:
    @patch("boss_career_ops.commands.interview.PipelineManager")
    @patch("boss_career_ops.commands.interview.Settings")
    def test_rule_based_fallback(self, MockSettings, MockPM):
        mock_pm = MagicMock()
        mock_pm.get_ai_result.return_value = None
        mock_pm.__enter__ = MagicMock(return_value=mock_pm)
        mock_pm.__exit__ = MagicMock(return_value=False)
        MockPM.return_value = mock_pm

        mock_settings = MagicMock()
        mock_settings.profile.skills = ["Go", "Docker", "Python"]
        MockSettings.return_value = mock_settings

        job = _make_job()
        result = _generate_interview_prep(job)

        assert result["ok"] is True
        assert result["source"] == "rule"
        assert result["job_name"] == "Golang工程师"
        assert "skills_match" in result
        assert "tips" in result
        assert len(result["tips"]) > 0

    @patch("boss_career_ops.commands.interview.PipelineManager")
    def test_agent_result_takes_priority(self, MockPM):
        mock_pm = MagicMock()
        mock_pm.get_ai_result.return_value = {
            "result": '{"ok": true, "questions": ["q1"], "source": "agent"}',
        }
        mock_pm.__enter__ = MagicMock(return_value=mock_pm)
        mock_pm.__exit__ = MagicMock(return_value=False)
        MockPM.return_value = mock_pm

        job = _make_job()
        result = _generate_interview_prep(job)

        assert result["source"] == "agent"
        assert result["ok"] is True

    @patch("boss_career_ops.commands.interview.PipelineManager")
    @patch("boss_career_ops.commands.interview.Settings")
    def test_empty_skills(self, MockSettings, MockPM):
        mock_pm = MagicMock()
        mock_pm.get_ai_result.return_value = None
        mock_pm.__enter__ = MagicMock(return_value=mock_pm)
        mock_pm.__exit__ = MagicMock(return_value=False)
        MockPM.return_value = mock_pm

        mock_settings = MagicMock()
        mock_settings.profile.skills = []
        MockSettings.return_value = mock_settings

        job = _make_job(skills=[])
        result = _generate_interview_prep(job)

        assert result["ok"] is True
        assert result["source"] == "rule"
        assert result["skills_match"]["matched"] == []
        assert result["skills_match"]["gap"] == []

    @patch("boss_career_ops.commands.interview.PipelineManager")
    @patch("boss_career_ops.commands.interview.Settings")
    def test_skill_matching(self, MockSettings, MockPM):
        mock_pm = MagicMock()
        mock_pm.get_ai_result.return_value = None
        mock_pm.__enter__ = MagicMock(return_value=mock_pm)
        mock_pm.__exit__ = MagicMock(return_value=False)
        MockPM.return_value = mock_pm

        mock_settings = MagicMock()
        mock_settings.profile.skills = ["Go", "Docker"]
        MockSettings.return_value = mock_settings

        job = _make_job(skills=["Go", "Kubernetes", "MySQL"])
        result = _generate_interview_prep(job)

        assert "Go" in result["skills_match"]["matched"]
        assert "Kubernetes" in result["skills_match"]["gap"]
