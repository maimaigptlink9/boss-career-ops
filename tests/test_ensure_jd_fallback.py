import json
from unittest.mock import MagicMock, patch

from boss_career_ops.pipeline.manager import PipelineManager
from boss_career_ops.platform.models import Job
from boss_career_ops.config.singleton import SingletonMeta


class TestEnsureJobDescriptionFallback:
    def setup_method(self):
        SingletonMeta._instances.clear()

    def teardown_method(self):
        SingletonMeta._instances.clear()

    @patch("boss_career_ops.pipeline.manager.get_active_adapter")
    def test_passes_job_id_and_security_id_lid(self, mock_get_adapter, tmp_path):
        mock_adapter = MagicMock()
        mock_get_adapter.return_value = mock_adapter

        SingletonMeta.reset(PipelineManager)
        pm = PipelineManager(db_path=tmp_path / "test.db")
        pm.open()
        pm.upsert_job("job1", security_id="sec1")
        pm.update_job_data("job1", {"lid": "lid123"})

        api_job = Job(
            job_id="job1",
            security_id="sec1",
            description="岗位描述",
            raw_data={},
        )
        mock_adapter.get_job_detail.return_value = api_job

        pm.get_job_detail("job1")
        mock_adapter.get_job_detail.assert_called_once_with(
            "job1", security_id="sec1", lid="lid123"
        )
        pm.close()

    @patch("boss_career_ops.pipeline.manager.get_active_adapter")
    def test_data_source_card_api(self, mock_get_adapter, tmp_path):
        mock_adapter = MagicMock()
        mock_get_adapter.return_value = mock_adapter

        SingletonMeta.reset(PipelineManager)
        pm = PipelineManager(db_path=tmp_path / "test.db")
        pm.open()
        pm.upsert_job("job1", security_id="sec1")

        api_job = Job(
            job_id="job1",
            security_id="sec1",
            description="岗位描述",
            raw_data={"_card_fetched": True},
        )
        mock_adapter.get_job_detail.return_value = api_job

        pm._ensure_job_description(pm.get_job("job1"))
        job = pm.get_job("job1")
        data = json.loads(job["data"])
        assert data["data_source"] == "card_api"
        pm.close()

    @patch("boss_career_ops.pipeline.manager.get_active_adapter")
    def test_data_source_detail_api(self, mock_get_adapter, tmp_path):
        mock_adapter = MagicMock()
        mock_get_adapter.return_value = mock_adapter

        SingletonMeta.reset(PipelineManager)
        pm = PipelineManager(db_path=tmp_path / "test.db")
        pm.open()
        pm.upsert_job("job1", security_id="sec1")

        api_job = Job(
            job_id="job1",
            security_id="sec1",
            description="岗位描述",
            raw_data={},
        )
        mock_adapter.get_job_detail.return_value = api_job

        pm._ensure_job_description(pm.get_job("job1"))
        job = pm.get_job("job1")
        data = json.loads(job["data"])
        assert data["data_source"] == "detail_api"
        pm.close()

    def test_lid_stored_in_raw_data_from_search(self):
        result = []
        for j in [{"encryptJobId": "j1", "lid": "lid_abc"}]:
            job = Job(job_id="j1", raw_data={})
            if j.get("lid"):
                job.raw_data["lid"] = j["lid"]
            result.append(job)

        assert result[0].raw_data["lid"] == "lid_abc"

    def test_extract_job_data_includes_lid(self):
        job = Job(
            job_id="j1",
            description="描述",
            raw_data={"lid": "lid_xyz"},
        )
        data = PipelineManager._extract_job_data(job, data_source="detail_api")
        assert data["lid"] == "lid_xyz"

    def test_extract_job_data_no_lid(self):
        job = Job(
            job_id="j1",
            description="描述",
            raw_data={},
        )
        data = PipelineManager._extract_job_data(job, data_source="detail_api")
        assert "lid" not in data
