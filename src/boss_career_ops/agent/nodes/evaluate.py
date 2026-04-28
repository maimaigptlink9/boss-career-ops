import json

from langchain_core.messages import SystemMessage, HumanMessage

from boss_career_ops.agent.llm import get_llm, is_llm_available
from boss_career_ops.agent.prompts import EVALUATE_SYSTEM, EVALUATE_USER, sanitize_input, _get_weight_description
from boss_career_ops.agent.tools import get_job_detail, write_evaluation, get_profile
from boss_career_ops.evaluator.engine import EvaluationEngine
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)


async def run(state: dict) -> dict:
    job_ids = state.get("job_ids", [])
    job_details = state.get("job_details", {})
    evaluation_results = dict(state.get("evaluation_results", {}))
    errors = list(state.get("errors", []))

    if not job_ids:
        return {"evaluation_results": {}, "next_action": "", "errors": ["无待评估职位"]}

    profile = get_profile()
    profile_text = json.dumps(profile, ensure_ascii=False) if profile else ""

    engine = EvaluationEngine()
    llm = get_llm() if is_llm_available() else None

    for job_id in job_ids:
        try:
            job = job_details.get(job_id) or get_job_detail(job_id)
            if not job:
                errors.append(f"职位 {job_id} 详情获取失败")
                continue

            jd_text = json.dumps(job, ensure_ascii=False)
            rag_context = state.get("rag_context", "")

            if llm is not None:
                try:
                    system_msg = SystemMessage(
                        content=EVALUATE_SYSTEM.substitute(
                            weight_description=_get_weight_description()
                        )
                    )
                    user_msg = HumanMessage(
                        content=EVALUATE_USER.safe_substitute(
                            profile=sanitize_input(profile_text),
                            jd=sanitize_input(jd_text),
                            rag_context=rag_context,
                        )
                    )
                    response = await llm.ainvoke([system_msg, user_msg])
                    content = response.content

                    json_str = content
                    if "```json" in content:
                        json_str = content.split("```json")[1].split("```")[0].strip()
                    elif "```" in content:
                        json_str = content.split("```")[1].split("```")[0].strip()

                    parsed = json.loads(json_str)
                    scores_detail = parsed.get("scores", {})
                    total_score = float(parsed.get("total_score", 0))
                    grade = parsed.get("grade", "C")
                    analysis = parsed.get("analysis", "")

                    write_evaluation(
                        job_id=job_id,
                        score=total_score,
                        grade=grade,
                        analysis=analysis,
                        scores_detail=scores_detail,
                    )
                    evaluation_results[job_id] = parsed
                    continue

                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    logger.warning("LLM 评估解析失败,降级到规则引擎: job_id=%s, %s", job_id, e)
                except Exception as e:
                    logger.warning("LLM 评估异常,降级到规则引擎: job_id=%s, %s", job_id, e)

            # 规则引擎兜底
            result = engine.evaluate(job)
            write_evaluation(
                job_id=job_id,
                score=result.get("total_score", 0),
                grade=result.get("grade", "C"),
                analysis=result.get("recommendation", ""),
                scores_detail=result.get("scores", {}),
            )
            evaluation_results[job_id] = result

        except Exception as e:
            logger.warning("评估职位 %s 失败: %s", job_id, e)
            errors.append(f"评估 {job_id} 失败: {e}")

    return {
        "evaluation_results": evaluation_results,
        "next_action": "",
        "errors": errors,
        "messages": [{"role": "system", "content": f"评估完成: {len(evaluation_results)} 个职位"}],
    }
