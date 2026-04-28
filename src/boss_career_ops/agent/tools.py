import json

from boss_career_ops.config.settings import Settings
from boss_career_ops.display.logger import get_logger
from boss_career_ops.errors import Result
from boss_career_ops.pipeline.manager import PipelineManager
from boss_career_ops.platform.registry import get_active_adapter

logger = get_logger(__name__)

_pm = None


def _get_pm():
    global _pm
    if _pm is None:
        _pm = PipelineManager()
    return _pm


def get_job_detail(job_id: str) -> dict | None:
    """读取职位详情，含 Pipeline data 中的所有评估结果"""
    with _get_pm() as pm:
        job = pm.get_job(job_id)
        if job is None:
            return None
        ai_results = pm.get_ai_results(job_id)
        if ai_results:
            job["ai_results"] = ai_results
        return job


def get_chat_messages(security_id: str) -> list[dict]:
    """读取与某联系人的聊天记录"""
    try:
        adapter = get_active_adapter()
        messages = adapter.get_chat_messages(security_id)
        return [
            {"sender_name": m.sender_name, "content": m.content, "time": m.time}
            for m in messages
        ]
    except Exception as e:
        logger.warning("获取聊天记录失败: %s", e)
        return []


def get_profile() -> dict:
    """读取个人档案（profile.yml）"""
    settings = Settings()
    profile = settings.profile
    return {
        "name": profile.name,
        "title": profile.title,
        "experience_years": profile.experience_years,
        "skills": profile.skills,
        "expected_salary": {
            "min": profile.expected_salary.min,
            "max": profile.expected_salary.max,
        },
        "preferred_cities": profile.preferred_cities,
        "education": profile.education,
        "career_goals": profile.career_goals,
    }


def get_cv() -> str:
    """读取简历内容（cv.md）"""
    settings = Settings()
    return settings.cv_content or ""


def list_pipeline_jobs(stage: str | None = None) -> list[dict]:
    """列出 Pipeline 中的职位，可按阶段筛选"""
    with _get_pm() as pm:
        return pm.list_jobs(stage=stage)


def get_job_with_ai_result(job_id: str) -> dict | None:
    """读取职位详情 + 关联的 AI 结果"""
    with _get_pm() as pm:
        job = pm.get_job(job_id)
        if job is None:
            return None
        ai_results = pm.get_ai_results(job_id)
        result_map = {}
        for r in ai_results:
            result_map[r["task_type"]] = (
                json.loads(r["result"]) if r["result"] else None
            )
        job["ai_results"] = result_map
        return job


def write_evaluation(
    job_id: str,
    score: float,
    grade: str,
    analysis: str,
    scores_detail: dict | None = None,
) -> None:
    """写入评估结果到 Pipeline + ai_results 表"""
    result_data = {
        "score": score,
        "grade": grade,
        "analysis": analysis,
    }
    if scores_detail:
        result_data["scores_detail"] = scores_detail
    with _get_pm() as pm:
        pm.save_ai_result(
            job_id, "evaluate", json.dumps(result_data, ensure_ascii=False)
        )
        pm.update_score(job_id, score, grade)


def write_resume(job_id: str, markdown_content: str) -> None:
    """写入润色后的简历 Markdown"""
    with _get_pm() as pm:
        pm.save_ai_result(
            job_id,
            "resume",
            json.dumps({"content": markdown_content}, ensure_ascii=False),
        )


def write_chat_summary(security_id: str, summary_data: dict) -> None:
    """写入聊天摘要"""
    with _get_pm() as pm:
        pm.save_ai_result(
            security_id,
            "chat_summary",
            json.dumps(summary_data, ensure_ascii=False),
        )


def write_interview_prep(job_id: str, prep_data: dict) -> None:
    """写入面试准备方案"""
    with _get_pm() as pm:
        pm.save_ai_result(
            job_id,
            "interview_prep",
            json.dumps(prep_data, ensure_ascii=False),
        )


def evaluate_job(job_id: str) -> dict | None:
    """评估职位匹配度并持久化结果到 ai_results 表"""
    job = get_job_detail(job_id)
    if not job:
        return None
    from boss_career_ops.evaluator.engine import EvaluationEngine

    engine = EvaluationEngine()
    result = engine.evaluate(job)
    write_evaluation(
        job_id=job_id,
        score=result["total_score"],
        grade=result["grade"],
        analysis=result.get("recommendation", ""),
        scores_detail=result.get("scores"),
    )
    return result


def generate_resume(job_id: str) -> str | None:
    """根据职位信息生成定制简历并持久化到 ai_results 表"""
    job = get_job_detail(job_id)
    if not job:
        return None
    from boss_career_ops.resume.generator import ResumeGenerator

    generator = ResumeGenerator()
    resume_md = generator.generate(job)
    if resume_md:
        write_resume(job_id=job_id, markdown_content=resume_md)
    return resume_md


def search_jobs(keyword: str, city: str = "") -> list[dict]:
    try:
        adapter = get_active_adapter()
        params = adapter.build_search_params(keyword, city)
        jobs = adapter.search(params)
        return [
            {
                "job_id": j.job_id,
                "job_name": j.job_name,
                "company_name": j.company_name,
                "city": j.city,
                "salary": j.salary_desc,
                "skills": j.skills,
                "security_id": j.security_id,
            }
            for j in jobs
        ]
    except Exception as e:
        logger.warning("搜索职位失败: %s", e)
        return []


def greet_recruiter(security_id: str, job_id: str) -> Result:
    try:
        adapter = get_active_adapter()
        result = adapter.greet(security_id, job_id)
        if result.ok:
            return Result.success(data={"message": result.message})
        return Result.failure(error=result.message, code="GREET_FAILED")
    except Exception as e:
        return Result.failure(error=str(e), code="PLATFORM_ERROR")


def apply_job(security_id: str, job_id: str) -> Result:
    try:
        adapter = get_active_adapter()
        result = adapter.apply(security_id, job_id)
        if result.ok:
            return Result.success(data={"message": result.message})
        return Result.failure(error=result.message, code="APPLY_FAILED")
    except Exception as e:
        return Result.failure(error=str(e), code="PLATFORM_ERROR")


def analyze_skill_gap() -> dict:
    profile = get_profile()
    pipeline_jobs = list_pipeline_jobs()
    return {
        "skills": profile.get("skills", []),
        "jd_count": len(pipeline_jobs),
        "analysis_available": bool(profile.get("skills") and pipeline_jobs),
    }


def prepare_interview(job_id: str) -> Result:
    job = get_job_detail(job_id)
    if not job:
        return Result.failure(error="职位不存在", code="NOT_FOUND")
    return Result.success(data={
        "job_id": job_id,
        "job_name": job.get("job_name", ""),
        "company_name": job.get("company_name", ""),
        "analysis_available": True,
    })
