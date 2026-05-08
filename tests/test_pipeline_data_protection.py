import json

from boss_career_ops.pipeline.manager import PipelineManager
from boss_career_ops.platform.models import Job


class TestUpdateJobDataEmptyProtection:
    """验证 update_job_data 不会用空值覆盖已有数据"""

    def test_empty_string_does_not_overwrite(self, tmp_dir):
        db = tmp_dir / "test.db"
        with PipelineManager(db) as pm:
            pm.upsert_job("j1", data={"description": "原始描述", "city_name": "深圳"})
            pm.update_job_data("j1", {"description": "", "city_name": ""})
            job = pm.get_job("j1")
            data = json.loads(job["data"])
            assert data["description"] == "原始描述"
            assert data["city_name"] == "深圳"

    def test_none_does_not_overwrite(self, tmp_dir):
        db = tmp_dir / "test.db"
        with PipelineManager(db) as pm:
            pm.upsert_job("j1", data={"salary_min": 20000, "skills": ["Python"]})
            pm.update_job_data("j1", {"salary_min": None, "skills": None})
            job = pm.get_job("j1")
            data = json.loads(job["data"])
            assert data["salary_min"] == 20000
            assert data["skills"] == ["Python"]

    def test_valid_value_does_overwrite(self, tmp_dir):
        db = tmp_dir / "test.db"
        with PipelineManager(db) as pm:
            pm.upsert_job("j1", data={"description": "旧描述", "city_name": "北京"})
            pm.update_job_data("j1", {"description": "新描述", "city_name": "上海"})
            job = pm.get_job("j1")
            data = json.loads(job["data"])
            assert data["description"] == "新描述"
            assert data["city_name"] == "上海"

    def test_mixed_empty_and_valid(self, tmp_dir):
        db = tmp_dir / "test.db"
        with PipelineManager(db) as pm:
            pm.upsert_job("j1", data={"description": "保留", "city_name": "深圳"})
            pm.update_job_data("j1", {"description": "", "city_name": "广州"})
            job = pm.get_job("j1")
            data = json.loads(job["data"])
            assert data["description"] == "保留"
            assert data["city_name"] == "广州"


class TestBatchAddJobsDataSource:
    """验证 batch_add_jobs 写入 data_source="search_api" """

    def test_batch_add_stores_search_api(self, tmp_dir):
        db = tmp_dir / "test.db"
        with PipelineManager(db) as pm:
            job = Job(
                job_id="j1",
                job_name="Python开发",
                company_name="测试公司",
                salary_desc="20K-40K",
                description="后端开发",
                city_name="深圳",
            )
            pm.batch_add_jobs([job])
            result = pm.get_job("j1")
            data = json.loads(result["data"])
            assert data["data_source"] == "search_api"


class TestExtractJobDataSource:
    """验证 _extract_job_data 的 data_source 参数"""

    def test_with_data_source(self):
        job = Job(
            job_id="j1",
            job_name="Python开发",
            description="后端开发",
            city_name="深圳",
        )
        data = PipelineManager._extract_job_data(job, data_source="detail_api")
        assert data["data_source"] == "detail_api"

    def test_without_data_source_backward_compatible(self):
        job = Job(
            job_id="j1",
            job_name="Python开发",
            description="后端开发",
            city_name="深圳",
        )
        data = PipelineManager._extract_job_data(job)
        assert "data_source" not in data
        assert data["description"] == "后端开发"
        assert data["city_name"] == "深圳"
