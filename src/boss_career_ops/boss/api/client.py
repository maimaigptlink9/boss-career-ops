import random
import time
from typing import Any

import httpx

from boss_career_ops.boss.api.endpoints import Endpoints
from boss_career_ops.boss.auth.token_store import TokenStore
from boss_career_ops.config.singleton import SingletonMeta
from boss_career_ops.config.thresholds import Thresholds
from boss_career_ops.display.error_codes import ErrorCode
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)

RATE_LIMITED_CODES = {429, 10003}
RATE_LIMITED_KEYWORDS = {"limit", "频繁", "too many", "rate limit"}
RISK_CONTROL_KEYWORDS = {"环境存在异常", "访问行为异常", "操作异常", "风控", "risk"}

# 需要降级到浏览器通道的端点（高风险操作）
BROWSER_FALLBACK_ENDPOINTS = {"job_detail", "recommend", "recommend_v2", "user_info"}

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.zhipin.com/web/geek/job?query=&city=",
    "Origin": "https://www.zhipin.com",
    "X-Requested-With": "XMLHttpRequest",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Ch-Ua": '"Chromium";v="131", "Not_A Brand";v="24", "Google Chrome";v="131"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
}


class BossClient(metaclass=SingletonMeta):
    def __init__(self, cdp_url: str | None = None):
        self._endpoints = Endpoints()
        self._token_store = TokenStore()
        self._thresholds = Thresholds()
        self._cdp_url = cdp_url
        self._last_request_time = 0.0
        self._burst_count = 0
        self._burst_window_start = 0.0
        self._rate_limit_count = 0

    def _get_cookies(self) -> dict[str, str]:
        try:
            from boss_career_ops.bridge.client import BridgeClient

            bridge = BridgeClient()
            if bridge.is_available():
                cookies = bridge.get_cookies()
                if cookies:
                    logger.debug("从 Bridge 获取实时 Cookie 成功")
                    try:
                        self._token_store.save(cookies)
                        logger.debug("Bridge Cookie 已回写 TokenStore")
                    except Exception:
                        logger.warning("Bridge Cookie 回写 TokenStore 失败")
                    return cookies
        except Exception:
            pass
        tokens = self._token_store.load()
        if not tokens:
            return {}
        return {k: v for k, v in tokens.items() if isinstance(v, str)}

    def _gaussian_delay(self):
        rl = self._thresholds.rate_limit
        mean = (rl.request_delay_min + rl.request_delay_max) / 2
        std = (rl.request_delay_max - rl.request_delay_min) / 4
        delay = max(rl.request_delay_min, random.gauss(mean, std))
        if self._rate_limit_count > 0:
            delay *= 2 ** self._rate_limit_count
            logger.debug("限流惩罚: 延迟翻倍至 %.1f 秒 (限流次数: %d)", delay, self._rate_limit_count)
        now = time.time()
        if now - self._last_request_time < rl.request_delay_min:
            self._burst_count += 1
            if self._burst_count > 5:
                delay *= rl.burst_penalty_multiplier
                logger.info("突发惩罚: 延迟 %.1f 秒", delay)
        else:
            self._burst_count = 0
        self._last_request_time = time.time()
        time.sleep(delay)

    def _build_headers(self, endpoint_name: str = "", params: dict | None = None, cookies: dict[str, str] | None = None) -> dict[str, str]:
        headers = dict(DEFAULT_HEADERS)
        if cookies is None:
            cookies = self._get_cookies()
        if endpoint_name == "search":
            query = ""
            if params and params.get("query"):
                import urllib.parse
                query = f"?{urllib.parse.urlencode({'query': params['query']})}"
            headers["Referer"] = f"https://www.zhipin.com/web/geek/job{query}"
        elif endpoint_name in ("recommend", "recommend_v2"):
            headers["Referer"] = "https://www.zhipin.com/web/geek/recommend"
        elif endpoint_name in ("job_detail",):
            headers["Referer"] = "https://www.zhipin.com/web/geek/job"
        elif endpoint_name in ("chat_list", "chat_messages"):
            headers["Referer"] = "https://www.zhipin.com/web/geek/chat"
        bst = cookies.get("bst", "")
        if bst:
            headers["zp_token"] = bst
        return headers

    def _is_rate_limited(self, status_code: int, resp_data: dict) -> bool:
        if status_code in RATE_LIMITED_CODES:
            return True
        if resp_data.get("code") in RATE_LIMITED_CODES:
            return True
        msg = str(resp_data.get("message", "")).lower()
        return any(kw in msg for kw in RATE_LIMITED_KEYWORDS)

    def _is_risk_blocked(self, resp_data: dict) -> bool:
        msg = str(resp_data.get("message", ""))
        return any(kw in msg for kw in RISK_CONTROL_KEYWORDS)

    def _inject_stoken(self, params: dict | None, cookies: dict[str, str] | None = None) -> dict:
        if params is None:
            params = {}
        if cookies is None:
            cookies = self._get_cookies()
        stoken = cookies.get("__zp_stoken__", "")
        if stoken:
            params["__zp_stoken__"] = stoken
        return params

    def _exponential_backoff_delay(self, attempt: int) -> float:
        rl = self._thresholds.rate_limit
        delay = rl.retry_base_delay * (2 ** attempt)
        delay = min(delay, rl.retry_max_delay)
        jitter = random.uniform(0, delay * 0.3)
        return delay + jitter

    def _request_via_browser(self, endpoint_name: str, params: dict | None = None) -> dict | None:
        if endpoint_name not in BROWSER_FALLBACK_ENDPOINTS:
            return None
        try:
            from boss_career_ops.boss.browser_client import BrowserClient

            browser = BrowserClient()
            tokens = self._get_cookies()
            if not tokens:
                logger.warning("无 Cookie，浏览器通道降级无法注入 Cookie")
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

            page_obj.goto("https://www.zhipin.com/web/geek/job?query=", wait_until="domcontentloaded", timeout=15000)
            page_obj.wait_for_timeout(3000)

            ep = self._endpoints.get(endpoint_name)
            api_path = ep.path if ep else ""

            if endpoint_name in ("job_detail", "recommend", "recommend_v2", "user_info"):
                query_parts = []
                if params:
                    for k, v in params.items():
                        query_parts.append(f"{k}={v}")
                query_str = "&".join(query_parts)
                fetch_url = f"{api_path}?{query_str}" if query_str else api_path

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
                page_obj.close()
                browser.close()

                if result and isinstance(result, dict):
                    if result.get("code") == 0:
                        logger.info("浏览器通道降级成功 (fetch): %s", endpoint_name)
                        return result
                    if "_fetch_error" in result:
                        logger.warning("浏览器 fetch 请求失败: %s", result["_fetch_error"])
                    else:
                        logger.warning("浏览器通道降级失败 (fetch): %s, code=%s", endpoint_name, result.get("code"))
                return None

            page_obj.close()
            browser.close()
            return None
        except Exception as e:
            logger.warning("浏览器通道降级异常: %s - %s", endpoint_name, e)
            return None

    def request(self, endpoint_name: str, params: dict | None = None, json_data: dict | None = None) -> dict:
        ep = self._endpoints.get(endpoint_name)
        if ep is None:
            raise ValueError(f"未知端点: {endpoint_name}")
        rl = self._thresholds.rate_limit
        max_attempts = rl.retry_max_attempts
        for attempt in range(max_attempts):
            self._gaussian_delay()
            cookies = self._get_cookies()
            if ep.method == "GET":
                params = self._inject_stoken(params, cookies=cookies)
            url = self._endpoints.url(endpoint_name)
            headers = self._build_headers(endpoint_name, params, cookies=cookies)
            try:
                with httpx.Client(follow_redirects=True, timeout=30.0) as client:
                    if ep.method == "GET":
                        resp = client.get(url, params=params, headers=headers, cookies=cookies)
                    else:
                        resp = client.post(url, params=params, json=json_data, headers=headers, cookies=cookies)
            except httpx.TransportError as e:
                logger.warning("请求传输错误 (尝试 %d/%d): %s", attempt + 1, max_attempts, e)
                if attempt < max_attempts - 1:
                    backoff = self._exponential_backoff_delay(attempt)
                    logger.info("传输错误退避 %.1f 秒后重试", backoff)
                    time.sleep(backoff)
                    continue
                return {"ok": False, "code": ErrorCode.NETWORK_ERROR, "message": str(e)}
            if resp.status_code != 200:
                try:
                    resp_data = resp.json()
                except Exception:
                    resp_data = {}
                if self._is_rate_limited(resp.status_code, resp_data) and attempt < max_attempts - 1:
                    self._rate_limit_count += 1
                    cooldown = min(60, 10 * (2 ** (self._rate_limit_count - 1)))
                    logger.warning("限流冷却: %d 秒 (第 %d 次限流)", cooldown, self._rate_limit_count)
                    time.sleep(cooldown)
                    backoff = self._exponential_backoff_delay(attempt)
                    logger.warning("限流检测 (尝试 %d/%d): HTTP %d, 退避 %.1f 秒", attempt + 1, max_attempts, resp.status_code, backoff)
                    time.sleep(backoff)
                    continue
                logger.error("请求失败: %s %s → %d", ep.method, url, resp.status_code)
                return {"ok": False, "code": resp.status_code, "message": f"HTTP {resp.status_code}"}
            try:
                result = resp.json()
            except Exception:
                return {"ok": False, "code": ErrorCode.PARSE_ERROR, "message": "响应解析失败"}
            if self._is_rate_limited(0, result) and attempt < max_attempts - 1:
                self._rate_limit_count += 1
                cooldown = min(60, 10 * (2 ** (self._rate_limit_count - 1)))
                logger.warning("限流冷却: %d 秒 (第 %d 次限流)", cooldown, self._rate_limit_count)
                time.sleep(cooldown)
                backoff = self._exponential_backoff_delay(attempt)
                logger.warning("API 限流 (尝试 %d/%d): code=%s, 退避 %.1f 秒", attempt + 1, max_attempts, result.get("code"), backoff)
                time.sleep(backoff)
                continue
            if self._is_risk_blocked(result):
                logger.warning("风控拦截: %s", result.get("message", ""))
                result["_risk_blocked"] = True
                if endpoint_name in BROWSER_FALLBACK_ENDPOINTS:
                    logger.info("风控拦截，尝试浏览器通道降级: %s", endpoint_name)
                    browser_result = self._request_via_browser(endpoint_name, params)
                    if browser_result and browser_result.get("code") == 0:
                        return browser_result
                    logger.warning("浏览器通道降级也失败: %s", endpoint_name)
            self._rate_limit_count = 0
            return result
        return {"ok": False, "code": "RATE_LIMITED", "message": "重试次数耗尽，请求仍被限流"}

    def get(self, endpoint_name: str, params: dict | None = None) -> dict:
        return self.request(endpoint_name, params=params)

    def post(self, endpoint_name: str, json_data: dict | None = None, params: dict | None = None) -> dict:
        return self.request(endpoint_name, params=params, json_data=json_data)
