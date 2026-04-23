import os

from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)


class Embedder:
    def __init__(self, provider: str = ""):
        if provider:
            self._provider = provider
        else:
            self._provider = os.environ.get("BCO_EMBEDDING_PROVIDER", "local")
        self._embedding_function = None

    def get_embedding_function(self):
        if self._embedding_function is not None:
            return self._embedding_function

        if self._provider == "openai":
            try:
                from langchain_openai import OpenAIEmbeddings

                embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
                self._embedding_function = embeddings
                logger.info("使用 OpenAI embedding 模型: text-embedding-3-small")
            except ImportError:
                logger.warning("langchain_openai 未安装，回退到本地 embedding")
                self._embedding_function = None
        else:
            self._embedding_function = None
            logger.info("使用 ChromaDB 默认 embedding 模型: all-MiniLM-L6-v2")

        return self._embedding_function
