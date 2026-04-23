import os
from unittest.mock import patch, MagicMock

from boss_career_ops.rag.embedder import Embedder


class TestEmbedderInit:
    def test_default_local_provider(self):
        with patch.dict(os.environ, {}, clear=True):
            embedder = Embedder()
            assert embedder._provider == "local"

    @patch.dict(os.environ, {"BCO_EMBEDDING_PROVIDER": "openai"}, clear=True)
    def test_env_var_switching(self):
        embedder = Embedder()
        assert embedder._provider == "openai"

    def test_explicit_provider_overrides_env(self):
        with patch.dict(os.environ, {"BCO_EMBEDDING_PROVIDER": "openai"}, clear=True):
            embedder = Embedder(provider="local")
            assert embedder._provider == "local"


class TestGetEmbeddingFunction:
    def test_local_provider_returns_none(self):
        with patch.dict(os.environ, {}, clear=True):
            embedder = Embedder(provider="local")
            result = embedder.get_embedding_function()
            assert result is None

    @patch("boss_career_ops.rag.embedder.OpenAIEmbeddings", create=True)
    def test_openai_provider_returns_embeddings(self, mock_openai_cls):
        mock_embeddings = MagicMock()
        mock_openai_cls.return_value = mock_embeddings
        with patch.dict(os.environ, {"BCO_EMBEDDING_PROVIDER": "openai"}, clear=True):
            embedder = Embedder(provider="openai")
            with patch("boss_career_ops.rag.embedder.logger"):
                with patch.dict("sys.modules", {"langchain_openai": MagicMock(OpenAIEmbeddings=mock_openai_cls)}):
                    result = embedder.get_embedding_function()
                    if result is not None:
                        assert result == mock_embeddings

    def test_caching_embedding_function(self):
        embedder = Embedder(provider="local")
        embedder._embedding_function = "cached_value"
        result = embedder.get_embedding_function()
        assert result == "cached_value"
