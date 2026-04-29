import json
import tempfile
from pathlib import Path

from boss_career_ops.pipeline.manager import PipelineManager, _PIPELINE_COLS, _AI_RESULT_COLS
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
    def test_save_and_get_ai_result(self, pipeline_manager):
        with pipeline_manager:
            result_json = json.dumps({"score": 85, "grade": "A"}, ensure_ascii=False)
            pipeline_manager.save_ai_result("job1", "evaluate", result_json)

            row = pipeline_manager.get_ai_result("job1", "evaluate")
            assert row is not None
            assert row["job_id"] == "job1"
            assert row["task_type"] == "evaluate"
            assert row["result"] == result_json
            assert row["source"] == "agent"

    def test_save_ai_result_upsert(self, pipeline_manager):
        with pipeline_manager:
            pipeline_manager.save_ai_result("job1", "evaluate", '{"score": 70}')
            pipeline_manager.save_ai_result("job1", "evaluate", '{"score": 90}')

            row = pipeline_manager.get_ai_result("job1", "evaluate")
            assert row["result"] == '{"score": 90}'

    def test_get_ai_result_not_found(self, pipeline_manager):
        with pipeline_manager:
            assert pipeline_manager.get_ai_result("no_job", "evaluate") is None

    def test_get_ai_results_multiple(self, pipeline_manager):
        with pipeline_manager:
            pipeline_manager.save_ai_result("job1", "evaluate", '{"score": 80}')
            pipeline_manager.save_ai_result("job1", "resume", '{"content": "cv"}')

            rows = pipeline_manager.get_ai_results("job1")
            assert len(rows) == 2
            types = {r["task_type"] for r in rows}
            assert types == {"evaluate", "resume"}

    def test_get_ai_results_empty(self, pipeline_manager):
        with pipeline_manager:
            assert pipeline_manager.get_ai_results("no_job") == []

    def test_save_ai_result_custom_source(self, pipeline_manager):
        with pipeline_manager:
            pipeline_manager.save_ai_result("job1", "evaluate", "{}", source="rule_engine")
            row = pipeline_manager.get_ai_result("job1", "evaluate")
            assert row["source"] == "rule_engine"

    def test_ai_result_without_open_raises(self, pipeline_manager):
        try:
            pipeline_manager.save_ai_result("job1", "evaluate", "{}")
            assert False, "应抛出 RuntimeError"
        except RuntimeError as e:
            assert "未打开" in str(e)


class TestBatchCommit:
    def test_batch_commit_multiple_writes(self, pipeline_manager):
        with pipeline_manager:
            with pipeline_manager.batch_commit():
                pipeline_manager.upsert_job("job1", job_name="A")
                pipeline_manager.upsert_job("job2", job_name="B")
                pipeline_manager.update_score("job1", 4.5, "B+")
                pipeline_manager.update_stage("job1", Stage.EVALUATED)
            job1 = pipeline_manager.get_job("job1")
            assert job1 is not None
            assert job1["job_name"] == "A"
            assert job1["score"] == 4.5
            assert job1["grade"] == "B+"
            assert job1["stage"] == Stage.EVALUATED.value
            job2 = pipeline_manager.get_job("job2")
            assert job2 is not None
            assert job2["job_name"] == "B"

    def test_batch_commit_ai_results(self, pipeline_manager):
        with pipeline_manager:
            with pipeline_manager.batch_commit():
                pipeline_manager.save_ai_result("job1", "evaluate", '{"score": 80}')
                pipeline_manager.save_ai_result("job1", "resume", '{"content": "cv"}')
            rows = pipeline_manager.get_ai_results("job1")
            assert len(rows) == 2

    def test_batch_mode_resets_after_context(self, pipeline_manager):
        with pipeline_manager:
            assert pipeline_manager._batch_mode is False
            with pipeline_manager.batch_commit():
                assert pipeline_manager._batch_mode is True
            assert pipeline_manager._batch_mode is False

    def test_batch_mode_resets_on_exception(self, pipeline_manager):
        with pipeline_manager:
            try:
                with pipeline_manager.batch_commit():
                    pipeline_manager.upsert_job("job1")
                    raise ValueError("test error")
            except ValueError:
                pass
            assert pipeline_manager._batch_mode is False

    def test_non_batch_still_auto_commits(self, pipeline_manager):
        with pipeline_manager:
            pipeline_manager.upsert_job("job1", job_name="Standalone")
            job = pipeline_manager.get_job("job1")
            assert job is not None
            assert job["job_name"] == "Standalone"

    def test_batch_commit_single_transaction(self, pipeline_manager):
        with pipeline_manager:
            with pipeline_manager.batch_commit():
                pipeline_manager.upsert_job("job1")
                pipeline_manager.upsert_job("job2")
                pipeline_manager.update_score("job1", 3.0, "C")
                job1 = pipeline_manager.get_job("job1")
                assert job1 is not None
                assert job1["score"] == 3.0
                job2 = pipeline_manager.get_job("job2")
                assert job2 is not None
            job1_after = pipeline_manager.get_job("job1")
            assert job1_after["score"] == 3.0
            assert job1_after["grade"] == "C"


class TestDatabaseIndexes:
    def test_indexes_exist(self, pipeline_manager):
        with pipeline_manager:
            cursor = pipeline_manager._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            )
            index_names = {row[0] for row in cursor.fetchall()}
        assert "idx_pipeline_stage" in index_names
        assert "idx_pipeline_updated" in index_names
        assert "idx_ai_results_job_task" in index_names


class TestColumnConstants:
    def test_pipeline_cols_match_schema(self, pipeline_manager):
        with pipeline_manager:
            cursor = pipeline_manager._conn.execute("PRAGMA table_info(pipeline)")
            db_cols = [row[1] for row in cursor.fetchall()]
        assert _PIPELINE_COLS == db_cols

    def test_ai_result_cols_match_schema(self, pipeline_manager):
        with pipeline_manager:
            cursor = pipeline_manager._conn.execute("PRAGMA table_info(ai_results)")
            db_cols = [row[1] for row in cursor.fetchall()]
        assert _AI_RESULT_COLS == db_cols

    def test_get_job_uses_pipeline_cols(self, pipeline_manager):
        with pipeline_manager:
            pipeline_manager.upsert_job("j1", job_name="Test", company_name="Co", salary_desc="10K", security_id="s1")
            job = pipeline_manager.get_job("j1")
            assert list(job.keys()) == _PIPELINE_COLS

    def test_get_ai_result_uses_ai_result_cols(self, pipeline_manager):
        with pipeline_manager:
            pipeline_manager.save_ai_result("j1", "evaluate", '{"score": 80}')
            result = pipeline_manager.get_ai_result("j1", "evaluate")
            assert list(result.keys()) == _AI_RESULT_COLS


class TestSchemaMigration:
    def test_new_db_has_status_column(self, tmp_dir):
        db = tmp_dir / "test_new.db"
        with PipelineManager(db) as pm:
            pm.upsert_job("job1", job_name="测试")
            job = pm.get_job("job1")
            assert job["status"] == "active"

    def test_legacy_db_migration_adds_status(self, tmp_dir):
        import sqlite3 as sq3

        db = tmp_dir / "legacy.db"
        conn = sq3.connect(str(db))
        conn.execute("""
            CREATE TABLE pipeline (
                job_id TEXT PRIMARY KEY,
                job_name TEXT DEFAULT '',
                company_name TEXT DEFAULT '',
                salary_desc TEXT DEFAULT '',
                stage TEXT NOT NULL DEFAULT '发现',
                score REAL DEFAULT 0.0,
                grade TEXT DEFAULT '',
                security_id TEXT DEFAULT '',
                data TEXT DEFAULT '{}',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        conn.execute(
            "INSERT INTO pipeline (job_id, stage, created_at, updated_at) VALUES (?, ?, ?, ?)",
            ("legacy1", "发现", 1000.0, 1000.0),
        )
        conn.commit()
        conn.close()

        with PipelineManager(db) as pm:
            pm.upsert_job("new1", job_name="新职位")
            new_job = pm.get_job("new1")
            assert new_job["status"] == "active"
            legacy_job = pm.get_job("legacy1")
            assert legacy_job is not None
            assert legacy_job["status"] == "active"

    def test_repeated_init_schema_no_error(self, tmp_dir):
        db = tmp_dir / "test_repeat.db"
        with PipelineManager(db) as pm:
            pm._schema_initialized = False
            pm._init_schema()
            pm._schema_initialized = False
            pm._init_schema()
            pm.upsert_job("job1")
            assert pm.get_job("job1") is not None

    def test_status_index_created(self, tmp_dir):
        db = tmp_dir / "test_idx.db"
        with PipelineManager(db) as pm:
            cursor = pm._conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
            index_names = {row[0] for row in cursor.fetchall()}
        assert "idx_pipeline_status" in index_names
