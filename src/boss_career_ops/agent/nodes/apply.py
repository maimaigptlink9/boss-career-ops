import json

from langchain_core.messages import SystemMessage, HumanMessage

from boss_career_ops.agent.llm import get_llm, is_llm_available
from boss_career_ops.agent.prompts import APPLY_SYSTEM, APPLY_USER
from boss_career_ops.agent.tools import (
    get_job_detail,
    get_cv,
    greet_recruiter,
    apply_job,
)
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)


async def run(state: dict) -> dict:
    current_job_id = state.get("current_job_id", "")
    job_ids = state.get("job_ids", [])
    job_details = state.get("job_details", {})
    errors = list(state.get("errors", []))

    target_job_id = current_job_id or (job_ids[0] if job_ids else "")
    if not target_job_id:
        return {"errors": ["无目标职位"]}

    job = job_details.get(target_job_id) or get_job_detail(target_job_id)
    if not job:
        return {"errors": [f"职位 {target_job_id} 详情获取失败"]}

    security_id = job.get("security_id", "")
    if not security_id:
        errors.append(f"职位 {target_job_id} 缺少 security_id")
        return {"errors": errors}

    jd_text = json.dumps(job, ensure_ascii=False)
    cv = get_cv()
    cv_summary = cv[:500] if cv else ""

    greeting_msg = ""

    llm = get_llm() if is_llm_available() else None
    if llm is not None:
        try:
            system_msg = SystemMessage(content=APPLY_SYSTEM)
            user_msg = HumanMessage(
                content=APPLY_USER.format(cv_summary=cv_summary, jd=jd_text)
            )
            response = await llm.ainvoke([system_msg, user_msg])
            greeting_msg = response.content.strip()
        except Exception as e:
            logger.warning("LLM 生成打招呼语失败,使用默认: %s", e)

    # 打招呼
    try:
        greet_result = greet_recruiter(security_id, target_job_id)
        if not greet_result.get("ok"):
            errors.append(f"打招呼失败: {greet_result.get('message', '')}")
    except Exception as e:
        logger.warning("打招呼异常: %s", e)
        errors.append(f"打招呼异常: {e}")

    # 投递
    try:
        apply_result = apply_job(security_id, target_job_id)
        if not apply_result.get("ok"):
            errors.append(f"投递失败: {apply_result.get('message', '')}")
    except Exception as e:
        logger.warning("投递异常: %s", e)
        errors.append(f"投递异常: {e}")

    return {
        "errors": errors,
        "messages": [{"role": "system", "content": f"投递流程完成: {target_job_id}"}],
    }
