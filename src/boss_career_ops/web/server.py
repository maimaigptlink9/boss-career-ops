import asyncio
import json
import os
import random
import time
import warnings
from pathlib import Path

import yaml

try:
    from fastapi import FastAPI, Query, Request
    from fastapi.responses import FileResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
except ImportError:
    FastAPI = None

from boss_career_ops.config.settings import BCO_HOME, CONFIG_DIR, RESUMES_DIR, Settings
from boss_career_ops.config.thresholds import Thresholds
from boss_career_ops.display.logger import get_logger
from boss_career_ops.errors import BCOError, Result
from boss_career_ops.evaluator.engine import EvaluationEngine
from boss_career_ops.pipeline.manager import PipelineManager
from boss_career_ops.pipeline.stages import Stage, STAGE_ORDER
from boss_career_ops.platform.registry import get_active_adapter

logger = get_logger(__name__)

API_KEY = os.environ.get("BCO_WEB_API_KEY")

if not API_KEY:
    warnings.warn("BCO_WEB_API_KEY 未设置，Web API 无认证保护，仅建议本地使用")

WRITE_ENDPOINTS = {
    "/api/greet", "/api/apply", "/api/profile", "/api/settings/ai",
    "/api/search", "/api/evaluate", "/api/evaluate/pending",
    "/api/ai/reply-suggest", "/api/pipeline/dismiss", "/api/pipeline/restore",
    "/api/resume/generate", "/api/resume/upload", "/api/interview/prepare",
    "/api/skill-gap/analyze", "/api/batch-greet",
}

STATIC_DIR = Path(__file__).parent / "static"

EVAL_LIMIT = 50


def _ok(data=None):
    return {"ok": True, "data": data}


def _err(error: str, code: str = "INTERNAL_ERROR", **extra):
    result = {"ok": False, "error": error, "code": code}
    result.update(extra)
    return result


if FastAPI is None:
    app = None
else:
    app = FastAPI(title="Boss Career Ops", docs_url=None, redoc_url=None)

    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        if (
            API_KEY
            and request.url.path in WRITE_ENDPOINTS
            and request.method in ("POST", "PUT", "PATCH")
        ):
            auth = request.headers.get("Authorization", "")
            if not auth.startswith("Bearer ") or auth[7:] != API_KEY:
                return JSONResponse(
                    {"ok": False, "error": "未授权", "code": "UNAUTHORIZED"},
                    status_code=401,
                )
        return await call_next(request)

    @app.exception_handler(BCOError)
    async def bco_error_handler(request: Request, exc: BCOError):
        return JSONResponse(
            {"ok": False, "error": exc.message, "code": exc.code},
            status_code=400,
        )

    @app.get("/api/pipeline")
    async def api_pipeline(stage: str | None = Query(default=None), status: str | None = Query(default=None)):
        try:
            def _list():
                with PipelineManager() as pm:
                    return pm.list_jobs(stage=stage, status=status)
            return _ok(await asyncio.to_thread(_list))
        except Exception as e:
            return _err(str(e))

    @app.get("/api/jobs/{job_id}")
    async def api_job_detail(job_id: str):
        try:
            def _detail():
                with PipelineManager() as pm:
                    return pm.get_job_detail(job_id)
            job = await asyncio.to_thread(_detail)
            if job is None:
                return _err("职位不存在", "NOT_FOUND")
            return _ok(job)
        except Exception as e:
            return _err(str(e))

    @app.post("/api/pipeline/dismiss")
    async def api_pipeline_dismiss(body: dict):
        try:
            job_ids = body.get("job_ids", [])
            if not job_ids:
                return _err("job_ids 不能为空", "VALIDATION_ERROR")
            def _dismiss():
                with PipelineManager() as pm:
                    return pm.batch_dismiss(job_ids)
            return _ok({"dismissed": await asyncio.to_thread(_dismiss)})
        except Exception as e:
            return _err(str(e))

    @app.post("/api/pipeline/restore")
    async def api_pipeline_restore(body: dict):
        try:
            job_id = body.get("job_id", "")
            if not job_id:
                return _err("job_id 不能为空", "VALIDATION_ERROR")
            def _restore():
                with PipelineManager() as pm:
                    return pm.restore_job(job_id)
            ok = await asyncio.to_thread(_restore)
            if ok:
                return _ok({"restored": True})
            return _err("恢复失败", "RESTORE_FAILED")
        except Exception as e:
            return _err(str(e))

    @app.get("/api/pipeline/unevaluated")
    async def api_pipeline_unevaluated():
        try:
            def _fn():
                with PipelineManager() as pm:
                    return pm.get_unevaluated()
            return _ok(await asyncio.to_thread(_fn))
        except Exception as e:
            return _err(str(e))

    @app.post("/api/search")
    async def api_search(body: dict):
        try:
            keyword = body.get("keyword", "")
            if not keyword:
                return _err("keyword 不能为空", "VALIDATION_ERROR")
            city = body.get("city", "")
            pages = body.get("pages", 1)
            welfare = body.get("welfare", "")
            evaluate = body.get("evaluate", True)

            def _do():
                adapter = get_active_adapter()
                params = adapter.build_search_params(keyword, city)
                thresholds = Thresholds()
                max_pages = min(pages, thresholds.rate_limit.search_max_pages)
                all_jobs = []
                for p in range(1, max_pages + 1):
                    params["page"] = p
                    try:
                        jobs = adapter.search(params)
                    except Exception:
                        break
                    if not jobs:
                        break
                    if welfare:
                        jobs = adapter.filter_by_welfare(jobs, welfare)
                    all_jobs.extend(jobs)
                    if p < max_pages:
                        rl = thresholds.rate_limit
                        mean = (rl.search_page_delay_min + rl.search_page_delay_max) / 2
                        std = (rl.search_page_delay_max - rl.search_page_delay_min) / 4
                        time.sleep(max(rl.search_page_delay_min, random.gauss(mean, std)))

                results = [
                    {"job_id": j.job_id, "job_name": j.job_name, "company_name": j.company_name,
                     "city": j.city_name, "salary": j.salary_desc, "skills": j.skills, "security_id": j.security_id}
                    for j in all_jobs
                ]

                if evaluate and all_jobs:
                    engine = EvaluationEngine()
                    for job in all_jobs[:EVAL_LIMIT]:
                        try:
                            ev = engine.evaluate(job)
                            try:
                                with PipelineManager() as pm:
                                    pm.upsert_job(job_id=job.job_id, security_id=job.security_id)
                                    pm.update_score(job.job_id, ev["total_score"], ev["grade"])
                                    pm.update_job_data(job.job_id, {"evaluation": ev})
                            except Exception:
                                pass
                            for r in results:
                                if r["job_id"] == job.job_id:
                                    r["grade"] = ev["grade"]
                                    r["total_score"] = ev["total_score"]
                        except Exception:
                            pass

                try:
                    with PipelineManager() as pm:
                        pm.batch_add_jobs(all_jobs)
                except Exception:
                    pass

                if not evaluate:
                    try:
                        with PipelineManager() as pm:
                            for r in results:
                                job = pm.get_job(r["job_id"])
                                if job and job.get("grade"):
                                    r["grade"] = job["grade"]
                                    r["total_score"] = job.get("score")
                    except Exception:
                        pass

                return results

            return _ok(await asyncio.to_thread(_do))
        except Exception as e:
            logger.error("搜索职位失败: %s", e)
            return _err(str(e))

    @app.post("/api/evaluate")
    async def api_evaluate(body: dict):
        try:
            job_id = body.get("job_id", "")
            if not job_id:
                return _err("job_id 不能为空", "VALIDATION_ERROR")

            def _do():
                with PipelineManager() as pm:
                    job = pm.get_job_detail(job_id)
                if not job:
                    return None
                engine = EvaluationEngine()
                result = engine.evaluate(job)
                try:
                    with PipelineManager() as pm:
                        result_data = {"score": result["total_score"], "grade": result["grade"], "analysis": result.get("recommendation", "")}
                        if result.get("scores"):
                            result_data["scores_detail"] = result["scores"]
                        pm.save_ai_result(job_id, "evaluate", json.dumps(result_data, ensure_ascii=False))
                        pm.update_score(job_id, result["total_score"], result["grade"])
                        pm.update_stage(job_id, Stage.EVALUATED)
                except Exception:
                    pass
                return result

            result = await asyncio.to_thread(_do)
            if result is None:
                return _err("职位不存在", "NOT_FOUND")
            return _ok(result)
        except Exception as e:
            logger.error("评估职位失败: %s", e)
            return _err(str(e))

    @app.post("/api/evaluate/pending")
    async def api_evaluate_pending(body: dict):
        try:
            limit = body.get("limit", 50)

            def _do():
                with PipelineManager() as pm:
                    unevaluated = pm.get_unevaluated(limit=limit)
                results = []
                engine = EvaluationEngine()
                for job in unevaluated:
                    job_id = job.get("job_id", "")
                    if not job_id:
                        continue
                    try:
                        ev = engine.evaluate(job)
                        try:
                            with PipelineManager() as pm:
                                pm.update_score(job_id, ev["total_score"], ev["grade"])
                                pm.update_stage(job_id, Stage.EVALUATED)
                        except Exception:
                            pass
                        results.append({"job_id": job_id, "grade": ev.get("grade", ""), "score": ev.get("total_score", 0)})
                    except Exception:
                        pass
                return {"total": len(unevaluated), "evaluated": len(results), "results": results}

            return _ok(await asyncio.to_thread(_do))
        except Exception as e:
            logger.error("批量评估失败: %s", e)
            return _err(str(e))

    @app.post("/api/greet")
    async def api_greet(body: dict):
        try:
            security_id = body.get("security_id", "")
            job_id = body.get("job_id", "")
            if not security_id or not job_id:
                return _err("security_id 和 job_id 不能为空", "VALIDATION_ERROR")

            def _do():
                adapter = get_active_adapter()
                result = adapter.greet(security_id, job_id)
                if result.ok:
                    try:
                        with PipelineManager() as pm:
                            pm.upsert_job(job_id=job_id, security_id=security_id)
                            pm.update_stage(job_id, Stage.COMMUNICATING)
                    except Exception:
                        pass
                    return Result.success(data={"message": result.message})
                return Result.failure(error=result.message, code="GREET_FAILED")

            result = await asyncio.to_thread(_do)
            if result.ok:
                return _ok(result.data)
            return _err(result.error, result.code or "GREET_FAILED")
        except Exception as e:
            logger.error("打招呼失败: %s", e)
            return _err(str(e))

    @app.post("/api/batch-greet")
    async def api_batch_greet(body: dict):
        try:
            keyword = body.get("keyword", "")
            if not keyword:
                return _err("keyword 不能为空", "VALIDATION_ERROR")
            city = body.get("city", "")

            def _do():
                thresholds = Thresholds()
                rl = thresholds.rate_limit
                adapter = get_active_adapter()
                engine = EvaluationEngine()
                params = adapter.build_search_params(keyword, city)
                try:
                    jobs = adapter.search(params)
                except Exception:
                    return []
                jobs = jobs[:rl.batch_greet_max]
                results = []
                for job in jobs:
                    sid, jid = job.security_id, job.job_id
                    if not sid or not jid:
                        continue
                    evaluation = engine.evaluate(job)
                    score = evaluation["total_score"]
                    if score < thresholds.auto_action.skip_threshold:
                        results.append({"job_name": job.job_name, "job_id": jid, "result": {"ok": False, "message": f"评分 {score} 低于跳过阈值"}, "score": score})
                        continue
                    greet_result = adapter.greet(sid, jid)
                    results.append({"job_name": job.job_name, "job_id": jid, "result": {"ok": greet_result.ok, "message": greet_result.message}, "score": score})
                    if greet_result.ok:
                        try:
                            with PipelineManager() as pm:
                                pm.upsert_job(job_id=jid, security_id=sid)
                                pm.update_stage(jid, Stage.COMMUNICATING)
                        except Exception:
                            pass
                    mean = (rl.batch_greet_delay_min + rl.batch_greet_delay_max) / 2
                    std = (rl.batch_greet_delay_max - rl.batch_greet_delay_min) / 4
                    time.sleep(max(rl.batch_greet_delay_min, random.gauss(mean, std)))
                return results

            return _ok(await asyncio.to_thread(_do))
        except Exception as e:
            logger.error("批量打招呼失败: %s", e)
            return _err(str(e))

    @app.post("/api/apply")
    async def api_apply(body: dict):
        try:
            security_id = body.get("security_id", "")
            job_id = body.get("job_id", "")
            if not security_id or not job_id:
                return _err("security_id 和 job_id 不能为空", "VALIDATION_ERROR")

            def _do():
                adapter = get_active_adapter()
                result = adapter.apply(security_id, job_id)
                if result.ok:
                    try:
                        with PipelineManager() as pm:
                            pm.upsert_job(job_id=job_id, security_id=security_id)
                            pm.update_stage(job_id, Stage.APPLIED)
                    except Exception:
                        pass
                    return Result.success(data={"message": result.message})
                return Result.failure(error=result.message, code="APPLY_FAILED")

            result = await asyncio.to_thread(_do)
            if result.ok:
                return _ok(result.data)
            return _err(result.error, result.code or "APPLY_FAILED")
        except Exception as e:
            logger.error("投递失败: %s", e)
            return _err(str(e))

    @app.post("/api/resume/upload")
    async def api_resume_upload(body: dict):
        return _err("简历上传请使用 CLI: bco resume <job_id>", "USE_CLI")

    @app.post("/api/resume/generate")
    async def api_resume_generate(body: dict):
        return _err("简历生成请使用 CLI: bco resume <job_id>", "USE_CLI")

    @app.get("/api/resume/{job_id}")
    async def api_resume_get(job_id: str):
        try:
            def _do():
                with PipelineManager() as pm:
                    r = pm.get_ai_result(job_id, "resume")
                    if r:
                        data = json.loads(r["result"])
                        return data.get("content", "")
                return None
            content = await asyncio.to_thread(_do)
            if content is None:
                return _err("简历不存在", "NOT_FOUND")
            return _ok({"content": content, "format": "markdown"})
        except Exception as e:
            return _err(str(e))

    @app.get("/api/resume/{job_id}/pdf")
    async def api_resume_pdf(job_id: str):
        return _err("简历 PDF 请使用 CLI: bco resume <job_id>", "USE_CLI")

    @app.get("/api/chat/{security_id}")
    async def api_chat(security_id: str):
        try:
            def _do():
                adapter = get_active_adapter()
                messages = adapter.get_chat_messages(security_id)
                return [{"sender_name": m.sender_name, "content": m.content, "time": m.time} for m in messages]
            return _ok(await asyncio.to_thread(_do))
        except Exception as e:
            return _err(str(e))

    @app.get("/api/chat-list")
    async def api_chat_list():
        try:
            def _do():
                adapter = get_active_adapter()
                contacts = adapter.get_chat_list()
                contact_list = [{"security_id": c.security_id, "name": c.name, "last_message": c.last_message, "time": c.time} for c in contacts]
                try:
                    with PipelineManager() as pm:
                        all_jobs = pm.list_jobs()
                        for contact in contact_list:
                            sid = contact.get("security_id")
                            if not sid:
                                continue
                            for job in all_jobs:
                                if job.get("security_id") == sid:
                                    current_stage = Stage(job.get("stage", "发现"))
                                    if STAGE_ORDER.index(current_stage) < STAGE_ORDER.index(Stage.COMMUNICATING):
                                        pm.update_stage(job.get("job_id"), Stage.COMMUNICATING)
                                    break
                except Exception:
                    pass
                return contact_list
            return _ok(await asyncio.to_thread(_do))
        except Exception as e:
            return _err(str(e))

    @app.get("/api/chat/{security_id}/summary")
    async def api_chat_summary(security_id: str):
        try:
            def _do():
                with PipelineManager() as pm:
                    r = pm.get_ai_result(security_id, "chat_summary")
                    if r:
                        return json.loads(r["result"])
                return {"security_id": security_id, "summary": "", "message_count": 0}
            return _ok(await asyncio.to_thread(_do))
        except Exception as e:
            return _err(str(e))

    @app.get("/api/profile")
    async def api_get_profile():
        try:
            def _do():
                s = Settings()
                p = s.profile
                return {
                    "name": p.name, "title": p.title, "experience_years": p.experience_years,
                    "skills": p.skills, "expected_salary": {"min": p.expected_salary_min, "max": p.expected_salary_max},
                    "preferred_cities": p.preferred_cities, "remote_ok": p.remote_ok,
                    "education": p.education, "career_goals": p.career_goals, "avoid": p.avoid,
                }
            return _ok(await asyncio.to_thread(_do))
        except Exception as e:
            return _err(str(e))

    @app.put("/api/profile")
    async def api_update_profile(body: dict):
        try:
            def _update():
                profile_path = CONFIG_DIR / "profile.yml"
                profile_path.parent.mkdir(parents=True, exist_ok=True)
                current = {}
                if profile_path.exists():
                    try:
                        current = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
                    except Exception:
                        current = {}
                if not isinstance(current, dict):
                    current = {}
                if "expected_salary" in body and isinstance(body["expected_salary"], dict):
                    salary_body = body.pop("expected_salary")
                    current_salary = current.get("expected_salary", {})
                    if not isinstance(current_salary, dict):
                        current_salary = {}
                    for k, v in salary_body.items():
                        if v is not None:
                            current_salary[k] = v
                    current["expected_salary"] = current_salary
                current.update(body)
                profile_path.write_text(yaml.dump(current, allow_unicode=True, default_flow_style=False), encoding="utf-8")
                from boss_career_ops.config.singleton import SingletonMeta
                SingletonMeta.reload_instance(Settings)
                s = Settings()
                p = s.profile
                return {
                    "name": p.name, "title": p.title, "experience_years": p.experience_years,
                    "skills": p.skills, "expected_salary": {"min": p.expected_salary_min, "max": p.expected_salary_max},
                    "preferred_cities": p.preferred_cities, "remote_ok": p.remote_ok,
                    "education": p.education, "career_goals": p.career_goals, "avoid": p.avoid,
                }
            return _ok(await asyncio.to_thread(_update))
        except Exception as e:
            logger.error("更新个人档案失败: %s", e)
            return _err(str(e))

    @app.get("/api/stats")
    async def api_stats():
        try:
            def _stats():
                with PipelineManager() as pm:
                    all_jobs = pm.list_jobs()
                stage_counts: dict[str, int] = {}
                for job in all_jobs:
                    stage = job.get("stage", "unknown")
                    stage_counts[stage] = stage_counts.get(stage, 0) + 1
                return {"total": len(all_jobs), "by_stage": stage_counts}
            return _ok(await asyncio.to_thread(_stats))
        except Exception as e:
            return _err(str(e))

    @app.get("/api/settings/ai")
    async def api_settings_ai():
        return _ok({"configured": False, "provider": "", "source": "removed"})

    @app.post("/api/settings/ai")
    async def api_save_settings_ai(body: dict):
        return _err("Agent 系统已移除", "AGENT_REMOVED")

    @app.get("/api/settings/providers")
    async def api_settings_providers():
        return _ok([])

    @app.get("/api/auth/status")
    async def api_auth_status():
        try:
            def _check():
                from boss_career_ops.boss.auth.token_store import TokenStore
                return TokenStore().check_quality()
            return _ok(await asyncio.to_thread(_check))
        except Exception:
            return _ok({"ok": False, "missing": ["all"], "message": "无法检查认证状态"})

    @app.post("/api/ai/reply-suggest")
    async def api_reply_suggest(body: dict):
        return _err("Agent 系统已移除", "AGENT_REMOVED")

    @app.post("/api/interview/prepare")
    async def api_interview_prepare(body: dict):
        try:
            job_id = body.get("job_id", "")
            if not job_id:
                return _err("job_id 不能为空", "VALIDATION_ERROR")
            def _do():
                with PipelineManager() as pm:
                    r = pm.get_ai_result(job_id, "interview_prep")
                    if r:
                        data = json.loads(r["result"])
                        data["source"] = "agent"
                        return data
                return None
            result = await asyncio.to_thread(_do)
            if result is None:
                return _err("面试准备不存在，请使用 CLI: bco interview <job_id>", "NOT_FOUND")
            return _ok(result)
        except Exception as e:
            return _err(str(e))

    @app.get("/api/interview/{job_id}")
    async def api_interview_get(job_id: str):
        try:
            def _do():
                with PipelineManager() as pm:
                    r = pm.get_ai_result(job_id, "interview_prep")
                    if r:
                        return json.loads(r["result"])
                return None
            result = await asyncio.to_thread(_do)
            if result is None:
                return _err("面试准备不存在", "NOT_FOUND")
            return _ok(result)
        except Exception as e:
            return _err(str(e))

    @app.get("/api/analytics/overview")
    async def api_analytics_overview():
        try:
            def _do():
                with PipelineManager() as pm:
                    jobs = pm.list_jobs()
                total = len(jobs)
                scores = [j.get("score", 0) for j in jobs if j.get("score")]
                grade_counts: dict[str, int] = {}
                stage_counts: dict[str, int] = {}
                for j in jobs:
                    if j.get("grade"):
                        grade_counts[j["grade"]] = grade_counts.get(j["grade"], 0) + 1
                    stage_counts[j.get("stage", "unknown")] = stage_counts.get(j.get("stage", "unknown"), 0) + 1
                a_count = grade_counts.get("A", 0) + grade_counts.get("A+", 0)
                b_count = grade_counts.get("B", 0) + grade_counts.get("B+", 0)
                applied = stage_counts.get("已投递", 0) + stage_counts.get("沟通中", 0)
                return {
                    "total": total, "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
                    "grade_counts": grade_counts, "stage_counts": stage_counts,
                    "ab_ratio": f"{a_count}:{b_count}" if b_count else f"{a_count}:0",
                    "apply_ratio": f"{applied}/{total}" if total else "0/0",
                }
            return _ok(await asyncio.to_thread(_do))
        except Exception as e:
            return _err(str(e))

    @app.get("/api/analytics/salary-distribution")
    async def api_analytics_salary():
        try:
            def _do():
                with PipelineManager() as pm:
                    jobs = pm.list_jobs()
                buckets = {"0-10k": 0, "10-20k": 0, "20-30k": 0, "30-50k": 0, "50k+": 0}
                for j in jobs:
                    data = {}
                    try:
                        data = json.loads(j.get("data", "{}"))
                    except Exception:
                        pass
                    s_min = j.get("salary_min") or data.get("salary_min")
                    s_max = j.get("salary_max") or data.get("salary_max")
                    avg = ((s_min or 0) + (s_max or 0)) / 2 / 1000 if (s_min or s_max) else None
                    if avg is None:
                        continue
                    if avg < 10:
                        buckets["0-10k"] += 1
                    elif avg < 20:
                        buckets["10-20k"] += 1
                    elif avg < 30:
                        buckets["20-30k"] += 1
                    elif avg < 50:
                        buckets["30-50k"] += 1
                    else:
                        buckets["50k+"] += 1
                return buckets
            return _ok(await asyncio.to_thread(_do))
        except Exception as e:
            return _err(str(e))

    @app.get("/api/analytics/grade-distribution")
    async def api_analytics_grade():
        try:
            def _do():
                with PipelineManager() as pm:
                    jobs = pm.list_jobs()
                grade_counts: dict[str, int] = {}
                for j in jobs:
                    if j.get("grade"):
                        grade_counts[j["grade"]] = grade_counts.get(j["grade"], 0) + 1
                return grade_counts
            return _ok(await asyncio.to_thread(_do))
        except Exception as e:
            return _err(str(e))

    @app.get("/api/analytics/stage-funnel")
    async def api_analytics_funnel():
        try:
            def _do():
                with PipelineManager() as pm:
                    jobs = pm.list_jobs()
                stage_counts: dict[str, int] = {}
                for j in jobs:
                    stage_counts[j.get("stage", "unknown")] = stage_counts.get(j.get("stage", "unknown"), 0) + 1
                return stage_counts
            return _ok(await asyncio.to_thread(_do))
        except Exception as e:
            return _err(str(e))

    @app.post("/api/skill-gap/analyze")
    async def api_skill_gap_analyze(body: dict):
        try:
            def _do():
                s = Settings()
                user_skills = [sk.lower() for sk in (s.profile.skills or [])]
                with PipelineManager() as pm:
                    jobs = pm.list_jobs()
                jd_skill_count: dict[str, int] = {}
                for j in jobs:
                    for sk in (j.get("skills") or []):
                        jd_skill_count[sk.lower()] = jd_skill_count.get(sk.lower(), 0) + 1
                matched = [sk for sk in jd_skill_count if any(sk in us or us in sk for us in user_skills)]
                gap = sorted(
                    [(sk, cnt) for sk, cnt in jd_skill_count.items() if not any(sk in us or us in sk for us in user_skills)],
                    key=lambda x: -x[1],
                )[:10]
                return {"user_skills": user_skills, "matched_skills": matched, "missing_skills": gap, "jd_count": len(jobs)}
            return _ok(await asyncio.to_thread(_do))
        except Exception as e:
            return _err(str(e))

    @app.get("/")
    async def serve_index():
        if (STATIC_DIR / "index.html").exists():
            return FileResponse(STATIC_DIR / "index.html")
        return _ok({"message": "Boss Career Ops API"})

    if STATIC_DIR.exists():
        app.mount("/", StaticFiles(directory=str(STATIC_DIR)), name="static")
