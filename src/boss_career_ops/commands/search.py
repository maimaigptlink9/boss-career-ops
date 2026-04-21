import random
import time

from boss_career_ops.boss.api.client import BossClient
from boss_career_ops.boss.browser_client import BrowserClient
from boss_career_ops.boss.search_filters import build_search_params, filter_by_welfare
from boss_career_ops.cache.store import CacheStore
from boss_career_ops.config.thresholds import Thresholds
from boss_career_ops.display.error_codes import ErrorCode
from boss_career_ops.display.output import output_json, output_error
from boss_career_ops.display.logger import get_logger
from boss_career_ops.pipeline.manager import PipelineManager

logger = get_logger(__name__)


def _page_delay(thresholds: Thresholds):
    rl = thresholds.rate_limit
    mean = (rl.search_page_delay_min + rl.search_page_delay_max) / 2
    std = (rl.search_page_delay_max - rl.search_page_delay_min) / 4
    delay = max(rl.search_page_delay_min, random.gauss(mean, std))
    logger.info("翻页延迟 %.1f 秒", delay)
    time.sleep(delay)


def _search_via_browser(keyword: str, city: str, page: int, page_size: int) -> dict | None:
    try:
        browser = BrowserClient()
        browser.reset()
        from boss_career_ops.boss.auth.token_store import TokenStore
        token_store = TokenStore()
        tokens = token_store.load()
        if not tokens:
            logger.warning("无 Token，浏览器通道无法注入 Cookie")
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
        if not cookies_for_browser:
            logger.warning("无有效 Cookie 可注入")
            return None
        page_obj = browser.get_page()
        page_obj.goto("https://www.zhipin.com", wait_until="domcontentloaded")
        page_obj.wait_for_timeout(1000)
        browser.add_cookies(cookies_for_browser)
        logger.info("已注入 %d 个 Cookie 到浏览器", len(cookies_for_browser))

        from boss_career_ops.boss.search_filters import get_city_code
        city_code = get_city_code(city)
        search_url = f"https://www.zhipin.com/web/geek/job?query={keyword}"
        if city_code:
            search_url += f"&city={city_code}"

        api_response = {}

        def _handle_response(response):
            if "search/joblist.json" in response.url:
                try:
                    data = response.json()
                    api_response["data"] = data
                    logger.info("浏览器拦截到搜索 API 响应: code=%s", data.get("code"))
                except Exception as e:
                    logger.warning("解析搜索 API 响应失败: %s", e)

        page_obj.on("response", _handle_response)
        page_obj.goto(search_url, wait_until="networkidle")
        page_obj.wait_for_timeout(3000)
        logger.info("浏览器页面加载完成, 拦截到响应数=%d", len(api_response))

        result = api_response.get("data")
        if not result:
            logger.debug("未拦截到搜索 API 响应，当前 URL: %s", page_obj.url)

        page_obj.close()
        browser.close()

        if result and result.get("code") == 0:
            return result
        if result:
            return result
    except Exception as e:
        logger.warning("浏览器通道搜索失败: %s", e)
    return None


def run_search(keyword: str, city: str, welfare: str, page: int, limit: int, pages: int = 1, output: str | None = None):
    client = BossClient()
    thresholds = Thresholds()
    rl = thresholds.rate_limit
    if pages < 1:
        pages = 1
    max_pages = min(pages, rl.search_max_pages)
    all_jobs = []
    total = 0
    last_has_more = False
    for p in range(page, page + max_pages):
        params = build_search_params(keyword, city, page=p, page_size=limit)
        params["scene"] = "1"
        try:
            resp = client.get("search", params=params)
        except Exception as e:
            logger.error("搜索异常: %s", e)
            output_error(
                command="search",
                message=str(e),
                code=ErrorCode.SEARCH_ERROR,
                hints={"next_actions": ["bco status", "bco login"]},
                output=output,
            )
            return
        if resp.get("_risk_blocked"):
            logger.info("httpx 通道被风控拦截，尝试浏览器通道降级")
            browser_result = _search_via_browser(keyword, city, page, limit)
            if browser_result and browser_result.get("code") == 0:
                resp = browser_result
            else:
                output_error(
                    command="search",
                    message="搜索被风控拦截，浏览器通道也失败，请稍后重试或重新登录",
                    code="SEARCH_RISK_BLOCKED",
                    hints={"next_actions": ["bco login", "稍后重试", "降低搜索频率"]},
                    output=output,
                )
                return
        if resp.get("code") != 0:
            error_code = resp.get("code", "UNKNOWN")
            error_msg = resp.get("message", "搜索失败")
            if error_code == ErrorCode.RATE_LIMITED:
                output_error(
                    command="search",
                    message=f"搜索被限流: {error_msg}",
                    code="SEARCH_RATE_LIMITED",
                    hints={"next_actions": ["稍后重试", "降低搜索频率"]},
                    output=output,
                )
            else:
                output_error(
                    command="search",
                    message=error_msg,
                    code=ErrorCode.SEARCH_ERROR,
                    hints={"next_actions": ["bco status"]},
                    output=output,
                )
            return
        job_list = resp.get("zpData", {}).get("jobList", [])
        last_has_more = resp.get("zpData", {}).get("hasMore", False)
        total = resp.get("zpData", {}).get("totalCount", 0)
        if welfare:
            job_list = filter_by_welfare(job_list, welfare)
        all_jobs.extend(job_list)
        if not last_has_more:
            break
        if p < page + max_pages - 1:
            _page_delay(thresholds)
    with CacheStore() as cache:
        cache.set("search:last_result", all_jobs, ttl=thresholds.cache.search_ttl)
        cache.set("search:last_params", {"keyword": keyword, "city": city, "welfare": welfare}, ttl=thresholds.cache.search_ttl)
    try:
        pm = PipelineManager()
        with pm:
            pm.batch_add_jobs(all_jobs)
        logger.info("已将 %d 条搜索结果写入 Pipeline", len(all_jobs))
    except Exception as e:
        logger.warning("搜索结果写入 Pipeline 失败: %s", e)
    output_json(
        command="search",
        data=all_jobs,
        pagination={
            "page": page,
            "pages_fetched": min(max_pages, (page + max_pages) - page),
            "has_more": last_has_more,
            "total": total,
        },
        hints={"next_actions": ["bco evaluate --from-search", "bco detail <security_id>"]},
        output=output,
    )
