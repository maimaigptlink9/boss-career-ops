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
        jobs = []
        for j in job_list:
            job = self._mapper.map_job(j)
            if j.get("lid"):
                job.raw_data["lid"] = j["lid"]
            jobs.append(job)
        return jobs

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
            import urllib.parse
            nav_params = {"query": keyword}
            if city:
                nav_params["city"] = city
            if page_num and int(page_num) > 1:
                nav_params["page"] = page_num
            if page_size:
                nav_params["pageSize"] = page_size
            for k in ("experience", "education", "jobType", "scale", "financeStage", "salary"):
                if params.get(k):
                    nav_params[k] = params[k]
            search_url = f"https://www.zhipin.com/web/geek/job?{urllib.parse.urlencode(nav_params)}"
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
                jobs = []
                for j in job_list:
                    job = self._mapper.map_job(j)
                    if j.get("lid"):
                        job.raw_data["lid"] = j["lid"]
                    jobs.append(job)
                return jobs
        except Exception as e:
            logger.warning("浏览器通道搜索失败: %s", e)
        return []

    def get_job_detail(self, job_id: str, security_id: str = "", lid: str = "") -> Job | None:
        resp = self._client.get("job_detail", params={"encryptJobId": job_id})
        if not resp.get("_risk_blocked") and resp.get("code") == 0:
            zp_data = resp.get("zpData", {})
            job_info = zp_data.get("jobInfo", {})
            if job_info:
                job_detail_text = zp_data.get("jobDetail", "")
                if job_detail_text:
                    job_info["jobDetail"] = job_detail_text
                job_info["securityId"] = security_id
                return self._mapper.map_job(job_info)

        if resp.get("_risk_blocked"):
            logger.warning("获取职位详情被风控拦截: %s", job_id)
        else:
            logger.warning("获取职位详情失败: code=%s, job_id=%s", resp.get("code"), job_id)

        if security_id:
            logger.info("尝试 job_card 降级通道: security_id=%s", security_id[:20])
            card_job = self.get_job_card(security_id, lid)
            if card_job is not None:
                card_job.raw_data["_card_fetched"] = True
                return card_job

        job = self._get_job_detail_via_browser(security_id, job_id=job_id)
        if job is None:
            return Job(raw_data={"_risk_blocked": True})
        job.raw_data["_browser_fetched"] = True
        return job

    def get_job_card(self, security_id: str, lid: str = "") -> Job | None:
        resp = self._client.get_job_card(security_id, lid)
        if resp.get("_risk_blocked"):
            logger.warning("获取职位卡片被风控拦截: %s", security_id)
            return None
        if resp.get("code") != 0:
            return None
        job_card = resp.get("zpData", {}).get("jobCard", {})
        if not job_card:
            return None
        job_card["securityId"] = security_id
        return self._mapper.map_job(job_card)

    def _get_job_detail_via_browser(self, security_id: str, job_id: str = "") -> Job | None:
        try:
            import urllib.parse

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

            # 方案 A: 先尝试 JS fetch（带 __zp_stoken__ 参数）
            stoken = tokens.get("__zp_stoken__", "")
            fetch_url = f"/wapi/zpgeek/job/detail.json?encryptJobId={urllib.parse.quote(security_id)}"
            if stoken:
                # stoken 可能已 URL 编码（含 %2B 等），需先解码再重新编码，避免双重编码
                decoded_stoken = urllib.parse.unquote(stoken)
                fetch_url += f"&__zp_stoken__={urllib.parse.quote(decoded_stoken, safe='')}"
            page_obj.goto(
                "https://www.zhipin.com/web/geek/job?query=",
                wait_until="domcontentloaded",
                timeout=15000,
            )
            page_obj.wait_for_timeout(3000)

            js_code = f"""
            async () => {{
                try {{
                    const resp = await fetch("{fetch_url}", {{
                        method: "GET",
                        credentials: "include",
                        headers: {{
                            "Accept": "application/json",
                        }},
                    }});
                    const data = await resp.json();
                    return data;
                }} catch (e) {{
                    return {{_fetch_error: e.message}};
                }}
            }}
            """
            result = page_obj.evaluate(js_code)

            if result and isinstance(result, dict) and result.get("code") == 0:
                job_info = result.get("zpData", {}).get("jobInfo", {})
                if job_info:
                    job_info["securityId"] = security_id
                    page_obj.close()
                    logger.info("浏览器通道获取职位详情成功 (fetch): %s", security_id[:20])
                    return self._mapper.map_job(job_info)

            # 方案 B: fetch 失败，降级为导航到详情页抓取 DOM
            # 用页面拦截方式：导航到搜索页，拦截详情 API 响应
            logger.info("fetch 未获取到 JD，尝试页面拦截方式: %s", security_id[:20])

            api_response = {}

            def _handle_detail_response(response):
                url = response.url
                if "job/detail.json" in url and security_id[:30] in url:
                    try:
                        data = response.json()
                        if data.get("code") == 0:
                            api_response["data"] = data
                    except Exception:
                        pass

            page_obj.on("response", _handle_detail_response)
            page_obj.goto(
                "https://www.zhipin.com/web/geek/job?query=",
                wait_until="domcontentloaded",
                timeout=15000,
            )
            page_obj.wait_for_timeout(3000)

            # 用 JS 直接调用详情 API（页面原生方式，带完整 cookie 和 token）
            js_detail_code = f"""
            async () => {{
                try {{
                    const resp = await fetch("/wapi/zpgeek/job/detail.json?encryptJobId={urllib.parse.quote(security_id)}", {{
                        method: "GET",
                        credentials: "include",
                        headers: {{
                            "Accept": "application/json",
                            "X-Requested-With": "XMLHttpRequest",
                        }},
                    }});
                    const data = await resp.json();
                    return data;
                }} catch (e) {{
                    return {{_fetch_error: e.message}};
                }}
            }}
            """
            detail_result = page_obj.evaluate(js_detail_code)
            page_obj.remove_listener("response", _handle_detail_response)

            # 检查拦截到的或 JS 调用返回的结果
            result_to_check = api_response.get("data") or detail_result
            if result_to_check and isinstance(result_to_check, dict) and result_to_check.get("code") == 0:
                job_info = result_to_check.get("zpData", {}).get("jobInfo", {})
                if job_info and job_info.get("postDescription"):
                    job_info["securityId"] = security_id
                    page_obj.close()
                    logger.info("浏览器通道获取职位详情成功 (intercept): %s", security_id[:20])
                    return self._mapper.map_job(job_info)

            # 方案 C: 最后降级 - 直接导航到 job_detail 页面抓取 DOM
            detail_url_id = job_id if job_id else security_id
            logger.info("拦截方式也失败，尝试直接导航到详情页: %s (id=%s)", security_id[:20], detail_url_id[:20])
            page_obj.goto(
                f"https://www.zhipin.com/job_detail/{urllib.parse.quote(detail_url_id, safe='')}.html",
                wait_until="domcontentloaded",
                timeout=15000,
            )
            page_obj.wait_for_timeout(5000)

            jd_text = page_obj.evaluate("""
            () => {
                const selectors = [
                    '.job-detail-section .job-sec-text',
                    '.job-detail .text',
                    '.job-sec-text',
                    '[class*="job-detail"] [class*="desc"]',
                    '.job-detail-bottom .text',
                ];
                for (const sel of selectors) {
                    const el = document.querySelector(sel);
                    if (el && el.innerText.trim().length > 20) return el.innerText.trim();
                }
                // 兜底: 找所有可能的 JD 容器
                const allDivs = document.querySelectorAll('div');
                for (const div of allDivs) {
                    const text = div.innerText.trim();
                    if (text.length > 100 && (text.includes('岗位职责') || text.includes('任职要求') || text.includes('工作内容') || text.includes('职位描述'))) {
                        return text;
                    }
                }
                return '';
            }
            """)

            page_obj.close()

            if jd_text:
                raw_data = {
                    "securityId": security_id,
                    "postDescription": jd_text,
                    "_browser_fetched": True,
                    "_dom_scraped": True,
                }
                logger.info("浏览器通道获取职位详情成功 (DOM): %s", security_id[:20])
                return self._mapper.map_job(raw_data)

            logger.warning("浏览器通道获取职位详情失败: fetch code=%s, DOM 无内容",
                           result.get("code") if isinstance(result, dict) else "unknown")
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
