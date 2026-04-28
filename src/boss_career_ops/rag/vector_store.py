import json
from pathlib import Path

import chromadb

from boss_career_ops.display.logger import get_logger
from boss_career_ops.rag.chunker import chunk_interview, chunk_jd, chunk_resume
from boss_career_ops.rag.embedder import Embedder
from boss_career_ops.rag.schemas import InterviewExperience, JDDocument, ResumeTemplate

logger = get_logger(__name__)


class _LangchainEmbeddingAdapter:
    def __init__(self, lc_embeddings):
        self._lc = lc_embeddings

    def __call__(self, input):
        return self._lc.embed_documents(input)


class VectorStore:
    def __init__(self, persist_dir: str = "~/.bco/chroma_db"):
        self._persist_dir = Path(persist_dir).expanduser()
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(self._persist_dir))

        embedder = Embedder()
        ef = embedder.get_embedding_function()
        self._ef = _LangchainEmbeddingAdapter(ef) if ef else None

        self._jd_collection = self._get_or_create_collection("jd_knowledge")
        self._resume_collection = self._get_or_create_collection("resume_templates")
        self._interview_collection = self._get_or_create_collection("interview_experience")

    def _get_or_create_collection(self, name: str):
        kwargs = {"name": name}
        if self._ef:
            kwargs["embedding_function"] = self._ef
        return self._client.get_or_create_collection(**kwargs)

    def add_jd(self, doc: JDDocument) -> None:
        self.add_jd_batch([doc])

    def add_jd_batch(self, docs: list[JDDocument]) -> None:
        all_ids = []
        all_docs = []
        all_metadatas = []
        for doc in docs:
            chunks = chunk_jd(doc)
            for i, chunk in enumerate(chunks):
                chunk_id = f"{doc.doc_id}_{i}"
                all_ids.append(chunk_id)
                all_docs.append(chunk["content"])
                all_metadatas.append(chunk["metadata"])
        if all_ids:
            self._jd_collection.add(ids=all_ids, documents=all_docs, metadatas=all_metadatas)
        logger.info("JD 批量入库: %d 条", len(docs))

    def add_resume_template(self, doc: ResumeTemplate) -> None:
        chunks = chunk_resume(doc)
        ids = []
        documents = []
        metadatas = []
        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc.doc_id}_{i}"
            ids.append(chunk_id)
            documents.append(chunk["content"])
            metadatas.append(chunk["metadata"])
        if ids:
            self._resume_collection.add(ids=ids, documents=documents, metadatas=metadatas)
        logger.info("简历模板入库: %s - %s", doc.doc_id, doc.job_name)

    def add_interview_experience(self, doc: InterviewExperience) -> None:
        chunks = chunk_interview(doc)
        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc.doc_id}_{i}"
            self._interview_collection.add(
                ids=[chunk_id],
                documents=[chunk["content"]],
                metadatas=[chunk["metadata"]],
            )
        logger.info("面试经验入库: %s - %s", doc.doc_id, doc.company_name)

    def search_jd(self, query: str, n: int = 10, filters: dict | None = None) -> list[dict]:
        kwargs = {
            "query_text": query,
            "n_results": n,
        }
        if filters:
            kwargs["where"] = filters
        try:
            results = self._jd_collection.query(
                query_texts=kwargs["query_text"],
                n_results=kwargs["n_results"],
                where=kwargs.get("where"),
                include=["documents", "metadatas", "distances"],
            )
        except Exception:
            if filters:
                logger.warning("搜索条件降级：过滤条件 '%s' 不被支持，已忽略", filters)
            results = self._jd_collection.query(
                query_texts=kwargs["query_text"],
                n_results=kwargs["n_results"],
                include=["documents", "metadatas", "distances"],
            )
        return self._format_results(results)

    def search_resume(self, query: str, n: int = 5, filters: dict | None = None) -> list[dict]:
        kwargs = {
            "query_text": query,
            "n_results": n,
        }
        if filters:
            kwargs["where"] = filters
        try:
            results = self._resume_collection.query(
                query_texts=kwargs["query_text"],
                n_results=kwargs["n_results"],
                where=kwargs.get("where"),
                include=["documents", "metadatas", "distances"],
            )
        except Exception:
            if filters:
                logger.warning("搜索条件降级：过滤条件 '%s' 不被支持，已忽略", filters)
            results = self._resume_collection.query(
                query_texts=kwargs["query_text"],
                n_results=kwargs["n_results"],
                include=["documents", "metadatas", "distances"],
            )
        return self._format_results(results)

    def search_interview(self, query: str, n: int = 5) -> list[dict]:
        results = self._interview_collection.query(
            query_texts=query,
            n_results=n,
            include=["documents", "metadatas", "distances"],
        )
        return self._format_results(results)

    def delete_jd(self, job_id: str) -> None:
        self._jd_collection.delete(ids=[job_id])
        logger.info("JD 删除: %s", job_id)

    def _format_results(self, results: dict) -> list[dict]:
        formatted = []
        if not results or not results.get("ids") or not results["ids"][0]:
            return formatted
        for i in range(len(results["ids"][0])):
            item = {
                "id": results["ids"][0][i],
                "content": results["documents"][0][i] if results.get("documents") else "",
                "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                "distance": results["distances"][0][i] if results.get("distances") else None,
            }
            formatted.append(item)
        return formatted
