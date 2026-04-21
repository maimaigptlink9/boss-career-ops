import asyncio

from boss_career_ops.boss.browser_client import BrowserClient
from boss_career_ops.bridge.client import BridgeClient
from boss_career_ops.hooks.manager import HookManager
from boss_career_ops.display.error_codes import ErrorCode
from boss_career_ops.display.output import output_json, output_error
from boss_career_ops.display.logger import get_logger
from boss_career_ops.pipeline.manager import PipelineManager
from boss_career_ops.pipeline.stages import Stage

logger = get_logger(__name__)

JOB_DETAIL_URL = "https://www.zhipin.com/job_detail/{job_id}.html"
JOB_GEEK_URL = "https://www.zhipin.com/web/geek/job?query=&city="


async def _apply_via_browser(security_id: str, job_id: str) -> dict:
    hooks = HookManager()
    before_result = await hooks.execute_before("apply_before", {"security_id": security_id, "job_id": job_id})
    if before_result.action.value == "veto":
        return {"ok": False, "message": f"Hook veto: {before_result.reason}", "code": ErrorCode.HOOK_VETO}
    bridge = BridgeClient()
    if bridge.is_available():
        result = _apply_via_bridge(bridge, security_id, job_id)
        if result.get("ok"):
            await hooks.execute_after("apply_after", {"security_id": security_id, "job_id": job_id, "result": "success"})
            return result
        logger.warning("Bridge 投递失败: %s，尝试浏览器通道", result.get("message"))
    browser = BrowserClient()
    if browser.ensure_connected():
        result = _apply_via_patchright(browser, security_id, job_id)
        if result.get("ok"):
            await hooks.execute_after("apply_after", {"security_id": security_id, "job_id": job_id, "result": "success"})
            return result
    return {"ok": False, "message": "浏览器通道全部不可用，无法投递", "code": ErrorCode.APPLY_BROWSER_ERROR}


def _apply_via_bridge(bridge: BridgeClient, security_id: str, job_id: str) -> dict:
    try:
        url = JOB_DETAIL_URL.format(job_id=job_id)
        nav = bridge.navigate(url)
        if not nav.ok:
            return {"ok": False, "message": f"Bridge 导航失败: {nav.error}"}
        import time
        time.sleep(2)
        apply_btn = bridge.click(".btn-apply") or bridge.click("[ka='job-apply']")
        if not apply_btn.ok:
            chat_btn = bridge.click(".btn-startchat") or bridge.click("[ka='job-chat']")
            if chat_btn.ok:
                return {"ok": True, "message": "投递成功（通过沟通按钮）"}
            return {"ok": False, "message": "未找到投递按钮"}
        return {"ok": True, "message": "投递成功"}
    except Exception as e:
        return {"ok": False, "message": str(e)}


def _apply_via_patchright(browser: BrowserClient, security_id: str, job_id: str) -> dict:
    page = None
    try:
        page = browser.get_page()
        url = JOB_DETAIL_URL.format(job_id=job_id)
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)
        apply_btn = page.query_selector(".btn-apply") or page.query_selector("[ka='job-apply']")
        if apply_btn:
            apply_btn.click()
            page.wait_for_timeout(2000)
            dialog_confirm = page.query_selector(".dialog-btn-confirm") or page.query_selector(".btn-confirm")
            if dialog_confirm:
                dialog_confirm.click()
                page.wait_for_timeout(1000)
            logger.info("浏览器通道投递成功: %s", job_id)
            return {"ok": True, "message": "投递成功（浏览器通道）"}
        chat_btn = page.query_selector(".btn-startchat") or page.query_selector("[ka='job-chat']")
        if chat_btn:
            chat_btn.click()
            page.wait_for_timeout(2000)
            logger.info("浏览器通道沟通成功: %s", job_id)
            return {"ok": True, "message": "投递成功（通过沟通按钮）"}
        return {"ok": False, "message": "未找到投递或沟通按钮", "code": ErrorCode.APPLY_BROWSER_ERROR}
    except Exception as e:
        return {"ok": False, "message": f"浏览器投递失败: {e}", "code": ErrorCode.APPLY_BROWSER_ERROR}
    finally:
        if page:
            try:
                page.close()
            except Exception:
                pass


def _upload_resume_before_apply(job_id: str) -> dict:
    from boss_career_ops.resume.generator import ResumeGenerator
    from boss_career_ops.resume.pdf_engine import PDFEngine
    from boss_career_ops.resume.keywords import KeywordInjector
    from boss_career_ops.resume.upload import ResumeUploader
    from boss_career_ops.boss.api.client import BossClient
    from boss_career_ops.config.settings import RESUMES_DIR, Settings

    client = BossClient()
    resp = client.get("job_detail", params={"securityId": job_id})
    if resp.get("code") != 0:
        return {"ok": False, "message": "获取职位详情失败"}
    job = resp.get("zpData", {}).get("jobInfo", {})
    generator = ResumeGenerator()
    resume_md = generator.generate(job)
    injector = KeywordInjector()
    jd_text = generator._extract_jd_text(job)
    keywords = injector.extract_from_jd(jd_text)
    resume_md = injector.inject(resume_md, keywords)
    output_path = RESUMES_DIR / f"{job_id}.pdf"
    engine = PDFEngine()
    engine.generate(resume_md, output_path)
    settings = Settings()
    name = getattr(settings.profile, "name", "") or "未命名"
    job_name = job.get("jobName", "") or "未命名"
    display_name = f"{name}_{job_name}.pdf"
    uploader = ResumeUploader()
    return uploader.upload(output_path, display_name)


def run_apply(security_id: str, job_id: str, resume_job_id: str = ""):
    if resume_job_id:
        upload_result = _upload_resume_before_apply(resume_job_id)
        if not upload_result.get("ok"):
            output_error(
                command="apply",
                message=f"简历上传失败: {upload_result.get('message', '')}",
                code=upload_result.get("code", "RESUME_UPLOAD_ERROR"),
                hints={"next_actions": ["bco resume <jid> --format pdf --upload"]},
            )
            return
    result = asyncio.run(_apply_via_browser(security_id, job_id))
    if result.get("ok"):
        try:
            pm = PipelineManager()
            with pm:
                pm.upsert_job(job_id=job_id, security_id=security_id)
                pm.update_stage(job_id, Stage.APPLIED)
        except Exception as e:
            logger.warning("投递阶段推进写入 Pipeline 失败: %s", e)
        output_json(
            command="apply",
            data=result,
            hints={"next_actions": ["bco pipeline", "bco follow-up"]},
        )
    else:
        output_error(
            command="apply",
            message=result.get("message", "投递失败"),
            code=result.get("code", "APPLY_ERROR"),
            hints={"next_actions": ["bco status", "bco login"]},
        )
