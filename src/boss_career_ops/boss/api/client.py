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
RISK_CONTROL_KEYWORDS = {"环境存在异常", "访问行为异常", "异常", "风控", "risk"}

# 需要降级到浏览器通道的端点（高风险操作）
BROWSER_FALLBACK_ENDPOINTS = {"job_detail", "recommend", "user_info"}

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

    def _get_cookies(self) -> dict[str, str]:
        tokens = self._token_store.load()
        if not tokens:
            return {}
        return {k: v for k, v in tokens.items() if isinstance(v, str)}

    def _gaussian_delay(self):
        rl = self._thresholds.rate_limit
        mean = (rl.request_delay_min + rl.request_delay_max) / 2
        std = (rl.request_delay_max - rl.request_delay_min) / 4
        delay = max(rl.request_delay_min, random.gauss(mean, std))
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

    def _build_headers(self) -> dict[str, str]:
        headers = dict(DEFAULT_HEADERS)
        tokens = self._token_store.load()
        if tokens:
            if "zp_token" in tokens:
                headers["Zp-Token"] = tokens["zp_token"]
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

    def _inject_stoken(self, params: dict | None) -> dict:
        if params is None:
            params = {}
        tokens = self._token_store.load()
        if tokens:
            stoken = tokens.get("__zp_stoken__", "")
            if stoken:
                params["__zp_stoken__"] = stoken
        return params

    def _exponential_backoff_delay(self, attempt: int) -> float:
        rl = self._thresholds.rate_limit
        delay = rl.retry_base_delay * (2 ** attempt)
        delay = min(delay, rl.retry_max_delay)
        jitter = random.uniform(0, delay * 0.3)
        return delay + jitter

    def request(self, endpoint_name: str, params: dict | None = None, json_data: dict | None = None) -> dict:
        ep = self._endpoints.get(endpoint_name)
        if ep is None:
            raise ValueError(f"未知端点: {endpoint_name}")
        rl = self._thresholds.rate_limit
        max_attempts = rl.retry_max_attempts
        if ep.method == "GET":
            params = self._inject_stoken(params)
        for attempt in range(max_attempts):
            self._gaussian_delay()
            url = self._endpoints.url(endpoint_name)
            cookies = self._get_cookies()
            headers = self._build_headers()
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
                backoff = self._exponential_backoff_delay(attempt)
                logger.warning("API 限流 (尝试 %d/%d): code=%s, 退避 %.1f 秒", attempt + 1, max_attempts, result.get("code"), backoff)
                time.sleep(backoff)
                continue
            if self._is_risk_blocked(result):
                logger.warning("风控拦截: %s", result.get("message", ""))
                result["_risk_blocked"] = True
            return result
        return {"ok": False, "code": "RATE_LIMITED", "message": "重试次数耗尽，请求仍被限流"}

    def get(self, endpoint_name: str, params: dict | None = None) -> dict:
        return self.request(endpoint_name, params=params)

    def post(self, endpoint_name: str, json_data: dict | None = None, params: dict | None = None) -> dict:
        return self.request(endpoint_name, params=params, json_data=json_data)
