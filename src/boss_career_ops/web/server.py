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
    "/api/ai/reply-suggest",
}

STATIC_DIR = Path(__file__).parent / "static"


def _ok(data=None):
    return {"ok": True, "data": data}


def _err(error: str, code: str = "INTERNAL_ERROR", **extra):
    result = {"ok": False, "error": error, "code": code}
    result.update(extra)
    return result


def _get_ai_status():
    provider = os.environ.get("BCO_LLM_PROVIDER", "deepseek").lower()
    api_key_env = os.environ.get("BCO_LLM_API_KEY", "")
    configured = is_llm_available()
    source = "env" if api_key_env else ("file" if configured else "none")
    return {
        "configured": configured,
        "provider": provider,
        "source": source,
    }


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
    async def api_pipeline(stage: str | None = Query(default=None)):
        try:
            jobs = await asyncio.to_thread(lambda: agent_tools.list_pipeline_jobs(stage=stage))
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

    @app.post("/api/search")
    async def api_search(body: dict):
        try:
            keyword = body.get("keyword", "")
            city = body.get("city", "")
            if not keyword:
                return _err("keyword 不能为空", "VALIDATION_ERROR")
            jobs = await asyncio.to_thread(agent_tools.search_jobs, keyword, city)
            return _ok(jobs)
        except Exception as e:
            logger.error("搜索职位失败: %s", e)
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

    @app.post("/api/apply")
    async def api_apply(body: dict):
        try:
            security_id = body.get("security_id", "")
            job_id = body.get("job_id", "")
            if not security_id or not job_id:
                return _err("security_id 和 job_id 不能为空", "VALIDATION_ERROR")
            result = await asyncio.to_thread(agent_tools.apply_job, security_id, job_id)
            if result.ok:
                return _ok(result.data)
            return _err(result.error, result.code or "APPLY_FAILED")
        except Exception as e:
            logger.error("投递失败: %s", e)
            return _err(str(e))

    @app.get("/api/chat/{security_id}")
    async def api_chat(security_id: str):
        try:
            messages = await asyncio.to_thread(agent_tools.get_chat_messages, security_id)
            return _ok(messages)
        except Exception as e:
            logger.error("获取聊天记录失败: %s", e)
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
                    current_salary.update(salary_body)
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
            if not provider or not api_key:
                return _err("provider 和 api_key 不能为空", "VALIDATION_ERROR")

            def _save():
                from boss_career_ops.boss.auth.token_store import TokenStore
                store = TokenStore()
                encrypted = store.fernet.encrypt(api_key.encode()).decode()
                config = {"provider": provider, "api_key_encrypted": encrypted}
                ai_config_file = BCO_HOME / "ai_config.yml"
                ai_config_file.parent.mkdir(parents=True, exist_ok=True)
                ai_config_file.write_text(
                    yaml.dump(config, allow_unicode=True), encoding="utf-8"
                )
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
            if not security_id:
                return _err("security_id 不能为空", "VALIDATION_ERROR")

            def _fetch():
                messages = agent_tools.get_chat_messages(security_id)
                job = None
                if job_id:
                    job = agent_tools.get_job_with_ai_result(job_id)
                return messages, job

            messages, job = await asyncio.to_thread(_fetch)
            return _ok({"suggestions": [], "messages_count": len(messages), "has_job": job is not None})
        except Exception as e:
            logger.error("AI 回复建议失败: %s", e)
            return _err(str(e))

    @app.get("/")
    async def serve_index():
        if (STATIC_DIR / "index.html").exists():
            return FileResponse(STATIC_DIR / "index.html")
        return _ok({"message": "Boss Career Ops API"})

    if STATIC_DIR.exists():
        app.mount("/", StaticFiles(directory=str(STATIC_DIR)), name="static")
