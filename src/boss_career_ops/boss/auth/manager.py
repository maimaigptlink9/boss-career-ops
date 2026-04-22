import json
import os
import subprocess
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
        self._profile = ""

    def login(self, *, profile: str = "") -> dict:
        self._profile = profile
        print("登录方式将按优先级依次尝试：", flush=True)
        print("  1. Bridge Cookie — 通过 Chrome 扩展读取已登录的 Cookie（推荐）", flush=True)
        print("  2. CDP — 连接远程调试模式的 Chrome 读取 Cookie", flush=True)
        print("  3. Patchright — 弹出独立浏览器窗口手动登录", flush=True)
        print(flush=True)
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

        print("[Bridge] 正在连接 Bridge Daemon...", flush=True)
        bridge = BridgeClient()

        if not bridge.is_available():
            print("[Bridge] Daemon 未运行，正在启动...", flush=True)
            try:
                t = threading.Thread(daemon=True, target=start_daemon)
                t.start()
                for i in range(10):
                    time.sleep(1)
                    if bridge.is_available():
                        break
                else:
                    logger.info("Bridge Daemon 启动超时（10秒）")
                    print("[Bridge] Daemon 启动超时，跳过", flush=True)
                    return {"ok": False, "method": "bridge_cookie"}
            except Exception:
                logger.info("Bridge Daemon 启动失败")
                print("[Bridge] Daemon 启动超时，跳过", flush=True)
                return {"ok": False, "method": "bridge_cookie"}

        print("[Bridge] Daemon 已就绪", flush=True)

        print("[Bridge] 等待 Chrome 扩展连接...", flush=True)
        for i in range(30):
            try:
                with httpx.Client(proxy=None) as client:
                    resp = client.get(f"{bridge._bridge_url}/status", timeout=5.0)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("extensions_connected", 0) > 0:
                        break
            except Exception:
                pass
            if (i + 1) % 10 == 0 and i < 29:
                print(f"[Bridge] 等待 Chrome 扩展连接... ({i + 1}s/30s)", flush=True)
            time.sleep(1)
        else:
            print("[Bridge] 等待 Chrome 扩展连接超时（30秒）", flush=True)
            print("[Bridge] 请检查以下事项：", flush=True)
            print("  1. 打开 chrome://extensions/，确认「Boss-Career-Ops Bridge」扩展已启用", flush=True)
            print("  2. 确认扩展的 host_permissions 包含 http://127.0.0.1:18765/*", flush=True)
            print("  3. 点击扩展详情 → Service Worker，查看控制台是否有连接错误", flush=True)
            print("  4. 修改 manifest.json 后需在 chrome://extensions/ 点击刷新按钮重新加载", flush=True)
            return {"ok": False, "method": "bridge_cookie"}

        print("[Bridge] 正在获取 Cookie...", flush=True)
        try:
            cookies = bridge.get_cookies()
            if not cookies:
                logger.info("Bridge 返回空 Cookie")
                print("[Bridge] Bridge 返回空 Cookie", flush=True)
                print("[Bridge] 请确认：", flush=True)
                print("  1. Chrome 中已登录 BOSS 直聘（打开 zhipin.com 检查登录状态）", flush=True)
                print("  2. 扩展的 cookies 权限已授予（chrome://extensions/ → 扩展详情）", flush=True)
                return {"ok": False, "method": "bridge_cookie"}
            if _check_login_cookies(cookies):
                has_wt2 = "wt2" in cookies
                has_stoken = any(cookies.get(a) for a in STOKEN_ALIASES)
                print(f"[Bridge] Cookie 有效 (wt2: {'✓' if has_wt2 else '✗'}, stoken: {'✓' if has_stoken else '✗'})", flush=True)
                self._token_store.save(cookies)
                return {"ok": True, "method": "bridge_cookie", "message": "Bridge Cookie 登录成功"}
            missing = []
            if not cookies.get("wt2"):
                missing.append("wt2")
            if not any(cookies.get(a) for a in STOKEN_ALIASES):
                missing.append("stoken")
            print(f"[Bridge] Cookie 不完整，缺少: {', '.join(missing)}", flush=True)
            logger.info("Bridge Cookie 不包含有效登录态")
        except Exception:
            logger.info("Bridge Cookie 获取失败")
            print("[Bridge] Cookie 获取失败", flush=True)
        return {"ok": False, "method": "bridge_cookie"}

    def _login_cdp(self) -> dict:
        print("[CDP] 检测远程调试端口...", flush=True)
        cdp_url = self._cdp_url or self._detect_cdp()
        if not cdp_url:
            cdp_url = self._auto_launch_cdp()
            if not cdp_url:
                return {"ok": False, "method": "cdp"}
        try:
            from patchright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(cdp_url)
                context = browser.contexts[0]
                cookies = _extract_cookies_from_list(context.cookies())
                found_names = set(cookies.keys()) & LOGIN_COOKIE_NAMES
                logger.info("CDP: 直接读取到 %d 个 Cookie，登录相关: %s",
                            len(cookies), found_names or "无")
                if _check_login_cookies(cookies):
                    self._token_store.save(cookies)
                    print("[CDP] Cookie 有效，登录成功", flush=True)
                    return {"ok": True, "method": "cdp", "message": "CDP 登录成功"}
                logger.info("CDP 直接读取 Cookie 无有效登录态，尝试导航刷新...")
                page = context.pages[0] if context.pages else context.new_page()
                from boss_career_ops.boss.browser_client import ANTI_REDIRECT_JS
                page.add_init_script(ANTI_REDIRECT_JS)
                try:
                    page.goto("https://www.zhipin.com", wait_until="domcontentloaded", timeout=15000)
                    page.wait_for_timeout(3000)
                except Exception as nav_err:
                    logger.info("CDP 导航超时，尝试直接读取当前页面 Cookie: %s", nav_err)
                cookies = _extract_cookies_from_list(context.cookies())
                found_names = set(cookies.keys()) & LOGIN_COOKIE_NAMES
                logger.info("CDP: 导航后找到 %d 个 Cookie，登录相关: %s",
                            len(cookies), found_names or "无")
                if _check_login_cookies(cookies):
                    self._token_store.save(cookies)
                    print("[CDP] Cookie 有效，登录成功", flush=True)
                    return {"ok": True, "method": "cdp", "message": "CDP 登录成功"}
                logger.info("CDP 连接成功但未找到有效登录态（可能浏览器未登录 BOSS）")
                print("[CDP] Chrome 已连接但未检测到 BOSS 直聘登录态", flush=True)
                print("[CDP] 请在 Chrome 窗口中登录 BOSS 直聘，然后重新运行 bco login", flush=True)
        except Exception as e:
            logger.info("CDP 登录失败: %s", e)
        return {"ok": False, "method": "cdp"}

    @staticmethod
    def _find_chrome_profiles() -> list[dict]:
        user_data = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
        local_state_path = os.path.join(user_data, "Local State")
        if not os.path.exists(local_state_path):
            return []
        try:
            with open(local_state_path, "r", encoding="utf-8") as f:
                state = json.load(f)
            profiles = []
            for key, info in state.get("profile", {}).get("info_cache", {}).items():
                profiles.append({
                    "directory": key,
                    "name": info.get("name", key),
                    "gaia_name": info.get("gaia_name", ""),
                    "user_name": info.get("user_name", ""),
                    "user_data_dir": user_data,
                })
            return profiles
        except Exception:
            return []

    @staticmethod
    def _find_chrome_exe() -> str | None:
        candidates = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return None

    @staticmethod
    def _is_chrome_running() -> bool:
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq chrome.exe"],
                capture_output=True, text=True, timeout=5,
            )
            return "chrome.exe" in result.stdout
        except Exception:
            return False

    def _auto_launch_cdp(self) -> str | None:
        chrome_exe = self._find_chrome_exe()
        if not chrome_exe:
            print("[CDP] 未找到 Chrome 安装路径", flush=True)
            return None

        if self._is_chrome_running():
            print("[CDP] Chrome 正在运行，无法启动调试模式", flush=True)
            print("[CDP] 请先关闭所有 Chrome 窗口（包括系统托盘），然后重新运行 bco login", flush=True)
            return None

        profiles = self._find_chrome_profiles()
        if not profiles:
            print("[CDP] 未检测到 Chrome 配置文件", flush=True)
            return None

        profile_dir = "Default"
        if self._profile:
            matched = [p for p in profiles if p["directory"] == self._profile]
            if matched:
                profile_dir = matched[0]["directory"]
                print(f"[CDP] 使用指定配置文件: {matched[0]['name']} ({profile_dir})", flush=True)
            else:
                print(f"[CDP] 未找到配置文件 '{self._profile}'，可用: {', '.join(p['directory'] for p in profiles)}", flush=True)
                return None
        elif len(profiles) == 1:
            profile_dir = profiles[0]["directory"]
            print(f"[CDP] 检测到配置文件: {profiles[0]['name']}", flush=True)
        else:
            print(f"[CDP] 检测到 {len(profiles)} 个配置文件:", flush=True)
            for p in profiles:
                detail = p["name"]
                if p["gaia_name"]:
                    detail += f" ({p['gaia_name']}, {p['user_name']})"
                print(f"  - {p['directory']}: {detail}", flush=True)
            profile_dir = profiles[0]["directory"]
            print(f"[CDP] 自动选择: {profiles[0]['name']}（可通过 --profile 指定其他配置）", flush=True)

        user_data_dir = profiles[0]["user_data_dir"]
        print(f"[CDP] 正在启动 Chrome（配置: {profile_dir}）...", flush=True)
        try:
            subprocess.Popen([
                chrome_exe,
                f"--remote-debugging-port={CDP_CANDIDATE_PORTS[0]}",
                f"--user-data-dir={user_data_dir}",
                f"--profile-directory={profile_dir}",
            ])
        except Exception as e:
            logger.info("Chrome 启动失败: %s", e)
            print(f"[CDP] Chrome 启动失败: {e}", flush=True)
            return None

        print("[CDP] 等待 Chrome 启动...", flush=True)
        for i in range(15):
            time.sleep(1)
            cdp_url = self._detect_cdp()
            if cdp_url:
                print("[CDP] Chrome 已就绪", flush=True)
                return cdp_url
            if (i + 1) % 5 == 0:
                print(f"[CDP] 等待 Chrome 启动... ({i + 1}s/15s)", flush=True)

        print("[CDP] Chrome 启动超时", flush=True)
        return None

    def _detect_cdp(self) -> str | None:
        for port in CDP_CANDIDATE_PORTS:
            url = f"http://127.0.0.1:{port}"
            try:
                with httpx.Client(proxy=None) as client:
                    resp = client.get(f"{url}/json/version", timeout=2.0)
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
        # 先尝试通过 Bridge 实时获取 Cookie 校验
        try:
            from boss_career_ops.bridge.client import BridgeClient
            bridge = BridgeClient()
            if bridge.is_available():
                cookies = bridge.get_cookies()
                if cookies:
                    missing = []
                    if not cookies.get("wt2"):
                        missing.append("wt2")
                    has_stoken = any(cookies.get(a) for a in ["stoken", "__zp_stoken__"])
                    if not has_stoken:
                        missing.append("stoken")
                    if not missing:
                        return {"ok": True, "missing": [], "message": "在线，Cookie 实时有效"}
                    return {"ok": False, "missing": missing, "message": f"在线，但 Cookie 不完整，缺少: {', '.join(missing)}"}
                return {"ok": False, "missing": ["all"], "message": "在线，但 Bridge 返回空 Cookie"}
        except Exception:
            pass
        # Bridge 不可用，降级到 TokenStore
        quality = self._token_store.check_quality()
        if quality.get("ok"):
            return {"ok": True, "missing": [], "message": "离线，Cookie 存在但时效未知"}
        if not quality.get("missing") or "all" in quality.get("missing", []):
            return {"ok": False, "missing": quality.get("missing", []), "message": "离线，无 Token，请运行 bco login"}
        return {"ok": False, "missing": quality.get("missing", []), "message": f"离线，Token 不完整，缺少: {', '.join(quality['missing'])}"}
