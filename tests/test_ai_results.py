import json

from boss_career_ops.pipeline.manager import PipelineManager
from boss_career_ops.config.singleton import SingletonMeta


class TestAIResultsTable:
    def _make_manager(self, tmp_dir):
        SingletonMeta.reset(PipelineManager)
        return PipelineManager(db_path=tmp_dir / "test_ai_results.db")

    def test_save_and_get_evaluate_result(self, tmp_dir):
        mgr = self._make_manager(tmp_dir)
        with mgr:
            result_data = {"score": 4.2, "grade": "B", "analysis": "匹配度较高"}
            mgr.save_ai_result("job1", "evaluate", json.dumps(result_data, ensure_ascii=False))
            row = mgr.get_ai_result("job1", "evaluate")
            assert row is not None
            parsed = json.loads(row["result"])
            assert parsed["score"] == 4.2
            assert parsed["grade"] == "B"

    def test_save_and_get_resume_result(self, tmp_dir):
        mgr = self._make_manager(tmp_dir)
        with mgr:
            result_data = {"content": "# 简历\n这是润色后的简历"}
            mgr.save_ai_result("job1", "resume", json.dumps(result_data, ensure_ascii=False))
            row = mgr.get_ai_result("job1", "resume")
            assert row is not None
            parsed = json.loads(row["result"])
            assert "润色" in parsed["content"]

    def test_save_and_get_chat_summary(self, tmp_dir):
        mgr = self._make_manager(tmp_dir)
        with mgr:
            result_data = {"summary": "HR 表示对简历感兴趣", "sentiment": "positive"}
            mgr.save_ai_result("sec1", "chat_summary", json.dumps(result_data, ensure_ascii=False))
            row = mgr.get_ai_result("sec1", "chat_summary")
            assert row is not None
            parsed = json.loads(row["result"])
            assert parsed["sentiment"] == "positive"

    def test_save_and_get_interview_prep(self, tmp_dir):
        mgr = self._make_manager(tmp_dir)
        with mgr:
            result_data = {"tech_questions": ["Go 并发模型", "微服务架构"], "star_stories": ["项目A"]}
            mgr.save_ai_result("job1", "interview_prep", json.dumps(result_data, ensure_ascii=False))
            row = mgr.get_ai_result("job1", "interview_prep")
            assert row is not None
            parsed = json.loads(row["result"])
            assert len(parsed["tech_questions"]) == 2

    def test_unique_constraint_upsert(self, tmp_dir):
        mgr = self._make_manager(tmp_dir)
        with mgr:
            mgr.save_ai_result("job1", "evaluate", '{"score": 3.0}')
            mgr.save_ai_result("job1", "evaluate", '{"score": 4.5}')
            row = mgr.get_ai_result("job1", "evaluate")
            parsed = json.loads(row["result"])
            assert parsed["score"] == 4.5
            all_results = mgr.get_ai_results("job1")
            evaluate_results = [r for r in all_results if r["task_type"] == "evaluate"]
            assert len(evaluate_results) == 1

    def test_different_task_types_coexist(self, tmp_dir):
        mgr = self._make_manager(tmp_dir)
        with mgr:
            mgr.save_ai_result("job1", "evaluate", '{"score": 4.0}')
            mgr.save_ai_result("job1", "resume", '{"content": "cv"}')
            mgr.save_ai_result("job1", "interview_prep", '{"questions": []}')
            all_results = mgr.get_ai_results("job1")
            assert len(all_results) == 3
            types = {r["task_type"] for r in all_results}
            assert types == {"evaluate", "resume", "interview_prep"}

    def test_get_nonexistent_result(self, tmp_dir):
        mgr = self._make_manager(tmp_dir)
        with mgr:
            assert mgr.get_ai_result("no_job", "evaluate") is None

    def test_get_ai_results_empty(self, tmp_dir):
        mgr = self._make_manager(tmp_dir)
        with mgr:
            assert mgr.get_ai_results("no_job") == []

    def test_json_serialization_chinese(self, tmp_dir):
        mgr = self._make_manager(tmp_dir)
        with mgr:
            result_data = {"analysis": "匹配度较高，薪资符合预期", "recommendation": "值得投入"}
            mgr.save_ai_result("job1", "evaluate", json.dumps(result_data, ensure_ascii=False))
            row = mgr.get_ai_result("job1", "evaluate")
            parsed = json.loads(row["result"])
            assert "匹配度" in parsed["analysis"]
            assert "值得投入" in parsed["recommendation"]

    def test_default_source_is_agent(self, tmp_dir):
        mgr = self._make_manager(tmp_dir)
        with mgr:
            mgr.save_ai_result("job1", "evaluate", '{}')
            row = mgr.get_ai_result("job1", "evaluate")
            assert row["source"] == "agent"

    def test_custom_source(self, tmp_dir):
        mgr = self._make_manager(tmp_dir)
        with mgr:
            mgr.save_ai_result("job1", "evaluate", '{}', source="rule_engine")
            row = mgr.get_ai_result("job1", "evaluate")
            assert row["source"] == "rule_engine"

    def test_not_opened_raises(self, tmp_dir):
        SingletonMeta.reset(PipelineManager)
        mgr = PipelineManager(db_path=tmp_dir / "never.db")
        try:
            mgr.save_ai_result("job1", "evaluate", '{}')
            assert False, "应抛出 RuntimeError"
        except RuntimeError:
            pass
