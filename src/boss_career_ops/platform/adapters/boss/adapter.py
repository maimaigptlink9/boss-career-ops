import asyncio
import shutil
import tempfile
from pathlib import Path
from typing import Any

from boss_career_ops.boss.api.client import BossClient
from boss_career_ops.boss.auth.manager import AuthManager
from boss_career_ops.boss.browser_client import BrowserClient, ANTI_REDIRECT_JS
from boss_career_ops.boss.search_filters import (
    build_search_params as _boss_build_search_params,
    filter_by_welfare as _boss_filter_by_welfare,
    get_city_code as _boss_get_city_code,
)
from boss_career_ops.bridge.client import BridgeClient
from boss_career_ops.display.error_codes import ErrorCode
from boss_career_ops.display.logger import get_logger
from boss_career_ops.hooks.manager import HookManager
from boss_career_ops.platform.adapter import PlatformAdapter, PlatformBrowser
from boss_career_ops.platform.field_mapper import BossFieldMapper
from boss_career_ops.platform.models import (
    AuthStatus,
    ChatMessage,
    Contact,
    Job,
    OperationResult,
)
from boss_career_ops.resume.upload import ResumeUploader

logger = get_logger(__name__)

JOB_DETAIL_URL = "https://www.zhipin.com/job_detail/{job_id}.html"
RESUME_MANAGE_URL = "https://www.zhipin.com/web/geek/resume"


class BossBrowserAdapter(PlatformBrowser):

    def __init__(self, cdp_url: str | None = None, bridge_url: str | None = None):
        self._browser = BrowserClient(cdp_url=cdp_url, bridge_url=bridge_url)

    def ensure_connected(self) -> bool:
        return self._browser.ensure_connected()

    def get_page(self):
        return self._browser.get_page()

    def add_cookies(self, cookies: list[dict]) -> None:
        self._browser.add_cookies(cookies)

    def close(self) -> None:
        self._browser.close()

    def get_anti_redirect_js(self) -> str:
        return ANTI_REDIRECT_JS

    @property
    def inner(self) -> BrowserClient:
        return self._browser


class BossAdapter(PlatformAdapter):

    def __init__(self, cdp_url: str | None = None, bridge_url: str | None = None):
        self._client = BossClient(cdp_url=cdp_url)
        self._auth = AuthManager(cdp_url=cdp_url)
        self._mapper = BossFieldMapper()
        self._browser = BossBrowserAdapter(cdp_url=cdp_url, bridge_url=bridge_url)

    def search(self, params: dict[str, Any]) -> list[Job]:
        resp = self._client.post("search", params=params)
        if resp.get("_risk_blocked"):
            return self._search_via_browser(params)
        if resp.get("code") != 0:
            logger.error("搜索失败: code=%s, message=%s", resp.get("code"), resp.get("message"))
            return []
        job_list = resp.get("zpData", {}).get("jobList", [])
        return [self._mapper.map_job(j) for j in job_list]

    def _search_via_browser(self, params: dict[str, Any]) -> list[Job]:
        try:
            browser = self._browser
            browser.ensure_connected()
            tokens = self._client._get_cookies()
            if not tokens:
                return []
            cookies_for_browser = []
            for name, value in tokens.items():
                if isinstance(value, str) and value:
                    cookies_for_browser.append({
                        "name": name,
                        "value": value,
                        "domain": ".zhipin.com",
                        "path": "/",
                    })
            page_obj = browser.get_page()
            page_obj.goto("https://www.zhipin.com", wait_until="domcontentloaded")
            page_obj.wait_for_timeout(1000)
            browser.add_cookies(cookies_for_browser)
            keyword = params.get("query", "")
            city = params.get("city", "")
            page_num = params.get("page", 1)
            page_size = params.get("pageSize", 15)
            search_url = f"https://www.zhipin.com/web/geek/job?query={keyword}"
            if city:
                search_url += f"&city={city}"
            if page_num and int(page_num) > 1:
                search_url += f"&page={page_num}"
            if page_size:
                search_url += f"&pageSize={page_size}"
            api_response = {}

            def _handle_response(response):
                if "search/joblist.json" in response.url:
                    try:
                        data = response.json()
                        if data.get("code") == 0:
                            api_response["data"] = data
                    except Exception:
                        pass

            page_obj.on("response", _handle_response)
            try:
                page_obj.goto(search_url, wait_until="domcontentloaded", timeout=15000)
                page_obj.wait_for_timeout(5000)
            except Exception as e:
                logger.warning("浏览器搜索页面加载超时: %s", e)
            page_obj.close()
            result = api_response.get("data")
            if result and result.get("code") == 0:
                job_list = result.get("zpData", {}).get("jobList", [])
                return [self._mapper.map_job(j) for j in job_list]
        except Exception as e:
            logger.warning("浏览器通道搜索失败: %s", e)
        return []

    def get_job_detail(self, security_id: str) -> Job | None:
        resp = self._client.get("job_detail", params={"securityId": security_id})
        if resp.get("_risk_blocked"):
            logger.warning("获取职位详情被风控拦截，尝试浏览器通道降级: %s", security_id)
            return self._get_job_detail_via_browser(security_id)
        if resp.get("code") != 0:
            return None
        job_info = resp.get("zpData", {}).get("jobInfo", {})
        if not job_info:
            return None
        job_info["securityId"] = security_id
        return self._mapper.map_job(job_info)

    def _get_job_detail_via_browser(self, security_id: str) -> Job | None:
        try:
            browser = self._browser
            browser.ensure_connected()
            tokens = self._client._get_cookies()
            if not tokens:
                return None
            cookies_for_browser = []
            for name, value in tokens.items():
                if isinstance(value, str) and value:
                    cookies_for_browser.append({
                        "name": name,
                        "value": value,
                        "domain": ".zhipin.com",
                        "path": "/",
                    })
            page_obj = browser.get_page()
            page_obj.goto("https://www.zhipin.com", wait_until="domcontentloaded")
            page_obj.wait_for_timeout(1000)
            browser.add_cookies(cookies_for_browser)

            api_response = {}

            def _handle_response(response):
                if "job/detail.json" in response.url:
                    try:
                        data = response.json()
                        if data.get("code") == 0:
                            api_response["data"] = data
                    except Exception:
                        pass

            page_obj.on("response", _handle_response)
            try:
                detail_url = f"https://www.zhipin.com/web/geek/job?query="
                page_obj.goto(detail_url, wait_until="domcontentloaded", timeout=15000)
                page_obj.wait_for_timeout(3000)

                from boss_career_ops.pipeline.manager import PipelineManager
                job_id = ""
                try:
                    with PipelineManager() as pm:
                        jobs = pm.list_jobs()
                        for j in jobs:
                            if j.get("security_id") == security_id:
                                job_id = j.get("job_id", "")
                                break
                except Exception:
                    pass

                if job_id:
                    nav_url = JOB_DETAIL_URL.format(job_id=job_id)
                    page_obj.goto(nav_url, wait_until="domcontentloaded", timeout=15000)
                    page_obj.wait_for_timeout(5000)
                else:
                    page_obj.close()
                    logger.warning("无法获取 job_id，浏览器导航获取职位详情失败: %s", security_id[:20])
                    return None
            except Exception as e:
                logger.warning("浏览器职位详情页面加载超时: %s", e)
            page_obj.close()

            result = api_response.get("data")
            if result and result.get("code") == 0:
                job_info = result.get("zpData", {}).get("jobInfo", {})
                if job_info:
                    job_info["securityId"] = security_id
                    logger.info("浏览器通道获取职位详情成功 (导航+拦截): %s", security_id[:20])
                    return self._mapper.map_job(job_info)
            logger.warning("浏览器通道获取职位详情失败: 无有效响应")
        except Exception as e:
            logger.warning("浏览器通道获取职位详情失败: %s", e)
        return None

    def greet(self, security_id: str, job_id: str) -> OperationResult:
        hooks = HookManager()

        async def _do_greet():
            before_result = await hooks.execute_before("greet_before", {"security_id": security_id, "job_id": job_id})
            if before_result.action.value == "veto":
                return OperationResult(ok=False, message=f"Hook veto: {before_result.reason}", code=ErrorCode.HOOK_VETO)
            resp = self._client.post("greet", json_data={"securityId": security_id, "jobId": job_id})
            if resp.get("code") == 0:
                await hooks.execute_after("greet_after", {"security_id": security_id, "job_id": job_id, "result": "success"})
                return OperationResult(ok=True, message="打招呼成功")
            error_code = resp.get("code", "UNKNOWN")
            error_msg = resp.get("message", "打招呼失败")
            if error_code == 7:
                return OperationResult(ok=False, message="已打过招呼", code=ErrorCode.ALREADY_GREETED)
            if "limit" in str(error_msg).lower() or error_code == 10003:
                return OperationResult(ok=False, message="今日打招呼次数用完", code=ErrorCode.GREET_LIMIT)
            return OperationResult(ok=False, message=error_msg, code=str(error_code))

        return asyncio.run(_do_greet())

    def apply(self, security_id: str, job_id: str) -> OperationResult:
        hooks = HookManager()

        async def _do_apply():
            before_result = await hooks.execute_before("apply_before", {"security_id": security_id, "job_id": job_id})
            if before_result.action.value == "veto":
                return OperationResult(ok=False, message=f"Hook veto: {before_result.reason}", code=ErrorCode.HOOK_VETO)
            if self._browser.inner.is_bridge_available():
                bridge = BridgeClient()
                result = self._apply_via_bridge(bridge, security_id, job_id)
                if result.ok:
                    await hooks.execute_after("apply_after", {"security_id": security_id, "job_id": job_id, "result": "success"})
                    return result
                logger.warning("Bridge 投递失败: %s，尝试浏览器通道", result.message)
            browser = self._browser
            if browser.ensure_connected():
                result = self._apply_via_patchright(browser, security_id, job_id)
                if result.ok:
                    await hooks.execute_after("apply_after", {"security_id": security_id, "job_id": job_id, "result": "success"})
                    return result
            return OperationResult(ok=False, message="浏览器通道全部不可用，无法投递", code=ErrorCode.APPLY_BROWSER_ERROR)

        return asyncio.run(_do_apply())

    def _apply_via_bridge(self, bridge: BridgeClient, security_id: str, job_id: str) -> OperationResult:
        try:
            url = JOB_DETAIL_URL.format(job_id=job_id)
            nav = bridge.navigate(url)
            if not nav.ok:
                return OperationResult(ok=False, message=f"Bridge 导航失败: {nav.error}")
            import time
            time.sleep(2)
            apply_btn = bridge.click(".btn-apply") or bridge.click("[ka='job-apply']")
            if not apply_btn.ok:
                chat_btn = bridge.click(".btn-startchat") or bridge.click("[ka='job-chat']")
                if chat_btn.ok:
                    return OperationResult(ok=True, message="投递成功（通过沟通按钮）")
                return OperationResult(ok=False, message="未找到投递按钮")
            return OperationResult(ok=True, message="投递成功")
        except Exception as e:
            return OperationResult(ok=False, message=str(e))

    def _apply_via_patchright(self, browser: BossBrowserAdapter, security_id: str, job_id: str) -> OperationResult:
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
                return OperationResult(ok=True, message="投递成功（浏览器通道）")
            chat_btn = page.query_selector(".btn-startchat") or page.query_selector("[ka='job-chat']")
            if chat_btn:
                chat_btn.click()
                page.wait_for_timeout(2000)
                return OperationResult(ok=True, message="投递成功（通过沟通按钮）")
            return OperationResult(ok=False, message="未找到投递或沟通按钮", code=ErrorCode.APPLY_BROWSER_ERROR)
        except Exception as e:
            return OperationResult(ok=False, message=f"浏览器投递失败: {e}", code=ErrorCode.APPLY_BROWSER_ERROR)
        finally:
            if page:
                try:
                    page.close()
                except Exception:
                    pass

    def get_chat_list(self) -> list[Contact]:
        resp = self._client.get("chat_list")
        if resp.get("code") != 0:
            return []
        zp_data = resp.get("zpData", {})
        chat_list = zp_data.get("groupList", []) or zp_data.get("list", [])
        return [self._mapper.map_contact(c) for c in chat_list]

    def get_chat_messages(self, security_id: str) -> list[ChatMessage]:
        logger.warning("chat_messages HTTP API 已废弃，需迁移至 WebSocket 通道")
        resp = self._client.get("chat_messages", params={"securityId": security_id})
        if resp.get("code") != 0:
            return []
        messages = resp.get("zpData", {}).get("list", [])
        return [self._mapper.map_chat_message(m) for m in messages]

    def exchange_contact(self, security_id: str, contact_type: str) -> OperationResult:
        resp = self._client.post("exchange_contact", json_data={"securityId": security_id, "type": contact_type})
        if resp.get("code") == 0:
            return OperationResult(ok=True, message="交换成功", data={"security_id": security_id, "type": contact_type})
        return OperationResult(ok=False, message=resp.get("message", "交换失败"), code="EXCHANGE_ERROR")

    def mark_contact(self, security_id: str, tag: str) -> OperationResult:
        resp = self._client.post("mark_contact", json_data={"securityId": security_id, "tag": tag})
        if resp.get("code") == 0:
            return OperationResult(ok=True, message="标记成功", data={"security_id": security_id, "tag": tag})
        return OperationResult(ok=False, message=resp.get("message", "标记失败"), code="MARK_ERROR")

    def get_recommendations(self, params: dict[str, Any] | None = None) -> list[Job]:
        recommend_params = params or {}
        recommend_params.setdefault("tag", "5")
        recommend_params.setdefault("isActive", "true")
        resp = self._client.get("recommend_v2", params=recommend_params)
        if resp.get("code") != 0:
            return []
        zp_data = resp.get("zpData", {})
        job_list = zp_data.get("jobList", [])
        if not job_list:
            card_list = zp_data.get("cardList", [])
            if card_list:
                job_list = card_list
        return [self._mapper.map_job(j) for j in job_list]

    def upload_resume(self, pdf_path: str, display_name: str) -> OperationResult:
        uploader = ResumeUploader(browser=self._browser.inner)
        result = uploader.upload(Path(pdf_path), display_name)
        return OperationResult(
            ok=result.get("ok", False),
            message=result.get("message", ""),
            code=result.get("code", ""),
            data=result,
        )

    def login(self, *, profile: str = "") -> AuthStatus:
        result = self._auth.login(profile=profile)
        if result.get("ok"):
            return AuthStatus(ok=True, message=result.get("message", "登录成功"))
        return AuthStatus(ok=False, message=result.get("message", "登录失败"), missing=[])

    def check_auth_status(self) -> AuthStatus:
        quality = self._auth.check_status()
        if quality.get("ok"):
            return AuthStatus(ok=True, message=quality.get("message", "Token 有效"))
        return AuthStatus(
            ok=False,
            missing=quality.get("missing", []),
            message=quality.get("message", "Token 无效"),
        )

    def build_search_params(
        self,
        keyword: str,
        city: str = "",
        experience: str = "",
        education: str = "",
        job_type: str = "",
        scale: str = "",
        finance: str = "",
        page: int = 1,
        page_size: int = 15,
    ) -> dict[str, Any]:
        return _boss_build_search_params(keyword, city, experience, education, job_type, scale, finance, page, page_size)

    def get_city_code(self, city: str) -> str:
        return _boss_get_city_code(city)

    def filter_by_welfare(self, jobs: list[Job], welfare_keywords: str) -> list[Job]:
        raw_jobs = [j.raw_data for j in jobs if j.raw_data]
        filtered_raw = _boss_filter_by_welfare(raw_jobs, welfare_keywords)
        filtered_ids = {j.get("encryptJobId", "") for j in filtered_raw}
        return [j for j in jobs if j.job_id in filtered_ids]
