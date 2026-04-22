import threading
import time

import httpx

from boss_career_ops.boss.auth.token_store import TokenStore
from boss_career_ops.config.singleton import SingletonMeta
from boss_career_ops.display.error_codes import ErrorCode
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)

REQUIRED_LOGIN_COOKIES = {"wt2"}
STOKEN_ALIASES = ["stoken", "__zp_stoken__"]
LOGIN_COOKIE_NAMES = REQUIRED_LOGIN_COOKIES | set(STOKEN_ALIASES)
BOSS_LOGIN_URL = "https://www.zhipin.com/?ka=header-login"
CDP_CANDIDATE_PORTS = [9222, 9223, 9224, 9225]


def _check_login_cookies(cookies: dict[str, str]) -> bool:
    if not cookies.get("wt2"):
        return False
    for alias in STOKEN_ALIASES:
        if cookies.get(alias):
            return True
    return False


def _extract_cookies_from_list(cookies_list: list[dict]) -> dict[str, str]:
    return {c["name"]: c["value"] for c in cookies_list}


class AuthManager(metaclass=SingletonMeta):
    def __init__(self, cdp_url: str | None = None):
        self._token_store = TokenStore()
        self._cdp_url = cdp_url

    def login(self) -> dict:
        for level, method in enumerate([
            self._login_bridge_cookie,
            self._login_cdp,
            self._login_patchright,
        ], 1):
            logger.info("尝试登录级别 %d: %s", level, method.__name__)
            try:
                result = method()
                if result.get("ok"):
                    logger.info("登录成功（级别 %d）", level)
                    return result
            except Exception as e:
                logger.warning("登录级别 %d 失败: %s", level, e)
        return {"ok": False, "message": "所有登录方式均失败", "code": ErrorCode.LOGIN_FAILED}

    def _login_bridge_cookie(self) -> dict:
        try:
            from boss_career_ops.bridge.client import BridgeClient
            from boss_career_ops.bridge.daemon import start_daemon
        except ImportError:
            logger.info("Bridge 模块不可用，跳过 Bridge Cookie 登录")
            return {"ok": False, "method": "bridge_cookie"}

        bridge = BridgeClient()

        if not bridge.is_available():
            try:
                t = threading.Thread(daemon=True, target=start_daemon)
                t.start()
                for _ in range(10):
                    time.sleep(1)
                    if bridge.is_available():
                        break
                else:
                    logger.info("Bridge Daemon 启动超时（10秒）")
                    return {"ok": False, "method": "bridge_cookie"}
            except Exception:
                logger.info("Bridge Daemon 启动失败")
                return {"ok": False, "method": "bridge_cookie"}

        for _ in range(30):
            try:
                resp = httpx.get(f"{bridge._bridge_url}/status", timeout=5.0)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("extensions_connected", 0) > 0:
                        break
            except Exception:
                pass
            time.sleep(1)
        else:
            print("Bridge Daemon 已启动，但 Chrome 扩展未连接。")
            print("请安装 BOSS Career Ops 浏览器扩展并确保其已启用。")
            return {"ok": False, "method": "bridge_cookie"}

        try:
            cookies = bridge.get_cookies()
            if not cookies:
                logger.info("Bridge 返回空 Cookie")
                return {"ok": False, "method": "bridge_cookie"}
            if _check_login_cookies(cookies):
                self._token_store.save(cookies)
                return {"ok": True, "method": "bridge_cookie", "message": "Bridge Cookie 登录成功"}
            logger.info("Bridge Cookie 不包含有效登录态")
        except Exception:
            logger.info("Bridge Cookie 获取失败")
        return {"ok": False, "method": "bridge_cookie"}

    def _login_cdp(self) -> dict:
        cdp_url = self._cdp_url or self._detect_cdp()
        if not cdp_url:
            logger.info("未检测到 CDP 端口（9222-9225），跳过 CDP 登录")
            return {"ok": False, "method": "cdp"}
        try:
            from patchright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(cdp_url)
                context = browser.contexts[0]
                page = context.pages[0] if context.pages else context.new_page()
                from boss_career_ops.boss.browser_client import ANTI_REDIRECT_JS
                page.add_init_script(ANTI_REDIRECT_JS)
                page.goto("https://www.zhipin.com")
                page.wait_for_timeout(3000)
                cookies = _extract_cookies_from_list(context.cookies())
                found_names = set(cookies.keys()) & LOGIN_COOKIE_NAMES
                logger.info("CDP: 找到 %d 个 Cookie，登录相关: %s",
                            len(cookies), found_names or "无")
                if _check_login_cookies(cookies):
                    self._token_store.save(cookies)
                    return {"ok": True, "method": "cdp", "message": "CDP 登录成功"}
                logger.info("CDP 连接成功但未找到有效登录态（可能浏览器未登录 BOSS）")
        except Exception as e:
            logger.info("CDP 登录失败: %s", e)
        return {"ok": False, "method": "cdp"}

    def _detect_cdp(self) -> str | None:
        for port in CDP_CANDIDATE_PORTS:
            url = f"http://localhost:{port}"
            try:
                resp = httpx.get(f"{url}/json/version", timeout=2.0)
                if resp.status_code == 200:
                    logger.info("检测到 CDP 端口: %d", port)
                    return url
            except httpx.ConnectError:
                continue
            except Exception:
                continue
        logger.info("CDP 端口 9222-9225 均无响应。请确保: 1) 先关闭所有 Chrome 窗口 2) 再运行 chrome.exe --remote-debugging-port=9222")
        return None

    def _login_patchright(self) -> dict:
        try:
            from patchright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=False,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-first-run",
                        "--no-default-browser-check",
                    ],
                )
                try:
                    context = browser.new_context(
                        viewport={"width": 1280, "height": 800},
                        locale="zh-CN",
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                    )
                    page = context.new_page()
                    from boss_career_ops.boss.browser_client import ANTI_REDIRECT_JS
                    page.add_init_script(ANTI_REDIRECT_JS)
                    page.goto(BOSS_LOGIN_URL, wait_until="domcontentloaded")
                    current_url = page.url
                    logger.info("Patchright: 已打开登录页 %s", current_url)
                    print("\n请在弹出的浏览器窗口中完成登录操作（扫码或账号密码）...")
                    print("登录成功后将自动检测，无需其他操作。\n")
                    max_wait = 180
                    progress_interval = 10
                    last_log_time = -1
                    for i in range(max_wait):
                        page.wait_for_timeout(1000)
                        cookies = _extract_cookies_from_list(context.cookies())
                        if _check_login_cookies(cookies):
                            logger.info("检测到登录 Cookie（等待 %d 秒）", i + 1)
                            self._token_store.save(cookies)
                            return {"ok": True, "method": "patchright", "message": "浏览器登录成功"}
                        if (i + 1) % progress_interval == 0 and i + 1 != last_log_time:
                            last_log_time = i + 1
                            found_names = set(cookies.keys()) & LOGIN_COOKIE_NAMES
                            print(
                                f"[浏览器] 等待登录中... {i + 1}/{max_wait} 秒",
                                flush=True,
                            )
                            logger.info(
                                "Patchright: 已等待 %d/%d 秒，Cookie 名称: %s，登录相关: %s，当前 URL: %s",
                                i + 1, max_wait,
                                list(cookies.keys())[:10],
                                found_names or "无",
                                page.url,
                            )
                    logger.warning("等待 %d 秒后仍未检测到登录 Cookie", max_wait)
                    all_cookies = _extract_cookies_from_list(context.cookies())
                    logger.info("最终 Cookie 名称: %s", list(all_cookies.keys()))
                    logger.info("当前 URL: %s", page.url)
                    logger.info("页面标题: %s", page.title())
                    missing = LOGIN_COOKIE_NAMES - set(all_cookies.keys())
                    if missing:
                        logger.info("缺少登录关键 Cookie: %s", ", ".join(sorted(missing)))
                        if not any(a in all_cookies for a in STOKEN_ALIASES):
                            logger.info("可能原因: 1) 未完成登录 2) BOSS 反爬拦截 3) Cookie 名称已变更")
                finally:
                    browser.close()
        except ImportError:
            logger.info("patchright 未安装，跳过浏览器登录")
        except Exception as e:
            logger.info("patchright 登录失败: %s", e)
        return {"ok": False, "method": "patchright"}

    def check_status(self) -> dict:
        quality = self._token_store.check_quality()
        return quality
