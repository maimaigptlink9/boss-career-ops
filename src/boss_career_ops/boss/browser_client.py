from typing import Any

from boss_career_ops.config.singleton import SingletonMeta
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)

ANTI_REDIRECT_JS = """
() => {
    const BLOCKED_HOSTS = ['www.zhipin.com', 'zhipin.com'];
    const ALLOWED_PREFIX = '/web/geek/';

    function shouldBlock(url) {
        try {
            const u = new URL(url, location.href);
            if (!BLOCKED_HOSTS.includes(u.hostname)) return false;
            return !u.pathname.startsWith(ALLOWED_PREFIX);
        } catch { return false; }
    }

    const origAssign = Location.prototype.assign;
    Location.prototype.assign = function(url) {
        if (shouldBlock(url)) { console.warn('[BCO] 拦截 Location.assign:', url); return; }
        return origAssign.call(this, url);
    };

    const origReplace = Location.prototype.replace;
    Location.prototype.replace = function(url) {
        if (shouldBlock(url)) { console.warn('[BCO] 拦截 Location.replace:', url); return; }
        return origReplace.call(this, url);
    };

    const origPushState = History.prototype.pushState;
    History.prototype.pushState = function(state, title, url) {
        if (url && shouldBlock(url)) { console.warn('[BCO] 拦截 pushState:', url); return; }
        return origPushState.call(this, state, title, url);
    };
}
"""


class BrowserClient(metaclass=SingletonMeta):
    def __init__(self, cdp_url: str | None = None, bridge_url: str | None = None):
        self._cdp_url = cdp_url
        self._bridge_url = bridge_url
        self._browser = None
        self._context = None
        self._pw = None

    def reset(self):
        self.close()

    def _connect_bridge(self) -> bool:
        if not self._bridge_url:
            return False
        try:
            import httpx
            resp = httpx.get(f"{self._bridge_url}/status", timeout=5.0)
            if resp.status_code == 200:
                logger.info("Bridge 连接成功")
                return True
        except Exception:
            pass
        return False

    def _connect_cdp(self) -> bool:
        if not self._cdp_url:
            return False
        try:
            from patchright.sync_api import sync_playwright
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.connect_over_cdp(self._cdp_url)
            self._context = self._browser.contexts[0]
            logger.info("CDP 连接成功")
            return True
        except Exception as e:
            logger.debug("CDP 连接失败: %s", e)
        return False

    def _connect_patchright(self) -> bool:
        try:
            from patchright.sync_api import sync_playwright
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-infobars",
                ],
            )
            self._context = self._browser.new_context(
                viewport={"width": 1280, "height": 800},
                locale="zh-CN",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            )
            logger.info("patchright 浏览器启动成功")
            return True
        except Exception as e:
            logger.debug("patchright 启动失败: %s", e)
        return False

    def ensure_connected(self) -> bool:
        if self._context:
            return True
        for method in [self._connect_bridge, self._connect_cdp, self._connect_patchright]:
            if method():
                return True
        return False

    def get_page(self):
        if not self.ensure_connected():
            raise RuntimeError("浏览器连接失败")
        page = self._context.new_page()
        page.add_init_script(ANTI_REDIRECT_JS)
        return page

    def add_cookies(self, cookies: list[dict]):
        if not self._context:
            raise RuntimeError("浏览器未连接")
        self._context.add_cookies(cookies)

    def close(self):
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()
        self._browser = None
        self._context = None
        self._pw = None
