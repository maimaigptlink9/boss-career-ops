import json

from langchain_core.messages import SystemMessage, HumanMessage

from boss_career_ops.agent.llm import get_llm, is_llm_available
from boss_career_ops.agent.prompts import RESUME_SYSTEM, RESUME_USER
from boss_career_ops.agent.tools import get_job_detail, get_cv, write_resume
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)


async def run(state: dict) -> dict:
    current_job_id = state.get("current_job_id", "")
    job_ids = state.get("job_ids", [])
    job_details = state.get("job_details", {})
    resume_versions = dict(state.get("resume_versions", {}))
    errors = list(state.get("errors", []))

    target_job_id = current_job_id or (job_ids[0] if job_ids else "")
    if not target_job_id:
        return {"resume_versions": {}, "errors": ["无目标职位"]}

    job = job_details.get(target_job_id) or get_job_detail(target_job_id)
    if not job:
        return {"resume_versions": {}, "errors": [f"职位 {target_job_id} 详情获取失败"]}

    cv = get_cv()
    if not cv:
        return {"resume_versions": {}, "errors": ["简历内容为空"]}

    jd_text = json.dumps(job, ensure_ascii=False)
    rag_context = state.get("rag_context", "")

    # 尝试 RAG 检索相似简历模板
    if not rag_context:
        try:
            from boss_career_ops.rag.retriever import Retriever
            retriever = Retriever()
            similar = retriever.find_matching_resumes(jd_text, n=3)
            if similar:
                rag_context = "\n".join(
                    r.get("content", "") for r in similar if r.get("content")
                )
        except Exception as e:
            logger.warning("RAG 检索失败,跳过: %s", e)

    llm = get_llm() if is_llm_available() else None

    if llm is not None:
        try:
            system_msg = SystemMessage(content=RESUME_SYSTEM)
            user_msg = HumanMessage(
                content=RESUME_USER.format(cv=cv, jd=jd_text, rag_context=rag_context)
            )
            response = await llm.ainvoke([system_msg, user_msg])
            markdown_content = response.content

            write_resume(target_job_id, markdown_content)
            resume_versions[target_job_id] = markdown_content
            return {
                "resume_versions": resume_versions,
                "messages": [{"role": "system", "content": f"简历润色完成: {target_job_id}"}],
            }

        except Exception as e:
            logger.warning("LLM 简历润色失败,降级到模板生成: %s", e)

    # 模板生成兜底
    try:
        from boss_career_ops.resume.generator import ResumeGenerator
        generator = ResumeGenerator()
        markdown_content = generator.generate(job)
        if markdown_content:
            write_resume(target_job_id, markdown_content)
            resume_versions[target_job_id] = markdown_content
            return {
                "resume_versions": resume_versions,
                "messages": [{"role": "system", "content": f"简历模板生成完成: {target_job_id}"}],
            }
    except Exception as e:
        logger.warning("模板简历生成失败: %s", e)
        errors.append(f"简历生成失败: {e}")

    return {"resume_versions": resume_versions, "errors": errors}
