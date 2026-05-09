from boss_career_ops.platform.registry import get_active_adapter
from boss_career_ops.config.settings import Settings
from boss_career_ops.pipeline.manager import PipelineManager
from boss_career_ops.display.output import output_json, output_error
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)


def _get_security_id_from_pipeline(job_id: str) -> str:
    try:
        with PipelineManager() as pm:
            job = pm.get_job(job_id)
            if job:
                return job.get("security_id", "")
    except Exception:
        pass
    return ""


def run_interview(job_id: str):
    security_id = _get_security_id_from_pipeline(job_id)
    if not security_id:
        output_error(command="interview", message=f"缺少 security_id（job_id={job_id}），请先搜索该职位使其入库", code="MISSING_SECURITY_ID")
        return
    try:
        adapter = get_active_adapter()
        job = adapter.get_job_detail(security_id)
        if not job:
            output_error(command="interview", message="获取职位详情失败", code="DETAIL_ERROR")
            return
        prep = _generate_interview_prep(job)
        if prep.get("ok") is False:
            output_error(command="interview", message=prep.get("error", "面试准备失败"), code=prep.get("code", "INTERVIEW_ERROR"))
            return
        output_json(
            command="interview",
            data=prep,
            hints={"next_actions": ["bco negotiate <jid>", "bco pipeline"]},
        )
    except Exception as e:
        output_error(command="interview", message=str(e), code="INTERVIEW_ERROR")


def _generate_interview_prep(job) -> dict:
    job_id = getattr(job, 'job_id', "")
    if job_id:
        try:
            with PipelineManager() as pm:
                ai_result = pm.get_ai_result(job_id, "interview_prep")
                if ai_result:
                    import json
                    ai_data = json.loads(ai_result["result"])
                    ai_data["source"] = "agent"
                    ai_data["ok"] = True
                    return ai_data
        except Exception as e:
            logger.warning("读取 Agent 面试准备失败: %s", e)

    jd_skills = getattr(job, 'skills', None) or []
    if isinstance(jd_skills, str):
        jd_skills = [s.strip() for s in jd_skills.split(",") if s.strip()]

    settings = Settings()
    user_skills = settings.profile.skills or []

    jd_lower = {s.lower() for s in jd_skills}
    user_lower = {s.lower() for s in user_skills}

    matched = [s for s in jd_skills if s.lower() in user_lower or any(u in s.lower() or s.lower() in u for u in user_lower)]
    gap = [s for s in jd_skills if s not in matched]

    tips = [
        "提前了解公司产品和技术博客",
        "用 STAR 法则组织行为面试回答",
        "对 JD 中的每项技能准备至少一个项目经历佐证",
        "准备一段 1-2 分钟的自我介绍，突出与岗位匹配的经验",
    ]
    if gap:
        tips.insert(0, f"重点准备差距技能：{', '.join(gap)}")
    if matched:
        tips.append(f"发挥优势技能：{', '.join(matched[:5])}，准备深度项目案例")

    return {
        "ok": True,
        "source": "rule",
        "job_name": getattr(job, 'job_name', ''),
        "company_name": getattr(job, 'company_name', ''),
        "skills_match": {"matched": matched, "gap": gap},
        "tips": tips,
    }
