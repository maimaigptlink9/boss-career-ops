from unittest.mock import patch, MagicMock

from boss_career_ops.rag.retriever import Retriever


class TestFindSimilarJds:
    @patch("boss_career_ops.rag.retriever.VectorStore")
    def test_find_similar_jds_no_filters(self, mock_vs_cls):
        mock_store = MagicMock()
        mock_vs_cls.return_value = mock_store
        mock_store.search_jd.return_value = [
            {"id": "jd001", "content": "Python开发", "distance": 0.1}
        ]
        retriever = Retriever()
        results = retriever.find_similar_jds("Python开发")
        assert len(results) == 1
        mock_store.search_jd.assert_called_once_with("Python开发", n=10, filters=None)

    @patch("boss_career_ops.rag.retriever.VectorStore")
    def test_find_similar_jds_with_city_filter(self, mock_vs_cls):
        mock_store = MagicMock()
        mock_vs_cls.return_value = mock_store
        mock_store.search_jd.return_value = []
        retriever = Retriever()
        retriever.find_similar_jds("Python", city="深圳")
        mock_store.search_jd.assert_called_once_with("Python", n=10, filters={"city": "深圳"})


class TestFindMatchingResumes:
    @patch("boss_career_ops.rag.retriever.VectorStore")
    def test_find_matching_resumes(self, mock_vs_cls):
        mock_store = MagicMock()
        mock_vs_cls.return_value = mock_store
        mock_store.search_resume.return_value = [
            {"id": "resume001", "content": "简历内容", "distance": 0.2}
        ]
        retriever = Retriever()
        results = retriever.find_matching_resumes("Python后端开发")
        assert len(results) == 1
        mock_store.search_resume.assert_called_once_with("Python后端开发", n=5)


class TestGetSkillMarketDemand:
    @patch("boss_career_ops.rag.retriever.VectorStore")
    def test_get_skill_market_demand_batch_query(self, mock_vs_cls):
        mock_store = MagicMock()
        mock_vs_cls.return_value = mock_store
        mock_store.search_jd.return_value = [
            {"id": "jd1", "content": "需要Python和Go开发经验"},
            {"id": "jd2", "content": "Python后端开发岗位"},
            {"id": "jd3", "content": "Go微服务开发"},
            {"id": "jd4", "content": "Java开发工程师"},
        ]
        retriever = Retriever()
        demand = retriever.get_skill_market_demand(["Python", "Go"])
        mock_store.search_jd.assert_called_once_with("Python OR Go", n=500)
        assert demand["Python"] == 2
        assert demand["Go"] == 2

    @patch("boss_career_ops.rag.retriever.VectorStore")
    def test_get_skill_market_demand_empty_skills(self, mock_vs_cls):
        mock_store = MagicMock()
        mock_vs_cls.return_value = mock_store
        retriever = Retriever()
        demand = retriever.get_skill_market_demand([])
        assert demand == {}
        mock_store.search_jd.assert_not_called()

    @patch("boss_career_ops.rag.retriever.VectorStore")
    def test_get_skill_market_demand_with_error(self, mock_vs_cls):
        mock_store = MagicMock()
        mock_vs_cls.return_value = mock_store
        mock_store.search_jd.side_effect = Exception("搜索失败")
        retriever = Retriever()
        demand = retriever.get_skill_market_demand(["Python"])
        assert demand["Python"] == 0
