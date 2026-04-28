from unittest.mock import patch, MagicMock

from boss_career_ops.rag.indexer import Indexer


class TestIndexFromPipeline:
    @patch("boss_career_ops.rag.indexer.VectorStore")
    @patch("boss_career_ops.rag.indexer.PipelineManager")
    @patch("boss_career_ops.rag.indexer.Embedder")
    def test_indexes_all_jobs(self, mock_embedder_cls, mock_pm_cls, mock_vs_cls):
        mock_pm = MagicMock()
        mock_pm.__enter__ = MagicMock(return_value=mock_pm)
        mock_pm.__exit__ = MagicMock(return_value=False)
        mock_pm.list_jobs.return_value = [
            {
                "job_id": "job1",
                "job_name": "Python开发",
                "company_name": "公司A",
                "salary_desc": "20K-40K",
                "data": '{"skills": ["Python"], "description": "后端开发"}',
                "score": 3.5,
                "grade": "C",
            },
            {
                "job_id": "job2",
                "job_name": "Go开发",
                "company_name": "公司B",
                "salary_desc": "25K-50K",
                "data": '{"skills": ["Go"], "description": "微服务开发"}',
                "score": 4.0,
                "grade": "B",
            },
        ]
        mock_pm_cls.return_value = mock_pm
        mock_store = MagicMock()
        mock_vs_cls.return_value = mock_store
        mock_embedder_cls.return_value = MagicMock()
        with patch("boss_career_ops.rag.indexer.parse_salary", return_value=(20000, 40000, 12)):
            indexer = Indexer()
            count = indexer.index_from_pipeline()
        assert count == 2
        assert mock_store.add_jd.call_count == 2


class TestIndexSingleJd:
    @patch("boss_career_ops.rag.indexer.VectorStore")
    @patch("boss_career_ops.rag.indexer.PipelineManager")
    @patch("boss_career_ops.rag.indexer.Embedder")
    def test_index_single_existing_job(self, mock_embedder_cls, mock_pm_cls, mock_vs_cls):
        mock_pm = MagicMock()
        mock_pm.__enter__ = MagicMock(return_value=mock_pm)
        mock_pm.__exit__ = MagicMock(return_value=False)
        mock_pm.get_job.return_value = {
            "job_id": "job1",
            "job_name": "Python开发",
            "company_name": "公司A",
            "salary_desc": "20K-40K",
            "data": '{"skills": ["Python"], "description": "后端开发"}',
        }
        mock_pm_cls.return_value = mock_pm
        mock_store = MagicMock()
        mock_vs_cls.return_value = mock_store
        mock_embedder_cls.return_value = MagicMock()
        with patch("boss_career_ops.rag.indexer.parse_salary", return_value=(20000, 40000, 12)):
            indexer = Indexer()
            indexer.index_single_jd("job1")
        mock_store.add_jd.assert_called_once()

    @patch("boss_career_ops.rag.indexer.VectorStore")
    @patch("boss_career_ops.rag.indexer.PipelineManager")
    @patch("boss_career_ops.rag.indexer.Embedder")
    def test_index_single_nonexistent_job(self, mock_embedder_cls, mock_pm_cls, mock_vs_cls):
        mock_pm = MagicMock()
        mock_pm.__enter__ = MagicMock(return_value=mock_pm)
        mock_pm.__exit__ = MagicMock(return_value=False)
        mock_pm.get_job.return_value = None
        mock_pm_cls.return_value = mock_pm
        mock_store = MagicMock()
        mock_vs_cls.return_value = mock_store
        mock_embedder_cls.return_value = MagicMock()
        indexer = Indexer()
        indexer.index_single_jd("missing")
        mock_store.add_jd.assert_not_called()


class TestReindexAll:
    @patch("boss_career_ops.rag.indexer.VectorStore")
    @patch("boss_career_ops.rag.indexer.PipelineManager")
    @patch("boss_career_ops.rag.indexer.Embedder")
    def test_reindex_deletes_and_rebuilds(self, mock_embedder_cls, mock_pm_cls, mock_vs_cls):
        mock_pm = MagicMock()
        mock_pm.__enter__ = MagicMock(return_value=mock_pm)
        mock_pm.__exit__ = MagicMock(return_value=False)
        mock_pm.list_jobs.return_value = []
        mock_pm_cls.return_value = mock_pm
        mock_store = MagicMock()
        mock_vs_cls.return_value = mock_store
        mock_embedder_cls.return_value = MagicMock()
        indexer = Indexer()
        count = indexer.reindex_all()
        mock_store._client.delete_collection.assert_any_call("jd_knowledge")
        mock_store._client.delete_collection.assert_any_call("resume_templates")
        mock_store._client.delete_collection.assert_any_call("interview_experience")
