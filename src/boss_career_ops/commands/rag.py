from boss_career_ops.display.logger import get_logger
from rich.console import Console

logger = get_logger(__name__)
console = Console()

def run_rag_index(reindex: bool = False):
    """构建/更新 RAG 知识库索引"""
    from boss_career_ops.rag.indexer import Indexer
    indexer = Indexer()
    if reindex:
        count = indexer.reindex_all()
        console.print(f"[green]全量重建索引完成，共索引 {count} 个文档[/green]")
    else:
        count = indexer.index_from_pipeline()
        console.print(f"[green]增量索引完成，共索引 {count} 个文档[/green]")

def run_rag_search(query: str, collection: str = "jd", top_k: int = 10):
    """RAG 语义搜索"""
    import json
    from boss_career_ops.rag.retriever import Retriever
    retriever = Retriever()
    if collection == "jd":
        results = retriever.find_similar_jds(query, n=top_k)
    elif collection == "resume":
        results = retriever.find_matching_resumes(query, n=top_k)
    elif collection == "interview":
        results = retriever.find_interview_tips(query, "", n=top_k)
    else:
        console.print(f"[red]未知的 collection: {collection}[/red]")
        return
    if results:
        console.print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        console.print("[yellow]未找到匹配结果[/yellow]")
