import json

from langchain_core.messages import SystemMessage, HumanMessage

from boss_career_ops.agent.llm import get_llm, is_llm_available
from boss_career_ops.agent.prompts import GAP_ANALYSIS_SYSTEM, GAP_ANALYSIS_USER, sanitize_input
from boss_career_ops.agent.tools import get_profile, list_pipeline_jobs
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)


def _simple_gap_analysis(skills: list[str], jds: list[str]) -> dict:
    missing = []
    skills_lower = {s.lower() for s in skills}
    for jd in jds:
        jd_lower = jd.lower()
        for skill in skills:
            if skill.lower() not in jd_lower:
                missing.append({"skill": skill, "priority": "medium", "suggestion": f"提升 {skill} 技能"})
    # 去重
    seen = set()
    unique_missing = []
    for item in missing:
        if item["skill"] not in seen:
            seen.add(item["skill"])
            unique_missing.append(item)
    return {
        "missing_skills": unique_missing[:10],
        "overall_assessment": f"共 {len(unique_missing)} 项技能需要提升",
    }


async def run(state: dict) -> dict:
    errors = list(state.get("errors", []))

    profile = get_profile()
    skills = profile.get("skills", [])

    pipeline_jobs = list_pipeline_jobs()
    jds = []
    for job in pipeline_jobs:
        jd_text = json.dumps(job, ensure_ascii=False)
        jds.append(jd_text)

    if not skills:
        errors.append("个人档案中无技能信息")
        return {"skill_gaps": {}, "next_action": "", "errors": errors}

    if not jds:
        errors.append("Pipeline 中无职位数据")
        return {"skill_gaps": {}, "next_action": "", "errors": errors}

    skills_text = json.dumps(skills, ensure_ascii=False)
    jds_text = "\n---\n".join(jds[:20])

    llm = get_llm() if is_llm_available() else None

    if llm is not None:
        try:
            system_msg = SystemMessage(content=GAP_ANALYSIS_SYSTEM)
            user_msg = HumanMessage(
                content=GAP_ANALYSIS_USER.safe_substitute(
                    skills=sanitize_input(skills_text),
                    jds=sanitize_input(jds_text),
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
            missing_skills = parsed.get("missing_skills", [])
            overall_assessment = parsed.get("overall_assessment", "")

            # 持久化到 ai_results
            try:
                from boss_career_ops.pipeline.manager import PipelineManager
                with PipelineManager() as pm:
                    pm.save_ai_result(
                        "profile",
                        "gap_analysis",
                        json.dumps(parsed, ensure_ascii=False),
                    )
            except Exception as e:
                logger.warning("技能差距分析持久化失败: %s", e)

            return {
                "skill_gaps": parsed,
                "next_action": "",
                "messages": [{"role": "system", "content": f"技能差距分析完成: {overall_assessment}"}],
            }

        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.warning("LLM 技能差距分析解析失败,降级到简单比较: %s", e)
        except Exception as e:
            logger.warning("LLM 技能差距分析异常,降级到简单比较: %s", e)

    # 简单关键词比较兜底
    result = _simple_gap_analysis(skills, jds)
    try:
        from boss_career_ops.pipeline.manager import PipelineManager
        with PipelineManager() as pm:
            pm.save_ai_result(
                "profile",
                "gap_analysis",
                json.dumps(result, ensure_ascii=False),
            )
    except Exception as e:
        logger.warning("技能差距分析持久化失败: %s", e)

    return {
        "skill_gaps": result,
        "next_action": "",
        "messages": [{"role": "system", "content": f"技能差距分析完成(规则): {result.get('overall_assessment', '')}"}],
    }
