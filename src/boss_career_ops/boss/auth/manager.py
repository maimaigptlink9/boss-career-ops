import ctypes
from typing import Any

import httpx

from boss_career_ops.boss.auth.token_store import TokenStore
from boss_career_ops.config.singleton import SingletonMeta
from boss_career_ops.display.error_codes import ErrorCode
from boss_career_ops.display.logger import get_logger
from boss_career_ops.display.output import output_json, output_error

logger = get_logger(__name__)

REQUIRED_LOGIN_COOKIES = {"wt2"}
STOKEN_ALIASES = ["stoken", "__zp_stoken__"]
LOGIN_COOKIE_NAMES = REQUIRED_LOGIN_COOKIES | set(STOKEN_ALIASES)
BOSS_LOGIN_URL = "https://www.zhipin.com/?ka=header-login"
CDP_CANDIDATE_PORTS = [9222, 9223, 9224, 9225]


def _is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _check_login_cookies(cookies: dict[str, str]) -> bool:
    if not cookies.get("wt2"):
        return False
    for alias in STOKEN_ALIASES:
        if cookies.get(alias):
            return True
    return False


def _extract_cookies_from_list(cookies_list: list[dict]) -> dict[str, str]:
    return {c["name"]: c["value"] for c in cookies_list}


def _parse_set_cookie(header_value: str) -> dict[str, str]:
    cookies = {}
    if not header_value:
        return cookies
    for part in header_value.split(","):
        part = part.strip()
        if "=" in part:
            name_val = part.split(";")[0].strip()
            if "=" in name_val:
                name, val = name_val.split("=", 1)
                cookies[name.strip()] = val.strip()
    return cookies


class AuthManager(metaclass=SingletonMeta):
    def __init__(self, cdp_url: str | None = None):
        self._token_store = TokenStore()
        self._cdp_url = cdp_url

    def login(self) -> dict:
        for level, method in enumerate([
            self._login_cookie_extract,
            self._login_cdp,
            self._login_qr_httpx,
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

    def _login_cookie_extract(self) -> dict:
        if not _is_admin():
            logger.info("Cookie 提取需要管理员权限，当前非管理员，跳过")
            return {"ok": False, "method": "cookie_extract"}
        try:
            import rookiepy
            cookies_list = rookiepy.chrome(domains=[".zhipin.com", "zhipin.com"])
            cookies = _extract_cookies_from_list(cookies_list)
            found_names = set(cookies.keys()) & LOGIN_COOKIE_NAMES
            logger.info("Cookie 提取: 找到 %d 个 zhipin.com Cookie，登录相关: %s",
                        len(cookies), found_names or "无")
            if _check_login_cookies(cookies):
                self._token_store.save(cookies)
                return {"ok": True, "method": "cookie_extract", "message": "Cookie 提取成功"}
            missing = LOGIN_COOKIE_NAMES - found_names
            logger.info("Cookie 中缺少登录关键字段: %s", missing)
        except ImportError:
            logger.info("rookiepy 未安装，跳过 Cookie 提取")
        except Exception as e:
            logger.info("Cookie 提取失败: %s", e)
        return {"ok": False, "method": "cookie_extract"}

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

    def _login_qr_httpx(self) -> dict:
        try:
            from boss_career_ops.boss.api.client import BossClient
            from boss_career_ops.boss.api.endpoints import Endpoints
            client = BossClient()
            endpoints = Endpoints()
            qr_resp = client.get("qr_code")
            qr_data = qr_resp.get("zpData", {}) or qr_resp.get("data", {})
            qr_url = qr_data.get("qr_url") or qr_data.get("url")
            token = qr_data.get("token") or qr_data.get("qr_token")
            if not qr_url:
                logger.info("QR httpx: 未获取到二维码链接")
                return {"ok": False, "method": "qr_httpx"}
            try:
                import qrcode
                qr = qrcode.QRCode(border=1)
                qr.add_data(qr_url)
                qr.make(fit=True)
                qr.print_ascii(invert=True)
            except ImportError:
                logger.info("qrcode 库未安装，输出链接: %s", qr_url)
                print(f"\n请使用 BOSS 直聘 APP 扫描以下链接登录:\n{qr_url}\n")
            print("\n请使用 BOSS 直聘 APP 扫描上方二维码登录\n")
            import time as _time
            for i in range(120):
                _time.sleep(1)
                scan_resp = client.get("qr_scan_result", params={"token": token})
                scan_data = scan_resp.get("zpData", {}) or scan_resp.get("data", {})
                scan_status = scan_data.get("status") or scan_data.get("scan_status")
                if scan_status == "scanned":
                    print("已扫码，请在手机确认登录...")
                elif scan_status == "confirmed":
                    cookies = scan_data.get("cookies", {})
                    if isinstance(cookies, dict) and _check_login_cookies(cookies):
                        self._token_store.save(cookies)
                        return {"ok": True, "method": "qr_httpx", "message": "QR 登录成功"}
                    set_cookie_headers = scan_resp.get("headers", {}).get("set-cookie", "")
                    if set_cookie_headers:
                        parsed = _parse_set_cookie(set_cookie_headers)
                        if _check_login_cookies(parsed):
                            self._token_store.save(parsed)
                            return {"ok": True, "method": "qr_httpx", "message": "QR 登录成功"}
                elif scan_status in ("expired", "canceled"):
                    return {"ok": False, "method": "qr_httpx", "message": f"二维码{scan_status}"}
                if (i + 1) % 30 == 0:
                    logger.info("QR httpx: 已等待 %d/120 秒", i + 1)
            logger.info("QR httpx: 等待超时")
        except ImportError:
            logger.info("qrcode 库未安装，跳过 QR httpx 登录")
        except Exception as e:
            logger.info("QR httpx 登录失败: %s", e)
        return {"ok": False, "method": "qr_httpx"}

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
                last_log_time = -1
                for i in range(max_wait):
                    page.wait_for_timeout(1000)
                    cookies = _extract_cookies_from_list(context.cookies())
                    if _check_login_cookies(cookies):
                        logger.info("检测到登录 Cookie（等待 %d 秒）", i + 1)
                        self._token_store.save(cookies)
                        browser.close()
                        return {"ok": True, "method": "patchright", "message": "浏览器登录成功"}
                    if (i + 1) % 30 == 0 and i + 1 != last_log_time:
                        last_log_time = i + 1
                        found_names = set(cookies.keys()) & LOGIN_COOKIE_NAMES
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
                browser.close()
        except ImportError:
            logger.info("patchright 未安装，跳过浏览器登录")
        except Exception as e:
            logger.info("patchright 登录失败: %s", e)
        return {"ok": False, "method": "patchright"}

    def check_status(self) -> dict:
        quality = self._token_store.check_quality()
        return quality
