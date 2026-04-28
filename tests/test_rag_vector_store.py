from unittest.mock import patch, MagicMock

from boss_career_ops.rag.schemas import JDDocument, InterviewExperience, ResumeTemplate
from boss_career_ops.rag.vector_store import VectorStore


class TestVectorStoreInit:
    @patch("boss_career_ops.rag.vector_store.chromadb.PersistentClient")
    @patch("boss_career_ops.rag.vector_store.Embedder")
    def test_initialization_creates_collections(self, mock_embedder_cls, mock_chroma_cls):
        mock_client = MagicMock()
        mock_chroma_cls.return_value = mock_client
        mock_embedder = MagicMock()
        mock_embedder.get_embedding_function.return_value = None
        mock_embedder_cls.return_value = mock_embedder
        with patch("boss_career_ops.rag.vector_store.Path") as mock_path_cls:
            mock_path = MagicMock()
            mock_path_cls.return_value = mock_path
            store = VectorStore(persist_dir="/tmp/test_chroma")
            mock_client.get_or_create_collection.assert_any_call(name="jd_knowledge")
            mock_client.get_or_create_collection.assert_any_call(name="resume_templates")
            mock_client.get_or_create_collection.assert_any_call(name="interview_experience")


class TestAddJd:
    @patch("boss_career_ops.rag.vector_store.chromadb.PersistentClient")
    @patch("boss_career_ops.rag.vector_store.Embedder")
    def test_add_jd_delegates_to_add_jd_batch(self, mock_embedder_cls, mock_chroma_cls):
        mock_client = MagicMock()
        mock_chroma_cls.return_value = mock_client
        mock_embedder = MagicMock()
        mock_embedder.get_embedding_function.return_value = None
        mock_embedder_cls.return_value = mock_embedder
        mock_jd_col = MagicMock()
        mock_resume_col = MagicMock()
        mock_interview_col = MagicMock()
        mock_client.get_or_create_collection.side_effect = [mock_jd_col, mock_resume_col, mock_interview_col]
        with patch("boss_career_ops.rag.vector_store.Path"):
            store = VectorStore(persist_dir="/tmp/test_chroma")
        doc = JDDocument(
            doc_id="jd001",
            content="Python开发",
            job_name="Python开发",
            company_name="测试公司",
            city="深圳",
            salary_min=20000,
            salary_max=40000,
            skills=["Python"],
            industry="互联网",
            score=3.5,
            grade="C",
        )
        with patch.object(store, "add_jd_batch") as mock_batch:
            store.add_jd(doc)
            mock_batch.assert_called_once_with([doc])


class TestSearchJd:
    @patch("boss_career_ops.rag.vector_store.chromadb.PersistentClient")
    @patch("boss_career_ops.rag.vector_store.Embedder")
    def test_search_jd_returns_formatted_results(self, mock_embedder_cls, mock_chroma_cls):
        mock_client = MagicMock()
        mock_chroma_cls.return_value = mock_client
        mock_embedder = MagicMock()
        mock_embedder.get_embedding_function.return_value = None
        mock_embedder_cls.return_value = mock_embedder
        mock_jd_col = MagicMock()
        mock_resume_col = MagicMock()
        mock_interview_col = MagicMock()
        mock_client.get_or_create_collection.side_effect = [mock_jd_col, mock_resume_col, mock_interview_col]
        mock_jd_col.query.return_value = {
            "ids": [["jd001"]],
            "documents": [["Python开发"]],
            "metadatas": [[{"job_name": "Python开发", "company_name": "测试公司"}]],
            "distances": [[0.1]],
        }
        with patch("boss_career_ops.rag.vector_store.Path"):
            store = VectorStore(persist_dir="/tmp/test_chroma")
        results = store.search_jd("Python", n=5)
        assert len(results) == 1
        assert results[0]["id"] == "jd001"
        assert results[0]["content"] == "Python开发"
        assert results[0]["distance"] == 0.1


class TestDeleteJd:
    @patch("boss_career_ops.rag.vector_store.chromadb.PersistentClient")
    @patch("boss_career_ops.rag.vector_store.Embedder")
    def test_delete_jd_calls_collection_delete(self, mock_embedder_cls, mock_chroma_cls):
        mock_client = MagicMock()
        mock_chroma_cls.return_value = mock_client
        mock_embedder = MagicMock()
        mock_embedder.get_embedding_function.return_value = None
        mock_embedder_cls.return_value = mock_embedder
        mock_jd_col = MagicMock()
        mock_resume_col = MagicMock()
        mock_interview_col = MagicMock()
        mock_client.get_or_create_collection.side_effect = [mock_jd_col, mock_resume_col, mock_interview_col]
        with patch("boss_career_ops.rag.vector_store.Path"):
            store = VectorStore(persist_dir="/tmp/test_chroma")
        store.delete_jd("jd001")
        mock_jd_col.delete.assert_called_once_with(ids=["jd001"])


class TestAddJdChunkIdUniqueness:
    @patch("boss_career_ops.rag.vector_store.chunk_jd")
    @patch("boss_career_ops.rag.vector_store.chromadb.PersistentClient")
    @patch("boss_career_ops.rag.vector_store.Embedder")
    def test_add_jd_generates_unique_ids_for_multiple_chunks(self, mock_embedder_cls, mock_chroma_cls, mock_chunk_jd):
        mock_client = MagicMock()
        mock_chroma_cls.return_value = mock_client
        mock_embedder = MagicMock()
        mock_embedder.get_embedding_function.return_value = None
        mock_embedder_cls.return_value = mock_embedder
        mock_jd_col = MagicMock()
        mock_resume_col = MagicMock()
        mock_interview_col = MagicMock()
        mock_client.get_or_create_collection.side_effect = [mock_jd_col, mock_resume_col, mock_interview_col]
        doc = JDDocument(
            doc_id="jd002",
            content="内容",
            job_name="测试",
            company_name="公司",
            city="北京",
            salary_min=10000,
            salary_max=20000,
            skills=["Python"],
            industry="互联网",
        )
        mock_chunk_jd.return_value = [
            {"content": "chunk0", "metadata": {"doc_id": "jd002"}},
            {"content": "chunk1", "metadata": {"doc_id": "jd002"}},
            {"content": "chunk2", "metadata": {"doc_id": "jd002"}},
        ]
        with patch("boss_career_ops.rag.vector_store.Path"):
            store = VectorStore(persist_dir="/tmp/test_chroma")
        store.add_jd(doc)
        mock_jd_col.add.assert_called_once()
        call_kwargs = mock_jd_col.add.call_args[1]
        assert call_kwargs["ids"] == ["jd002_0", "jd002_1", "jd002_2"]


class TestAddJdBatchChunkIdUniqueness:
    @patch("boss_career_ops.rag.vector_store.chunk_jd")
    @patch("boss_career_ops.rag.vector_store.chromadb.PersistentClient")
    @patch("boss_career_ops.rag.vector_store.Embedder")
    def test_add_jd_batch_generates_unique_ids_for_multiple_chunks(self, mock_embedder_cls, mock_chroma_cls, mock_chunk_jd):
        mock_client = MagicMock()
        mock_chroma_cls.return_value = mock_client
        mock_embedder = MagicMock()
        mock_embedder.get_embedding_function.return_value = None
        mock_embedder_cls.return_value = mock_embedder
        mock_jd_col = MagicMock()
        mock_resume_col = MagicMock()
        mock_interview_col = MagicMock()
        mock_client.get_or_create_collection.side_effect = [mock_jd_col, mock_resume_col, mock_interview_col]
        doc1 = JDDocument(
            doc_id="jd010",
            content="内容1",
            job_name="测试1",
            company_name="公司1",
            city="北京",
            salary_min=10000,
            salary_max=20000,
            skills=["Python"],
            industry="互联网",
        )
        doc2 = JDDocument(
            doc_id="jd011",
            content="内容2",
            job_name="测试2",
            company_name="公司2",
            city="上海",
            salary_min=15000,
            salary_max=25000,
            skills=["Go"],
            industry="金融",
        )
        mock_chunk_jd.side_effect = [
            [
                {"content": "chunk0", "metadata": {"doc_id": "jd010"}},
                {"content": "chunk1", "metadata": {"doc_id": "jd010"}},
            ],
            [
                {"content": "chunk0", "metadata": {"doc_id": "jd011"}},
            ],
        ]
        with patch("boss_career_ops.rag.vector_store.Path"):
            store = VectorStore(persist_dir="/tmp/test_chroma")
        store.add_jd_batch([doc1, doc2])
        mock_jd_col.add.assert_called_once()
        call_kwargs = mock_jd_col.add.call_args[1]
        assert call_kwargs["ids"] == ["jd010_0", "jd010_1", "jd011_0"]


class TestAddInterviewChunkIdUniqueness:
    @patch("boss_career_ops.rag.vector_store.chunk_interview")
    @patch("boss_career_ops.rag.vector_store.chromadb.PersistentClient")
    @patch("boss_career_ops.rag.vector_store.Embedder")
    def test_add_interview_generates_unique_ids_for_multiple_chunks(self, mock_embedder_cls, mock_chroma_cls, mock_chunk_interview):
        mock_client = MagicMock()
        mock_chroma_cls.return_value = mock_client
        mock_embedder = MagicMock()
        mock_embedder.get_embedding_function.return_value = None
        mock_embedder_cls.return_value = mock_embedder
        mock_jd_col = MagicMock()
        mock_resume_col = MagicMock()
        mock_interview_col = MagicMock()
        mock_client.get_or_create_collection.side_effect = [mock_jd_col, mock_resume_col, mock_interview_col]
        doc = InterviewExperience(
            doc_id="intv001",
            content="面试经验",
            company_name="大厂",
            job_name="架构师",
            questions=["系统设计"],
            result="通过",
        )
        mock_chunk_interview.return_value = [
            {"content": "chunk0", "metadata": {"doc_id": "intv001"}},
            {"content": "chunk1", "metadata": {"doc_id": "intv001"}},
        ]
        with patch("boss_career_ops.rag.vector_store.Path"):
            store = VectorStore(persist_dir="/tmp/test_chroma")
        store.add_interview_experience(doc)
        assert mock_interview_col.add.call_count == 2
        ids_used = []
        for call in mock_interview_col.add.call_args_list:
            ids_used.append(call[1]["ids"][0])
        assert ids_used == ["intv001_0", "intv001_1"]


class TestAddResumeChunkIdUniqueness:
    @patch("boss_career_ops.rag.vector_store.chromadb.PersistentClient")
    @patch("boss_career_ops.rag.vector_store.Embedder")
    def test_add_resume_generates_unique_ids_for_multiple_chunks(self, mock_embedder_cls, mock_chroma_cls):
        mock_client = MagicMock()
        mock_chroma_cls.return_value = mock_client
        mock_embedder = MagicMock()
        mock_embedder.get_embedding_function.return_value = None
        mock_embedder_cls.return_value = mock_embedder
        mock_jd_col = MagicMock()
        mock_resume_col = MagicMock()
        mock_interview_col = MagicMock()
        mock_client.get_or_create_collection.side_effect = [mock_jd_col, mock_resume_col, mock_interview_col]
        doc = ResumeTemplate(
            doc_id="resume001",
            content="## 工作经历\n- 公司A\n## 教育背景\n- 大学B",
            job_name="Python开发",
            company_name="测试公司",
            result="通过",
            keywords=["Python"],
        )
        with patch("boss_career_ops.rag.vector_store.Path"):
            store = VectorStore(persist_dir="/tmp/test_chroma")
        store.add_resume_template(doc)
        mock_resume_col.add.assert_called_once()
        call_kwargs = mock_resume_col.add.call_args[1]
        assert call_kwargs["ids"] == ["resume001_0", "resume001_1"]
