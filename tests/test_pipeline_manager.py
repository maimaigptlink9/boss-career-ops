from boss_career_ops.pipeline.manager import PipelineManager
from boss_career_ops.pipeline.stages import Stage


class TestPipelineManager:
    def test_context_manager(self, tmp_dir):
        db = tmp_dir / "test_pipeline.db"
        with PipelineManager(db) as pm:
            assert pm._conn is not None
        assert pm._conn is None

    def test_add_and_get_job(self, tmp_dir):
        db = tmp_dir / "test_pipeline.db"
        with PipelineManager(db) as pm:
            pm.add_job("job1", job_name="Golang工程师", company_name="测试公司")
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
            pm.add_job("job1")
            pm.update_stage("job1", Stage.EVALUATED)
            job = pm.get_job("job1")
            assert job["stage"] == Stage.EVALUATED.value

    def test_update_score(self, tmp_dir):
        db = tmp_dir / "test_pipeline.db"
        with PipelineManager(db) as pm:
            pm.add_job("job1")
            pm.update_score("job1", 4.2, "B")
            job = pm.get_job("job1")
            assert job["score"] == 4.2
            assert job["grade"] == "B"

    def test_advance_stage(self, tmp_dir):
        db = tmp_dir / "test_pipeline.db"
        with PipelineManager(db) as pm:
            pm.add_job("job1")
            result = pm.advance_stage("job1")
            assert result == Stage.EVALUATED
            job = pm.get_job("job1")
            assert job["stage"] == Stage.EVALUATED.value

    def test_advance_stage_at_offer(self, tmp_dir):
        db = tmp_dir / "test_pipeline.db"
        with PipelineManager(db) as pm:
            pm.add_job("job1")
            pm.update_stage("job1", Stage.OFFER)
            result = pm.advance_stage("job1")
            assert result is None

    def test_advance_stage_nonexistent(self, tmp_dir):
        db = tmp_dir / "test_pipeline.db"
        with PipelineManager(db) as pm:
            result = pm.advance_stage("missing")
            assert result is None

    def test_list_jobs(self, tmp_dir):
        db = tmp_dir / "test_pipeline.db"
        with PipelineManager(db) as pm:
            pm.add_job("job1", job_name="A")
            pm.add_job("job2", job_name="B")
            jobs = pm.list_jobs()
            assert len(jobs) == 2

    def test_list_jobs_by_stage(self, tmp_dir):
        db = tmp_dir / "test_pipeline.db"
        with PipelineManager(db) as pm:
            pm.add_job("job1")
            pm.update_stage("job1", Stage.EVALUATED)
            pm.add_job("job2")
            jobs = pm.list_jobs(stage=Stage.EVALUATED.value)
            assert len(jobs) == 1

    def test_get_daily_summary(self, tmp_dir):
        db = tmp_dir / "test_pipeline.db"
        with PipelineManager(db) as pm:
            pm.add_job("job1")
            pm.add_job("job2")
            summary = pm.get_daily_summary()
            assert "new_today" in summary
            assert "by_stage" in summary
            assert "total" in summary
            assert summary["total"] == 2

    def test_not_opened_raises(self, tmp_dir):
        db = tmp_dir / "test_pipeline.db"
        pm = PipelineManager(db)
        try:
            pm.add_job("job1")
            assert False, "应抛出 RuntimeError"
        except RuntimeError:
            pass

    def test_add_job_idempotent(self, tmp_dir):
        db = tmp_dir / "test_pipeline.db"
        with PipelineManager(db) as pm:
            pm.add_job("job1", job_name="First")
            pm.add_job("job1", job_name="Second")
            job = pm.get_job("job1")
            assert job["job_name"] == "First"
