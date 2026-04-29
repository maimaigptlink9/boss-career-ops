import asyncio
import os
import warnings
from pathlib import Path

import yaml

try:
    from fastapi import FastAPI, Query, Request
    from fastapi.responses import FileResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
except ImportError:
    FastAPI = None

from boss_career_ops.agent import tools as agent_tools
from boss_career_ops.agent.llm import PROVIDER_DEFAULTS, is_llm_available, reset_llm
from boss_career_ops.config.settings import BCO_HOME, CONFIG_DIR
from boss_career_ops.display.logger import get_logger
from boss_career_ops.errors import BCOError, Result

logger = get_logger(__name__)

API_KEY = os.environ.get("BCO_WEB_API_KEY")

if not API_KEY:
    warnings.warn("BCO_WEB_API_KEY 未设置，Web API 无认证保护，仅建议本地使用")

WRITE_ENDPOINTS = {
    "/api/greet",
    "/api/apply",
    "/api/profile",
    "/api/settings/ai",
    "/api/search",
    "/api/evaluate",
    "/api/evaluate/pending",
    "/api/ai/reply-suggest",
    "/api/pipeline/dismiss",
    "/api/pipeline/restore",
    "/api/resume/generate",
    "/api/resume/upload",
    "/api/interview/prepare",
    "/api/skill-gap/analyze",
    "/api/batch-greet",
}

STATIC_DIR = Path(__file__).parent / "static"


def _ok(data=None):
    return {"ok": True, "data": data}


def _err(error: str, code: str = "INTERNAL_ERROR", **extra):
    result = {"ok": False, "error": error, "code": code}
    result.update(extra)
    return result


def _get_ai_status():
    from boss_career_ops.config.ai_config import get_ai_config
    cfg = get_ai_config()
    configured = is_llm_available()
    source = "env" if os.environ.get("BCO_LLM_API_KEY", "") else ("file" if configured else "none")
    return {
        "configured": configured,
        "provider": cfg.get("provider", "deepseek"),
        "base_url": cfg.get("base_url", ""),
        "model": cfg.get("model", ""),
        "source": source,
    }


def _build_reply_prompt(context: list, job: dict | None, message: str) -> str:
    parts = ["你是一个求职回复助手。根据聊天上下文和职位信息，生成 2-3 条专业、得体的回复建议。"]
    if context:
        parts.append("\n聊天上下文：")
        for msg in context[-10:]:
            sender = msg.get("sender_name", "对方")
            content = msg.get("content", "")
            parts.append(f"  {sender}: {content}")
    if job:
        parts.append(f"\n职位信息：{job.get('company_name', '')} · {job.get('job_name', '')}")
    if message:
        parts.append(f"\n对方最新消息：{message}")
    parts.append("\n请生成 2-3 条回复建议，每条一行，用数字编号。")
    return "\n".join(parts)


def _parse_suggestions(content: str) -> list[str]:
    suggestions = []
    for line in content.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        import re
        cleaned = re.sub(r'^\d+[\.\、\)]\s*', '', line)
        if cleaned:
            suggestions.append(cleaned)
    return suggestions[:3]


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
            jobs = await asyncio.to_thread(lambda: agent_tools.list_pipeline_jobs(stage=stage, status=status))
            return _ok(jobs)
        except Exception as e:
            logger.error("获取 Pipeline 失败: %s", e)
            return _err(str(e))

    @app.get("/api/jobs/{job_id}")
    async def api_job_detail(job_id: str):
        try:
            job = await asyncio.to_thread(agent_tools.get_job_with_ai_result, job_id)
            if job is None:
                return _err("职位不存在", "NOT_FOUND")
            return _ok(job)
        except Exception as e:
            logger.error("获取职位详情失败: %s", e)
            return _err(str(e))

    @app.post("/api/pipeline/dismiss")
    async def api_pipeline_dismiss(body: dict):
        try:
            job_ids = body.get("job_ids", [])
            if not job_ids:
                return _err("job_ids 不能为空", "VALIDATION_ERROR")
            count = await asyncio.to_thread(agent_tools.batch_dismiss_pipeline_jobs, job_ids)
            return _ok({"dismissed": count})
        except Exception as e:
            logger.error("排除职位失败: %s", e)
            return _err(str(e))

    @app.post("/api/pipeline/restore")
    async def api_pipeline_restore(body: dict):
        try:
            job_id = body.get("job_id", "")
            if not job_id:
                return _err("job_id 不能为空", "VALIDATION_ERROR")
            ok = await asyncio.to_thread(agent_tools.restore_pipeline_job, job_id)
            if ok:
                return _ok({"restored": True})
            return _err("恢复失败，职位可能不是已排除状态", "RESTORE_FAILED")
        except Exception as e:
            logger.error("恢复职位失败: %s", e)
            return _err(str(e))

    @app.get("/api/pipeline/unevaluated")
    async def api_pipeline_unevaluated():
        try:
            jobs = await asyncio.to_thread(agent_tools.get_unevaluated_jobs)
            return _ok(jobs)
        except Exception as e:
            logger.error("获取未评估职位失败: %s", e)
            return _err(str(e))

    @app.post("/api/search")
    async def api_search(body: dict):
        try:
            keyword = body.get("keyword", "")
            city = body.get("city", "")
            pages = body.get("pages", 1)
            welfare = body.get("welfare", "")
            evaluate = body.get("evaluate", True)
            if not keyword:
                return _err("keyword 不能为空", "VALIDATION_ERROR")
            jobs = await asyncio.to_thread(
                agent_tools.search_jobs, keyword, city, pages, welfare, evaluate
            )
            return _ok(jobs)
        except Exception as e:
            logger.error("搜索职位失败: %s", e)
            return _err(str(e))

    @app.post("/api/evaluate")
    async def api_evaluate(body: dict):
        try:
            job_id = body.get("job_id", "")
            if not job_id:
                return _err("job_id 不能为空", "VALIDATION_ERROR")
            result = await asyncio.to_thread(agent_tools.evaluate_job, job_id)
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
            result = await asyncio.to_thread(agent_tools.evaluate_pending_jobs, limit)
            return _ok(result)
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
            result = await asyncio.to_thread(agent_tools.greet_recruiter, security_id, job_id)
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
            city = body.get("city", "")
            if not keyword:
                return _err("keyword 不能为空", "VALIDATION_ERROR")
            results = await asyncio.to_thread(agent_tools.batch_greet, keyword, city)
            return _ok(results)
        except Exception as e:
            logger.error("批量打招呼失败: %s", e)
            return _err(str(e))

    @app.post("/api/apply")
    async def api_apply(body: dict):
        try:
            security_id = body.get("security_id", "")
            job_id = body.get("job_id", "")
            resume_job_id = body.get("resume_job_id", "")
            if not security_id or not job_id:
                return _err("security_id 和 job_id 不能为空", "VALIDATION_ERROR")
            result = await asyncio.to_thread(
                agent_tools.apply_job, security_id, job_id, resume_job_id
            )
            if result.ok:
                return _ok(result.data)
            return _err(result.error, result.code or "APPLY_FAILED")
        except Exception as e:
            logger.error("投递失败: %s", e)
            return _err(str(e))

    @app.post("/api/resume/upload")
    async def api_resume_upload(body: dict):
        try:
            job_id = body.get("job_id", "")
            if not job_id:
                return _err("job_id 不能为空", "VALIDATION_ERROR")
            result = await asyncio.to_thread(agent_tools.upload_resume, job_id)
            if result.get("ok"):
                return _ok(result)
            return _err(result.get("message", "上传失败"), result.get("code", "RESUME_UPLOAD_ERROR"))
        except Exception as e:
            logger.error("简历上传失败: %s", e)
            return _err(str(e))

    @app.get("/api/chat/{security_id}")
    async def api_chat(security_id: str):
        try:
            messages = await asyncio.to_thread(agent_tools.get_chat_messages, security_id)
            return _ok(messages)
        except Exception as e:
            logger.error("获取聊天记录失败: %s", e)
            return _err(str(e))

    @app.get("/api/chat-list")
    async def api_chat_list():
        try:
            contacts = await asyncio.to_thread(agent_tools.get_chat_list)
            return _ok(contacts)
        except Exception as e:
            logger.error("获取聊天列表失败: %s", e)
            return _err(str(e))

    @app.get("/api/chat/{security_id}/summary")
    async def api_chat_summary(security_id: str):
        try:
            result = await asyncio.to_thread(agent_tools.generate_chat_summary, security_id)
            return _ok(result)
        except Exception as e:
            logger.error("获取聊天摘要失败: %s", e)
            return _err(str(e))

    @app.get("/api/profile")
    async def api_get_profile():
        try:
            profile = await asyncio.to_thread(agent_tools.get_profile)
            return _ok(profile)
        except Exception as e:
            logger.error("获取个人档案失败: %s", e)
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

                profile_path.write_text(
                    yaml.dump(current, allow_unicode=True, default_flow_style=False),
                    encoding="utf-8",
                )

                from boss_career_ops.config.singleton import SingletonMeta
                from boss_career_ops.config.settings import Settings
                SingletonMeta.reload_instance(Settings)

                return agent_tools.get_profile()

            profile = await asyncio.to_thread(_update)
            return _ok(profile)
        except Exception as e:
            logger.error("更新个人档案失败: %s", e)
            return _err(str(e))

    @app.get("/api/stats")
    async def api_stats():
        try:
            all_jobs = await asyncio.to_thread(agent_tools.list_pipeline_jobs)
            stage_counts: dict[str, int] = {}
            for job in all_jobs:
                stage = job.get("stage", "unknown")
                stage_counts[stage] = stage_counts.get(stage, 0) + 1
            return _ok({
                "total": len(all_jobs),
                "by_stage": stage_counts,
            })
        except Exception as e:
            logger.error("获取统计失败: %s", e)
            return _err(str(e))

    @app.get("/api/settings/ai")
    async def api_settings_ai():
        try:
            status = await asyncio.to_thread(_get_ai_status)
            return _ok(status)
        except Exception as e:
            logger.error("获取 AI 设置失败: %s", e)
            return _err(str(e))

    @app.post("/api/settings/ai")
    async def api_save_settings_ai(body: dict):
        try:
            provider = body.get("provider", "")
            api_key = body.get("api_key", "")
            base_url = body.get("base_url", "")
            model = body.get("model", "")
            if not provider or not api_key:
                return _err("provider 和 api_key 不能为空", "VALIDATION_ERROR")

            def _save():
                from boss_career_ops.config.ai_config import save_ai_config
                save_ai_config(provider, api_key, base_url=base_url, model=model)
                reset_llm()
                return _get_ai_status()

            status = await asyncio.to_thread(_save)
            return _ok(status)
        except Exception as e:
            logger.error("保存 AI 设置失败: %s", e)
            return _err(str(e))

    @app.get("/api/settings/providers")
    async def api_settings_providers():
        try:
            providers = []
            for pid, info in PROVIDER_DEFAULTS.items():
                providers.append({
                    "id": pid,
                    "name": pid.capitalize(),
                    "base_url": info.get("base_url") or "",
                    "default_model": info.get("model", ""),
                })
            return _ok(providers)
        except Exception as e:
            logger.error("获取 Provider 列表失败: %s", e)
            return _err(str(e))

    @app.get("/api/auth/status")
    async def api_auth_status():
        try:
            def _check():
                from boss_career_ops.boss.auth.token_store import TokenStore
                store = TokenStore()
                return store.check_quality()
            quality = await asyncio.to_thread(_check)
            return _ok(quality)
        except Exception as e:
            logger.error("获取认证状态失败: %s", e)
            return _ok({"ok": False, "missing": ["all"], "message": "无法检查认证状态"})

    @app.post("/api/ai/reply-suggest")
    async def api_reply_suggest(body: dict):
        try:
            if not is_llm_available():
                return _err(
                    "AI 功能需要配置 API Key",
                    "AI_NOT_CONFIGURED",
                    setup_url="#/settings",
                )
            security_id = body.get("security_id", "")
            job_id = body.get("job_id", "")
            message = body.get("message", "")
            if not security_id and not message:
                return _err("security_id 或 message 至少提供一个", "VALIDATION_ERROR")

            def _generate():
                context = []
                if security_id:
                    messages = agent_tools.get_chat_messages(security_id)
                    context = messages[-10:]

                job = None
                if job_id:
                    job = agent_tools.get_job_with_ai_result(job_id)

                from boss_career_ops.agent.llm import get_llm
                llm = get_llm()
                if llm is None:
                    return {"suggestions": []}

                prompt = _build_reply_prompt(context, job, message)
                response = llm.invoke(prompt)
                return {"suggestions": _parse_suggestions(response.content)}

            suggestions = await asyncio.to_thread(_generate)
            return _ok(suggestions)
        except Exception as e:
            logger.error("AI 回复建议失败: %s", e)
            return _err(str(e))

    @app.post("/api/resume/generate")
    async def api_resume_generate(body: dict):
        try:
            job_id = body.get("job_id", "")
            inject_keywords = body.get("inject_keywords", True)
            if not job_id:
                return _err("job_id 不能为空", "VALIDATION_ERROR")
            result = await asyncio.to_thread(agent_tools.generate_resume, job_id, inject_keywords)
            if result is None:
                return _err("简历生成失败，请检查 cv.md 是否存在", "RESUME_ERROR")
            return _ok({"content": result, "format": "markdown"})
        except Exception as e:
            logger.error("生成简历失败: %s", e)
            return _err(str(e))

    @app.get("/api/resume/{job_id}")
    async def api_resume_get(job_id: str):
        try:
            content = await asyncio.to_thread(agent_tools.get_resume, job_id)
            if content is None:
                return _err("简历不存在", "NOT_FOUND")
            return _ok({"content": content, "format": "markdown"})
        except Exception as e:
            logger.error("获取简历失败: %s", e)
            return _err(str(e))

    @app.get("/api/resume/{job_id}/pdf")
    async def api_resume_pdf(job_id: str):
        try:
            pdf_path = await asyncio.to_thread(agent_tools.generate_resume_pdf, job_id)
            if pdf_path and Path(pdf_path).exists():
                return FileResponse(pdf_path, media_type="application/pdf", filename=f"resume_{job_id}.pdf")
            return _err("PDF 生成失败", "PDF_ERROR")
        except Exception as e:
            logger.error("获取简历 PDF 失败: %s", e)
            return _err(str(e))

    @app.post("/api/interview/prepare")
    async def api_interview_prepare(body: dict):
        try:
            job_id = body.get("job_id", "")
            if not job_id:
                return _err("job_id 不能为空", "VALIDATION_ERROR")
            result = await asyncio.to_thread(agent_tools.prepare_interview, job_id)
            if not result.ok:
                return _err(result.error, result.code or "INTERVIEW_ERROR")
            return _ok(result.data)
        except Exception as e:
            logger.error("面试准备失败: %s", e)
            return _err(str(e))

    @app.get("/api/interview/{job_id}")
    async def api_interview_get(job_id: str):
        try:
            result = await asyncio.to_thread(agent_tools.get_interview_prep, job_id)
            if result is None:
                return _err("面试准备不存在", "NOT_FOUND")
            return _ok(result)
        except Exception as e:
            logger.error("获取面试准备失败: %s", e)
            return _err(str(e))

    @app.get("/api/analytics/overview")
    async def api_analytics_overview():
        try:
            result = await asyncio.to_thread(agent_tools.get_analytics_overview)
            return _ok(result)
        except Exception as e:
            logger.error("获取数据总览失败: %s", e)
            return _err(str(e))

    @app.get("/api/analytics/salary-distribution")
    async def api_analytics_salary():
        try:
            result = await asyncio.to_thread(agent_tools.get_salary_distribution)
            return _ok(result)
        except Exception as e:
            logger.error("获取薪资分布失败: %s", e)
            return _err(str(e))

    @app.get("/api/analytics/grade-distribution")
    async def api_analytics_grade():
        try:
            result = await asyncio.to_thread(agent_tools.get_analytics_overview)
            return _ok(result.get("grade_counts", {}))
        except Exception as e:
            logger.error("获取等级分布失败: %s", e)
            return _err(str(e))

    @app.get("/api/analytics/stage-funnel")
    async def api_analytics_funnel():
        try:
            result = await asyncio.to_thread(agent_tools.get_analytics_overview)
            return _ok(result.get("stage_counts", {}))
        except Exception as e:
            logger.error("获取阶段漏斗失败: %s", e)
            return _err(str(e))

    @app.post("/api/skill-gap/analyze")
    async def api_skill_gap_analyze(body: dict):
        try:
            result = await asyncio.to_thread(agent_tools.analyze_skill_gap_detail)
            return _ok(result)
        except Exception as e:
            logger.error("技能差距分析失败: %s", e)
            return _err(str(e))

    @app.get("/")
    async def serve_index():
        if (STATIC_DIR / "index.html").exists():
            return FileResponse(STATIC_DIR / "index.html")
        return _ok({"message": "Boss Career Ops API"})

    if STATIC_DIR.exists():
        app.mount("/", StaticFiles(directory=str(STATIC_DIR)), name="static")
