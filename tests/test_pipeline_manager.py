import json
import tempfile
from pathlib import Path

from boss_career_ops.config.singleton import SingletonMeta
from boss_career_ops.pipeline.manager import PipelineManager
from boss_career_ops.pipeline.stages import Stage


class TestPipelineManager:
    def test_context_manager(self, tmp_dir):
        db = tmp_dir / "test_pipeline.db"
        with PipelineManager(db) as pm:
            assert pm._conn is not None
        assert pm._conn is None

    def test_upsert_and_get_job(self, tmp_dir):
        db = tmp_dir / "test_pipeline.db"
        with PipelineManager(db) as pm:
            pm.upsert_job("job1", job_name="Golang工程师", company_name="测试公司")
            job = pm.get_job("job1")
            assert job is not None
            assert job["job_name"] == "Golang工程师"
            assert job["stage"] == Stage.DISCOVERED.value

    def test_get_nonexistent_job(self, tmp_dir):
        db = tmp_dir / "test_pipeline.db"
        with PipelineManager(db) as pm:
            assert pm.get_job("missing") is None

    def test_update_stage(self, tmp_dir):
        db = tmp_dir / "test_pipeline.db"
        with PipelineManager(db) as pm:
            pm.upsert_job("job1")
            pm.update_stage("job1", Stage.EVALUATED)
            job = pm.get_job("job1")
            assert job["stage"] == Stage.EVALUATED.value

    def test_update_score(self, tmp_dir):
        db = tmp_dir / "test_pipeline.db"
        with PipelineManager(db) as pm:
            pm.upsert_job("job1")
            pm.update_score("job1", 4.2, "B")
            job = pm.get_job("job1")
            assert job["score"] == 4.2
            assert job["grade"] == "B"

    def test_list_jobs(self, tmp_dir):
        db = tmp_dir / "test_pipeline.db"
        with PipelineManager(db) as pm:
            pm.upsert_job("job1", job_name="A")
            pm.upsert_job("job2", job_name="B")
            jobs = pm.list_jobs()
            assert len(jobs) == 2

    def test_list_jobs_by_stage(self, tmp_dir):
        db = tmp_dir / "test_pipeline.db"
        with PipelineManager(db) as pm:
            pm.upsert_job("job1")
            pm.update_stage("job1", Stage.EVALUATED)
            pm.upsert_job("job2")
            jobs = pm.list_jobs(stage=Stage.EVALUATED.value)
            assert len(jobs) == 1

    def test_get_daily_summary(self, tmp_dir):
        db = tmp_dir / "test_pipeline.db"
        with PipelineManager(db) as pm:
            pm.upsert_job("job1")
            pm.upsert_job("job2")
            summary = pm.get_daily_summary()
            assert "new_today" in summary
            assert "by_stage" in summary
            assert "total" in summary
            assert summary["total"] == 2

    def test_not_opened_raises(self, tmp_dir):
        db = tmp_dir / "test_pipeline.db"
        pm = PipelineManager(db)
        try:
            pm.upsert_job("job1")
            assert False, "应抛出 RuntimeError"
        except RuntimeError:
            pass

    def test_upsert_job_idempotent(self, tmp_dir):
        db = tmp_dir / "test_pipeline.db"
        with PipelineManager(db) as pm:
            pm.upsert_job("job1", job_name="First")
            pm.upsert_job("job1", job_name="Second")
            job = pm.get_job("job1")
            assert job["job_name"] == "First"

    def test_nested_context_manager(self, tmp_dir):
        """测试嵌套 context manager 不会关闭连接"""
        db = tmp_dir / "test_pipeline.db"
        pm = PipelineManager(db)
        with pm:
            pm.upsert_job("job1", job_name="Golang工程师")
            with pm:
                pm.upsert_job("job2", job_name="Python工程师")
                job2 = pm.get_job("job2")
                assert job2 is not None
                assert pm._conn is not None
            assert pm._conn is not None
            job1 = pm.get_job("job1")
            assert job1 is not None
        assert pm._conn is None

    def test_ref_count_reset(self, tmp_dir):
        """测试引用计数正确归零"""
        db = tmp_dir / "test_pipeline.db"
        pm = PipelineManager(db)
        assert pm._ref_count == 0
        with pm:
            assert pm._ref_count == 1
            with pm:
                assert pm._ref_count == 2
            assert pm._ref_count == 1
        assert pm._ref_count == 0

    def test_multiple_context_managers_same_instance(self, tmp_dir):
        """测试同一实例多次使用 context manager"""
        db = tmp_dir / "test_pipeline.db"
        pm = PipelineManager(db)
        with pm:
            pm.upsert_job("job1")
        assert pm._conn is None
        with pm:
            job = pm.get_job("job1")
            assert job is not None
        assert pm._conn is None


class TestPipelineAIResults:
    def _make_manager(self, tmp_path):
        SingletonMeta.reset(PipelineManager)
        return PipelineManager(db_path=tmp_path / "test_pipeline.db")

    def test_save_and_get_ai_result(self, tmp_dir):
        mgr = self._make_manager(tmp_dir)
        with mgr:
            result_json = json.dumps({"score": 85, "grade": "A"}, ensure_ascii=False)
            mgr.save_ai_result("job1", "evaluate", result_json)

            row = mgr.get_ai_result("job1", "evaluate")
            assert row is not None
            assert row["job_id"] == "job1"
            assert row["task_type"] == "evaluate"
            assert row["result"] == result_json
            assert row["source"] == "agent"

    def test_save_ai_result_upsert(self, tmp_dir):
        mgr = self._make_manager(tmp_dir)
        with mgr:
            mgr.save_ai_result("job1", "evaluate", '{"score": 70}')
            mgr.save_ai_result("job1", "evaluate", '{"score": 90}')

            row = mgr.get_ai_result("job1", "evaluate")
            assert row["result"] == '{"score": 90}'

    def test_get_ai_result_not_found(self, tmp_dir):
        mgr = self._make_manager(tmp_dir)
        with mgr:
            assert mgr.get_ai_result("no_job", "evaluate") is None

    def test_get_ai_results_multiple(self, tmp_dir):
        mgr = self._make_manager(tmp_dir)
        with mgr:
            mgr.save_ai_result("job1", "evaluate", '{"score": 80}')
            mgr.save_ai_result("job1", "resume", '{"content": "cv"}')

            rows = mgr.get_ai_results("job1")
            assert len(rows) == 2
            types = {r["task_type"] for r in rows}
            assert types == {"evaluate", "resume"}

    def test_get_ai_results_empty(self, tmp_dir):
        mgr = self._make_manager(tmp_dir)
        with mgr:
            assert mgr.get_ai_results("no_job") == []

    def test_save_ai_result_custom_source(self, tmp_dir):
        mgr = self._make_manager(tmp_dir)
        with mgr:
            mgr.save_ai_result("job1", "evaluate", "{}", source="rule_engine")
            row = mgr.get_ai_result("job1", "evaluate")
            assert row["source"] == "rule_engine"

    def test_ai_result_without_open_raises(self, tmp_dir):
        SingletonMeta.reset(PipelineManager)
        mgr = PipelineManager(db_path=tmp_dir / "never.db")
        try:
            mgr.save_ai_result("job1", "evaluate", "{}")
            assert False, "应抛出 RuntimeError"
        except RuntimeError as e:
            assert "未打开" in str(e)
