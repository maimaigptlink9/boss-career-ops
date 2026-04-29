import json
import random
import time

from boss_career_ops.config.settings import RESUMES_DIR, Settings
from boss_career_ops.config.thresholds import Thresholds
from boss_career_ops.display.logger import get_logger
from boss_career_ops.errors import Result
from boss_career_ops.pipeline.manager import PipelineManager
from boss_career_ops.pipeline.stages import STAGE_ORDER, Stage
from boss_career_ops.platform.registry import get_active_adapter

logger = get_logger(__name__)

EVAL_LIMIT = 50

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
        "remote_ok": profile.remote_ok,
        "education": profile.education,
        "career_goals": profile.career_goals,
        "avoid": profile.avoid,
    }


def get_cv() -> str:
    """读取简历内容（cv.md）"""
    settings = Settings()
    return settings.cv_content or ""


def list_pipeline_jobs(stage: str | None = None, status: str | None = None) -> list[dict]:
    """列出 Pipeline 中的职位，可按阶段和状态筛选"""
    with _get_pm() as pm:
        return pm.list_jobs(stage=stage, status=status)


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


def dismiss_pipeline_job(job_id: str) -> bool:
    with _get_pm() as pm:
        return pm.dismiss_job(job_id)


def restore_pipeline_job(job_id: str) -> bool:
    with _get_pm() as pm:
        return pm.restore_job(job_id)


def batch_dismiss_pipeline_jobs(job_ids: list[str]) -> int:
    with _get_pm() as pm:
        return pm.batch_dismiss(job_ids)


def get_unevaluated_jobs(limit: int = 100) -> list[dict]:
    with _get_pm() as pm:
        return pm.get_unevaluated(limit=limit)


def write_evaluation(
    job_id: str,
    score: float,
    grade: str,
    analysis: str,
    scores_detail: dict | None = None,
) -> None:
    """写入评估结果到 Pipeline + ai_results 表，并推进阶段到评估"""
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
        pm.update_stage(job_id, Stage.EVALUATED)


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
    """评估职位匹配度并持久化结果到 ai_results 表，推进阶段到评估，合并 Agent 结果"""
    job = get_job_detail(job_id)
    if not job:
        return None
    from boss_career_ops.evaluator.engine import EvaluationEngine
    from boss_career_ops.evaluator.report import generate_report

    engine = EvaluationEngine()
    result = engine.evaluate(job)

    if job_id:
        try:
            with _get_pm() as pm:
                ai_result = pm.get_ai_result(job_id, "evaluate")
                if ai_result:
                    ai_data = json.loads(ai_result["result"])
                    result["agent_score"] = ai_data.get("score")
                    result["agent_grade"] = ai_data.get("grade")
                    result["agent_analysis"] = ai_data.get("analysis")
                    result["agent_scores_detail"] = ai_data.get("scores_detail")
                    if ai_data.get("score") is not None and ai_data.get("grade"):
                        result["total_score"] = ai_data["score"]
                        result["grade"] = ai_data["grade"]
                        result["source"] = "agent"
        except Exception as e:
            logger.warning("读取 Agent 评估结果失败: %s", e)

    report = generate_report(result)
    write_evaluation(
        job_id=job_id,
        score=result["total_score"],
        grade=result["grade"],
        analysis=result.get("recommendation", ""),
        scores_detail=result.get("scores"),
    )
    try:
        with _get_pm() as pm:
            pm.update_job_data(job_id, {"evaluate_report": report})
    except Exception as e:
        logger.warning("评估报告写入 Pipeline 失败: %s", e)
    return result


def generate_resume(job_id: str, inject_keywords: bool = True) -> str | None:
    """根据职位信息生成定制简历并持久化到 ai_results 表

    优先使用 Agent 润色结果，可选注入 ATS 关键词
    """
    job = get_job_detail(job_id)
    if not job:
        return None
    from boss_career_ops.resume.generator import ResumeGenerator

    generator = ResumeGenerator()
    resume_md = None

    try:
        with _get_pm() as pm:
            ai_result = pm.get_ai_result(job_id, "resume")
            if ai_result:
                ai_data = json.loads(ai_result["result"])
                resume_md = ai_data.get("content", "")
    except Exception as e:
        logger.warning("读取 Agent 简历润色结果失败: %s", e)

    if not resume_md:
        resume_md = generator.generate(job)

    if resume_md and inject_keywords:
        from boss_career_ops.resume.keywords import KeywordInjector

        injector = KeywordInjector()
        jd_text = generator._extract_jd_text(job)
        keywords = injector.extract_from_jd(jd_text)
        resume_md = injector.inject(resume_md, keywords)

    if resume_md:
        write_resume(job_id=job_id, markdown_content=resume_md)
        try:
            with _get_pm() as pm:
                pm.update_job_data(job_id, {"resume_generated": True, "resume_format": "md"})
        except Exception as e:
            logger.warning("简历生成 Pipeline 写入失败: %s", e)
    return resume_md


def search_jobs(
    keyword: str,
    city: str = "",
    pages: int = 1,
    welfare: str = "",
    evaluate: bool = True,
) -> list[dict]:
    """搜索职位，支持多页搜索、福利筛选、同步评估和批量入库

    与 CLI search 命令对齐：搜索后自动评估前 EVAL_LIMIT 条并写入 Pipeline
    """
    try:
        thresholds = Thresholds()
        adapter = get_active_adapter()
        params = adapter.build_search_params(keyword, city)
        all_jobs = []
        max_pages = min(pages, thresholds.rate_limit.search_max_pages)

        for p in range(1, max_pages + 1):
            params["page"] = p
            try:
                jobs = adapter.search(params)
            except Exception as e:
                logger.error("搜索第 %d 页失败: %s", p, e)
                break
            if not jobs:
                break
            if welfare:
                jobs = adapter.filter_by_welfare(jobs, welfare)
            all_jobs.extend(jobs)
            if p < max_pages:
                mean = (thresholds.rate_limit.search_page_delay_min + thresholds.rate_limit.search_page_delay_max) / 2
                std = (thresholds.rate_limit.search_page_delay_max - thresholds.rate_limit.search_page_delay_min) / 4
                delay = max(thresholds.rate_limit.search_page_delay_min, random.gauss(mean, std))
                time.sleep(delay)

        if not all_jobs:
            return []

        results = [
            {
                "job_id": j.job_id,
                "job_name": j.job_name,
                "company_name": j.company_name,
                "city": j.city_name,
                "salary": j.salary_desc,
                "skills": j.skills,
                "security_id": j.security_id,
            }
            for j in all_jobs
        ]

        if evaluate:
            from boss_career_ops.evaluator.engine import EvaluationEngine
            engine = EvaluationEngine()
            eval_jobs = all_jobs[:EVAL_LIMIT]
            for job in eval_jobs:
                try:
                    evaluation = engine.evaluate(job)
                    job_data = {"evaluation": evaluation}
                    try:
                        with _get_pm() as pm:
                            pm.upsert_job(
                                job_id=job.job_id,
                                security_id=job.security_id,
                            )
                            pm.update_score(job.job_id, evaluation["total_score"], evaluation["grade"])
                            pm.update_job_data(job.job_id, job_data)
                    except Exception as e:
                        logger.warning("搜索评估结果写入 Pipeline 失败: %s", e)
                    for r in results:
                        if r["job_id"] == job.job_id:
                            r["grade"] = evaluation["grade"]
                            r["total_score"] = evaluation["total_score"]
                except Exception as e:
                    logger.warning("职位 %s 评估失败: %s", job.job_id, e)

        try:
            with _get_pm() as pm:
                pm.batch_add_jobs(all_jobs)
        except Exception as e:
            logger.warning("搜索结果批量写入 Pipeline 失败: %s", e)

        if not evaluate:
            try:
                with _get_pm() as pm:
                    for r in results:
                        job = pm.get_job(r["job_id"])
                        if job and job.get("grade"):
                            r["grade"] = job["grade"]
                            r["total_score"] = job.get("score")
            except Exception as e:
                logger.warning("查询评分信息失败: %s", e)

        return results
    except Exception as e:
        logger.warning("搜索职位失败: %s", e)
        return []


def greet_recruiter(security_id: str, job_id: str) -> Result:
    """打招呼并推进 Pipeline 阶段到沟通"""
    try:
        adapter = get_active_adapter()
        result = adapter.greet(security_id, job_id)
        if result.ok:
            try:
                with _get_pm() as pm:
                    pm.upsert_job(job_id=job_id, security_id=security_id)
                    pm.update_stage(job_id, Stage.COMMUNICATING)
            except Exception as e:
                logger.warning("打招呼阶段推进写入 Pipeline 失败: %s", e)
            return Result.success(data={"message": result.message})
        return Result.failure(error=result.message, code="GREET_FAILED")
    except Exception as e:
        return Result.failure(error=str(e), code="PLATFORM_ERROR")


def apply_job(security_id: str, job_id: str, resume_job_id: str = "") -> Result:
    """投递简历并推进 Pipeline 阶段到投递

    可选 resume_job_id 参数：投递前自动生成并上传简历
    """
    if resume_job_id:
        upload_result = upload_resume(resume_job_id)
        if not upload_result.get("ok"):
            return Result.failure(
                error=f"简历上传失败: {upload_result.get('message', '')}",
                code=upload_result.get("code", "RESUME_UPLOAD_ERROR"),
            )
    try:
        adapter = get_active_adapter()
        result = adapter.apply(security_id, job_id)
        if result.ok:
            try:
                with _get_pm() as pm:
                    pm.upsert_job(job_id=job_id, security_id=security_id)
                    pm.update_stage(job_id, Stage.APPLIED)
            except Exception as e:
                logger.warning("投递阶段推进写入 Pipeline 失败: %s", e)
            return Result.success(data={"message": result.message})
        return Result.failure(error=result.message, code="APPLY_FAILED")
    except Exception as e:
        return Result.failure(error=str(e), code="PLATFORM_ERROR")


def upload_resume(job_id: str) -> dict:
    """生成定制简历 PDF 并上传到平台"""
    try:
        from boss_career_ops.resume.generator import ResumeGenerator
        from boss_career_ops.resume.pdf_engine import PDFEngine
        from boss_career_ops.resume.keywords import KeywordInjector
        from boss_career_ops.resume.upload import ResumeUploader

        adapter = get_active_adapter()
        try:
            job = adapter.get_job_detail(job_id)
            if job is None:
                return {"ok": False, "message": "获取职位详情失败"}
            job_dict = job.to_dict()
        except Exception:
            job_dict = get_job_detail(job_id) or {}

        generator = ResumeGenerator()
        resume_md = None

        try:
            with _get_pm() as pm:
                ai_result = pm.get_ai_result(job_id, "resume")
                if ai_result:
                    ai_data = json.loads(ai_result["result"])
                    resume_md = ai_data.get("content", "")
        except Exception as e:
            logger.warning("读取 Agent 简历润色结果失败: %s", e)

        if not resume_md:
            resume_md = generator.generate(job_dict)

        if resume_md:
            injector = KeywordInjector()
            jd_text = generator._extract_jd_text(job_dict)
            keywords = injector.extract_from_jd(jd_text)
            resume_md = injector.inject(resume_md, keywords)

        if not resume_md:
            return {"ok": False, "message": "简历生成失败，请检查 cv.md 是否存在"}

        RESUMES_DIR.mkdir(parents=True, exist_ok=True)
        output_path = RESUMES_DIR / f"{job_id}.pdf"
        engine = PDFEngine()
        engine.generate(resume_md, output_path)

        settings = Settings()
        name = getattr(settings.profile, "name", "") or "未命名"
        job_name = job_dict.get("job_name", "未命名")
        display_name = f"{name}_{job_name}.pdf"
        uploader = ResumeUploader()
        result = uploader.upload(output_path, display_name)
        return {"ok": result.get("ok", False), "message": result.get("message", ""), "code": result.get("code", "")}
    except Exception as e:
        logger.warning("简历上传失败: %s", e)
        return {"ok": False, "message": str(e), "code": "RESUME_UPLOAD_ERROR"}


def batch_greet(keyword: str, city: str = "") -> list[dict]:
    """批量打招呼：搜索 → 评估 → 阈值过滤 → 逐条打招呼 + 高斯延迟"""
    thresholds = Thresholds()
    rl = thresholds.rate_limit
    adapter = get_active_adapter()
    from boss_career_ops.evaluator.engine import EvaluationEngine
    engine = EvaluationEngine()
    params = adapter.build_search_params(keyword, city)
    try:
        jobs = adapter.search(params)
        if not jobs:
            return []
        jobs = jobs[:rl.batch_greet_max]
        results = []
        for job in jobs:
            sid = job.security_id
            jid = job.job_id
            if not sid or not jid:
                continue
            evaluation = engine.evaluate(job)
            score = evaluation["total_score"]
            if score < thresholds.auto_action.skip_threshold:
                results.append({
                    "job_name": job.job_name,
                    "job_id": jid,
                    "result": {"ok": False, "message": f"评分 {score} 低于跳过阈值 {thresholds.auto_action.skip_threshold}"},
                    "score": score,
                })
                continue
            if thresholds.auto_action.confirm_required and score < thresholds.auto_action.auto_greet_threshold:
                results.append({
                    "job_name": job.job_name,
                    "job_id": jid,
                    "result": {"ok": False, "message": f"评分 {score} 需人工确认（阈值 {thresholds.auto_action.auto_greet_threshold}）"},
                    "score": score,
                })
                continue
            greet_result = adapter.greet(sid, jid)
            results.append({
                "job_name": job.job_name,
                "job_id": jid,
                "result": {"ok": greet_result.ok, "message": greet_result.message},
                "score": score,
            })
            if greet_result.ok:
                try:
                    with _get_pm() as pm:
                        pm.upsert_job(job_id=jid, security_id=sid)
                        pm.update_stage(jid, Stage.COMMUNICATING)
                except Exception as e:
                    logger.warning("批量打招呼阶段推进写入 Pipeline 失败: %s", e)
            mean = (rl.batch_greet_delay_min + rl.batch_greet_delay_max) / 2
            std = (rl.batch_greet_delay_max - rl.batch_greet_delay_min) / 4
            delay = max(rl.batch_greet_delay_min, random.gauss(mean, std))
            time.sleep(delay)
        return results
    except Exception as e:
        logger.warning("批量打招呼失败: %s", e)
        return []


def evaluate_pending_jobs(limit: int = 50) -> dict:
    """批量评估待评估职位，推进阶段到评估"""
    with _get_pm() as pm:
        unevaluated = pm.get_unevaluated(limit=limit)
    results = []
    for job in unevaluated:
        job_id = job.get("job_id", "")
        if not job_id:
            continue
        try:
            result = evaluate_job(job_id)
            if result:
                results.append({
                    "job_id": job_id,
                    "grade": result.get("grade", ""),
                    "score": result.get("total_score", 0),
                })
        except Exception as e:
            logger.warning("评估职位 %s 失败: %s", job_id, e)
    return {"total": len(unevaluated), "evaluated": len(results), "results": results}


def get_chat_list() -> list[dict]:
    """获取聊天联系人列表，并自动推进匹配职位的阶段到沟通"""
    try:
        adapter = get_active_adapter()
        contacts = adapter.get_chat_list()
        contact_list = [
            {
                "security_id": c.security_id,
                "name": c.name,
                "last_message": c.last_message,
                "time": c.time,
            }
            for c in contacts
        ]
        try:
            with _get_pm() as pm:
                all_pipeline_jobs = pm.list_jobs()
                for contact in contact_list:
                    sid = contact.get("security_id")
                    if not sid:
                        continue
                    for job in all_pipeline_jobs:
                        if job.get("security_id") == sid:
                            current_stage = Stage(job.get("stage", "发现"))
                            comm_idx = STAGE_ORDER.index(Stage.COMMUNICATING)
                            current_idx = STAGE_ORDER.index(current_stage)
                            if current_idx < comm_idx:
                                pm.update_stage(job.get("job_id"), Stage.COMMUNICATING)
                            break
        except Exception as e:
            logger.warning("聊天阶段推进写入 Pipeline 失败: %s", e)
        return contact_list
    except Exception as e:
        logger.warning("获取聊天列表失败: %s", e)
        return []


def generate_chat_summary(security_id: str) -> dict:
    """生成聊天 AI 摘要"""
    messages = get_chat_messages(security_id)
    if not messages:
        return {"security_id": security_id, "summary": "", "message_count": 0}
    with _get_pm() as pm:
        ai_results = pm.get_ai_results(security_id)
        for r in ai_results:
            if r.get("task_type") == "chat_summary":
                return json.loads(r["result"]) if r.get("result") else {}
    return {"security_id": security_id, "summary": "", "message_count": len(messages)}


def analyze_skill_gap() -> dict:
    profile = get_profile()
    pipeline_jobs = list_pipeline_jobs()
    return {
        "skills": profile.get("skills", []),
        "jd_count": len(pipeline_jobs),
        "analysis_available": bool(profile.get("skills") and pipeline_jobs),
    }


def get_resume(job_id: str) -> str | None:
    """获取已生成的简历内容"""
    with _get_pm() as pm:
        ai_results = pm.get_ai_results(job_id)
        for r in ai_results:
            if r.get("task_type") == "resume" and r.get("result"):
                data = json.loads(r["result"])
                return data.get("content", "")
    return None


def generate_resume_pdf(job_id: str) -> str | None:
    """生成简历 PDF 并返回路径，使用 PDFEngine 真正生成 PDF"""
    resume_md = generate_resume(job_id)
    if not resume_md:
        return None
    try:
        from boss_career_ops.resume.pdf_engine import PDFEngine

        RESUMES_DIR.mkdir(parents=True, exist_ok=True)
        pdf_path = RESUMES_DIR / f"{job_id}.pdf"
        engine = PDFEngine()
        engine.generate(resume_md, pdf_path)
        return str(pdf_path)
    except Exception as e:
        logger.warning("生成简历 PDF 失败: %s", e)
        return None


def get_interview_prep(job_id: str) -> dict | None:
    """获取面试准备结果"""
    with _get_pm() as pm:
        ai_results = pm.get_ai_results(job_id)
        for r in ai_results:
            if r.get("task_type") == "interview_prep" and r.get("result"):
                return json.loads(r["result"])
    return None


def prepare_interview(job_id: str) -> Result:
    """准备面试方案，优先返回 Agent 生成结果"""
    job = get_job_detail(job_id)
    if not job:
        return Result.failure(error="职位不存在", code="NOT_FOUND")

    ai_prep = get_interview_prep(job_id)
    if ai_prep:
        ai_prep["source"] = "agent"
        return Result.success(data=ai_prep)

    return Result.failure(
        error="面试准备功能需要 Agent 支持。请先使用 Agent 生成面试准备方案",
        code="AI_RESULT_NOT_FOUND",
    )


def get_analytics_overview() -> dict:
    """数据分析总览"""
    with _get_pm() as pm:
        all_jobs = pm.list_jobs()
    total = len(all_jobs)
    grade_counts = {}
    stage_counts = {}
    total_score = 0
    scored_count = 0
    for job in all_jobs:
        grade = job.get("grade", "")
        if grade:
            grade_counts[grade] = grade_counts.get(grade, 0) + 1
        stage = job.get("stage", "unknown")
        stage_counts[stage] = stage_counts.get(stage, 0) + 1
        score = job.get("total_score") or job.get("score")
        if score:
            total_score += float(score)
            scored_count += 1
    avg_score = round(total_score / scored_count, 2) if scored_count > 0 else 0
    ab_count = grade_counts.get("A", 0) + grade_counts.get("B", 0)
    ab_ratio = round(ab_count / total * 100, 1) if total > 0 else 0
    applied_count = stage_counts.get("applied", 0)
    apply_ratio = round(applied_count / total * 100, 1) if total > 0 else 0
    return {
        "total": total,
        "avg_score": avg_score,
        "grade_counts": grade_counts,
        "stage_counts": stage_counts,
        "ab_ratio": ab_ratio,
        "apply_ratio": apply_ratio,
    }


def analyze_skill_gap_detail() -> dict:
    """详细技能差距分析"""
    profile = get_profile()
    with _get_pm() as pm:
        all_jobs = pm.list_jobs()
    user_skills = set(s.lower() for s in profile.get("skills", []))
    jd_skills_counter = {}
    for job in all_jobs:
        skills = job.get("skills", [])
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(",") if s.strip()]
        for skill in skills:
            skill_lower = skill.lower()
            jd_skills_counter[skill_lower] = jd_skills_counter.get(skill_lower, 0) + 1
    matched = [s for s in jd_skills_counter if s in user_skills]
    missing = sorted(
        [(s, c) for s, c in jd_skills_counter.items() if s not in user_skills],
        key=lambda x: -x[1],
    )[:10]
    return {
        "user_skills": list(user_skills),
        "matched_skills": matched,
        "missing_skills": [{"skill": s, "count": c} for s, c in missing],
        "jd_count": len(all_jobs),
    }


def get_salary_distribution() -> dict:
    """薪资分布统计"""
    with _get_pm() as pm:
        jobs = pm.list_jobs()
    buckets = {"0-10k": 0, "10-20k": 0, "20-30k": 0, "30-50k": 0, "50k+": 0}
    for job in jobs:
        salary_min = job.get("salary_min")
        salary_max = job.get("salary_max")
        avg = 0
        if salary_min and salary_max:
            avg = (salary_min + salary_max) / 2
        elif salary_min:
            avg = salary_min
        elif salary_max:
            avg = salary_max
        else:
            continue
        avg_k = avg / 1000
        if avg_k < 10:
            buckets["0-10k"] += 1
        elif avg_k < 20:
            buckets["10-20k"] += 1
        elif avg_k < 30:
            buckets["20-30k"] += 1
        elif avg_k < 50:
            buckets["30-50k"] += 1
        else:
            buckets["50k+"] += 1
    return buckets
