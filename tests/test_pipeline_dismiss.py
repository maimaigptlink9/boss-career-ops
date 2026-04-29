from boss_career_ops.pipeline.manager import PipelineManager, STATUS_ACTIVE, STATUS_DISMISSED
from boss_career_ops.pipeline.stages import Stage


class TestDismissRestore:
    def test_dismiss_job(self, tmp_dir):
        db = tmp_dir / "test.db"
        with PipelineManager(db) as pm:
            pm.upsert_job("j1", job_name="Test")
            assert pm.dismiss_job("j1") is True
            job = pm.get_job("j1")
            assert job["status"] == STATUS_DISMISSED

    def test_dismiss_already_dismissed_returns_false(self, tmp_dir):
        db = tmp_dir / "test.db"
        with PipelineManager(db) as pm:
            pm.upsert_job("j1")
            assert pm.dismiss_job("j1") is True
            assert pm.dismiss_job("j1") is False

    def test_dismiss_nonexistent_returns_false(self, tmp_dir):
        db = tmp_dir / "test.db"
        with PipelineManager(db) as pm:
            assert pm.dismiss_job("nope") is False

    def test_restore_job(self, tmp_dir):
        db = tmp_dir / "test.db"
        with PipelineManager(db) as pm:
            pm.upsert_job("j1")
            pm.dismiss_job("j1")
            assert pm.restore_job("j1") is True
            job = pm.get_job("j1")
            assert job["status"] == STATUS_ACTIVE

    def test_restore_active_returns_false(self, tmp_dir):
        db = tmp_dir / "test.db"
        with PipelineManager(db) as pm:
            pm.upsert_job("j1")
            assert pm.restore_job("j1") is False

    def test_is_dismissed(self, tmp_dir):
        db = tmp_dir / "test.db"
        with PipelineManager(db) as pm:
            pm.upsert_job("j1")
            assert pm.is_dismissed("j1") is False
            pm.dismiss_job("j1")
            assert pm.is_dismissed("j1") is True
            assert pm.is_dismissed("nope") is False


class TestBatchDismiss:
    def test_batch_dismiss(self, tmp_dir):
        db = tmp_dir / "test.db"
        with PipelineManager(db) as pm:
            pm.upsert_job("j1")
            pm.upsert_job("j2")
            pm.upsert_job("j3")
            count = pm.batch_dismiss(["j1", "j2"])
            assert count == 2
            assert pm.is_dismissed("j1") is True
            assert pm.is_dismissed("j2") is True
            assert pm.is_dismissed("j3") is False

    def test_batch_dismiss_empty(self, tmp_dir):
        db = tmp_dir / "test.db"
        with PipelineManager(db) as pm:
            assert pm.batch_dismiss([]) == 0

    def test_batch_dismiss_by_score(self, tmp_dir):
        db = tmp_dir / "test.db"
        with PipelineManager(db) as pm:
            pm.upsert_job("j1")
            pm.update_score("j1", 30.0, "D")
            pm.upsert_job("j2")
            pm.update_score("j2", 80.0, "A")
            pm.upsert_job("j3")
            pm.update_score("j3", 25.0, "E")
            count = pm.batch_dismiss_by_score(40.0)
            assert count == 2
            assert pm.is_dismissed("j1") is True
            assert pm.is_dismissed("j2") is False
            assert pm.is_dismissed("j3") is True

    def test_batch_dismiss_by_grade(self, tmp_dir):
        db = tmp_dir / "test.db"
        with PipelineManager(db) as pm:
            pm.upsert_job("j1")
            pm.update_score("j1", 30.0, "D")
            pm.upsert_job("j2")
            pm.update_score("j2", 80.0, "A")
            pm.upsert_job("j3")
            pm.update_score("j3", 20.0, "E")
            count = pm.batch_dismiss_by_grade(["D", "E"])
            assert count == 2
            assert pm.is_dismissed("j1") is True
            assert pm.is_dismissed("j2") is False
            assert pm.is_dismissed("j3") is True

    def test_batch_restore(self, tmp_dir):
        db = tmp_dir / "test.db"
        with PipelineManager(db) as pm:
            pm.upsert_job("j1")
            pm.upsert_job("j2")
            pm.batch_dismiss(["j1", "j2"])
            count = pm.batch_restore(["j1"])
            assert count == 1
            assert pm.is_dismissed("j1") is False
            assert pm.is_dismissed("j2") is True


class TestListJobsStatusFilter:
    def test_list_jobs_default_active_only(self, tmp_dir):
        db = tmp_dir / "test.db"
        with PipelineManager(db) as pm:
            pm.upsert_job("j1", job_name="Active")
            pm.upsert_job("j2", job_name="Dismissed")
            pm.dismiss_job("j2")
            jobs = pm.list_jobs()
            assert len(jobs) == 1
            assert jobs[0]["job_id"] == "j1"

    def test_list_jobs_dismissed_only(self, tmp_dir):
        db = tmp_dir / "test.db"
        with PipelineManager(db) as pm:
            pm.upsert_job("j1")
            pm.upsert_job("j2")
            pm.dismiss_job("j2")
            jobs = pm.list_jobs(status=STATUS_DISMISSED)
            assert len(jobs) == 1
            assert jobs[0]["job_id"] == "j2"

    def test_list_jobs_all_statuses(self, tmp_dir):
        db = tmp_dir / "test.db"
        with PipelineManager(db) as pm:
            pm.upsert_job("j1")
            pm.upsert_job("j2")
            pm.dismiss_job("j2")
            jobs = pm.list_jobs(status=None)
            assert len(jobs) == 2

    def test_list_jobs_stage_and_status(self, tmp_dir):
        db = tmp_dir / "test.db"
        with PipelineManager(db) as pm:
            pm.upsert_job("j1")
            pm.update_stage("j1", Stage.EVALUATED)
            pm.upsert_job("j2")
            pm.dismiss_job("j2")
            pm.upsert_job("j3")
            pm.update_stage("j3", Stage.EVALUATED)
            jobs = pm.list_jobs(stage=Stage.EVALUATED.value, status=STATUS_ACTIVE)
            assert len(jobs) == 2
            ids = {j["job_id"] for j in jobs}
            assert ids == {"j1", "j3"}


class TestBatchAddSkipsDismissed:
    def test_batch_add_skips_dismissed(self, tmp_dir):
        db = tmp_dir / "test.db"
        with PipelineManager(db) as pm:
            pm.upsert_job("j1", job_name="Old")
            pm.dismiss_job("j1")
            pm.batch_add_jobs([
                {"encryptJobId": "j1", "jobName": "New", "brandName": "Co", "salaryDesc": "10K"},
                {"encryptJobId": "j2", "jobName": "New2", "brandName": "Co2", "salaryDesc": "20K"},
            ])
            assert pm.is_dismissed("j1") is True
            job1 = pm.get_job("j1")
            assert job1["job_name"] == "Old"
            job2 = pm.get_job("j2")
            assert job2 is not None
            assert job2["job_name"] == "New2"


class TestGetUnevaluated:
    def test_get_unevaluated(self, tmp_dir):
        db = tmp_dir / "test.db"
        with PipelineManager(db) as pm:
            pm.upsert_job("j1")
            pm.upsert_job("j2")
            pm.update_stage("j2", Stage.EVALUATED)
            pm.upsert_job("j3")
            pending = pm.get_unevaluated()
            assert len(pending) == 2
            ids = {j["job_id"] for j in pending}
            assert ids == {"j1", "j3"}

    def test_get_unevaluated_skips_dismissed(self, tmp_dir):
        db = tmp_dir / "test.db"
        with PipelineManager(db) as pm:
            pm.upsert_job("j1")
            pm.dismiss_job("j1")
            pm.upsert_job("j2")
            pending = pm.get_unevaluated()
            assert len(pending) == 1
            assert pending[0]["job_id"] == "j2"

    def test_get_unevaluated_limit(self, tmp_dir):
        db = tmp_dir / "test.db"
        with PipelineManager(db) as pm:
            for i in range(10):
                pm.upsert_job(f"j{i}")
            pending = pm.get_unevaluated(limit=3)
            assert len(pending) == 3

    def test_get_unevaluated_empty(self, tmp_dir):
        db = tmp_dir / "test.db"
        with PipelineManager(db) as pm:
            assert pm.get_unevaluated() == []
