import json
import urllib.parse

import pytest

from boss_career_ops.boss.api.endpoints import Endpoints
from boss_career_ops.boss.auth.token_store import TokenStore
from boss_career_ops.boss.browser_client import BrowserClient


@pytest.fixture(scope="module")
def browser_ctx():
    tokens = TokenStore().load()
    if not tokens:
        pytest.skip("无 Token，请先运行 bco login")

    cookies = {k: v for k, v in tokens.items() if isinstance(v, str)}

    browser = BrowserClient()
    if not browser.ensure_connected():
        pytest.skip("浏览器启动失败")

    page = browser.get_page()

    browser_cookies = []
    for name, value in cookies.items():
        if isinstance(value, str) and value:
            browser_cookies.append({
                "name": name,
                "value": value,
                "domain": ".zhipin.com",
                "path": "/",
            })

    page.goto("https://www.zhipin.com", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(3000)
    browser.add_cookies(browser_cookies)

    yield page, cookies

    page.close()
    browser.close()


def _browser_fetch(page, url, method="GET", body=None):
    js = f"""
    async () => {{
        try {{
            const opts = {{
                method: "{method}",
                credentials: "include",
                headers: {{ "Accept": "application/json" }},
            }};
            {"opts.body = JSON.stringify(" + json.dumps(body or {}) + ");" if body else ""}
            const resp = await fetch("{url}", opts);
            const status = resp.status;
            const contentType = resp.headers.get("content-type") || "";
            let body = "";
            try {{ body = await resp.text(); }} catch(e) {{ body = e.message; }}
            return JSON.stringify({{
                status: status,
                contentType: contentType,
                body: body.substring(0, 500)
            }});
        }} catch (e) {{
            return JSON.stringify({{error: e.message}});
        }}
    }}
    """
    result_str = page.evaluate(js)
    try:
        return json.loads(result_str)
    except Exception:
        return {"error": f"parse failed: {result_str[:200]}"}


def _classify(result):
    if "error" in result and "status" not in result:
        return "❌", "请求异常", result["error"][:80]
    status = result.get("status", 0)
    ct = result.get("contentType", "")
    body = result.get("body", "")
    if status == 404 and "text/html" in ct:
        return "❌", "404 不存在", "HTML 404 页面"
    if "application/json" not in ct:
        return "⚠️", f"HTTP {status} 非JSON", body[:80]
    try:
        data = json.loads(body)
        code = data.get("code", "N/A")
        message = data.get("message", "")[:60]
        if code == 0:
            return "✅", "存在且可用", f"code=0 {message}"
        return "⚠️", f"存在但异常", f"code={code} {message}"
    except Exception:
        return "⚠️", f"HTTP {status}", body[:80]


BASE = "https://www.zhipin.com"


class TestEndpointExists:
    def test_search_get(self, browser_ctx):
        page, cookies = browser_ctx
        stoken = cookies.get("__zp_stoken__", "")
        url = f"{BASE}/wapi/zpgeek/search/joblist.json?query=test&city=101010100&page=1&pageSize=5"
        if stoken:
            url += f"&__zp_stoken__={stoken}"
        result = _browser_fetch(page, url, method="GET")
        icon, status, detail = _classify(result)
        print(f"\n  search (GET):  {icon} {status} — {detail}")
        assert True

    def test_search_post(self, browser_ctx):
        page, cookies = browser_ctx
        stoken = cookies.get("__zp_stoken__", "")
        url = f"{BASE}/wapi/zpgeek/search/joblist.json?_="
        if stoken:
            url += f"&__zp_stoken__={stoken}"
        result = _browser_fetch(page, url, method="POST", body={})
        icon, status, detail = _classify(result)
        print(f"\n  search (POST): {icon} {status} — {detail}")
        assert True

    def test_job_detail(self, browser_ctx):
        page, cookies = browser_ctx
        stoken = cookies.get("__zp_stoken__", "")
        url = f"{BASE}/wapi/zpgeek/job/detail.json?securityId=test"
        if stoken:
            url += f"&__zp_stoken__={stoken}"
        result = _browser_fetch(page, url, method="GET")
        icon, status, detail = _classify(result)
        print(f"\n  job_detail:    {icon} {status} — {detail}")
        assert True

    def test_user_info_old(self, browser_ctx):
        page, cookies = browser_ctx
        stoken = cookies.get("__zp_stoken__", "")
        url = f"{BASE}/wapi/zpgeek/user/info.json"
        if stoken:
            url += f"?__zp_stoken__={stoken}"
        result = _browser_fetch(page, url, method="GET")
        icon, status, detail = _classify(result)
        print(f"\n  user_info (旧路径 /zpgeek/user/，已废弃): {icon} {status} — {detail}")
        assert True

    def test_user_info_new(self, browser_ctx):
        page, cookies = browser_ctx
        stoken = cookies.get("__zp_stoken__", "")
        url = f"{BASE}/wapi/zpuser/wap/getUserInfo.json"
        if stoken:
            url += f"?__zp_stoken__={stoken}"
        result = _browser_fetch(page, url, method="GET")
        icon, status, detail = _classify(result)
        print(f"\n  user_info (新路径 /zpuser/wap/): {icon} {status} — {detail}")
        assert True

    def test_chat_list_old(self, browser_ctx):
        page, cookies = browser_ctx
        stoken = cookies.get("__zp_stoken__", "")
        url = f"{BASE}/wapi/zpgeek/chat/geekHistoryList.json"
        if stoken:
            url += f"?__zp_stoken__={stoken}"
        result = _browser_fetch(page, url, method="GET")
        icon, status, detail = _classify(result)
        print(f"\n  chat_list (旧路径 /zpgeek/chat/，已废弃): {icon} {status} — {detail}")
        assert True

    def test_chat_list_zpchat_groupInfoList(self, browser_ctx):
        page, _ = browser_ctx
        url = f"{BASE}/wapi/zpchat/group/groupInfoList"
        result = _browser_fetch(page, url, method="GET")
        icon, status, detail = _classify(result)
        print(f"\n  chat_list (/zpchat/group/groupInfoList): {icon} {status} — {detail}")
        assert True

    def test_chat_list_zpchat_gravityGroupInfoList(self, browser_ctx):
        page, _ = browser_ctx
        url = f"{BASE}/wapi/zpchat/group/gravityGroupInfoList?page=1&scene=1"
        result = _browser_fetch(page, url, method="GET")
        icon, status, detail = _classify(result)
        print(f"\n  chat_list (/zpchat/group/gravityGroupInfoList): {icon} {status} — {detail}")
        assert True

    def test_chat_messages_old(self, browser_ctx):
        page, cookies = browser_ctx
        stoken = cookies.get("__zp_stoken__", "")
        url = f"{BASE}/wapi/zpgeek/chat/geekChatHistory.json?securityId=test"
        if stoken:
            url += f"&__zp_stoken__={stoken}"
        result = _browser_fetch(page, url, method="GET")
        icon, status, detail = _classify(result)
        print(f"\n  chat_messages (旧路径 /zpgeek/chat/): {icon} {status} — {detail}")
        assert True

    def test_chat_messages_zpchat_history(self, browser_ctx):
        page, cookies = browser_ctx
        stoken = cookies.get("__zp_stoken__", "")
        url = f"{BASE}/wapi/zpchat/history/geekHistoryList.json?securityId=test"
        if stoken:
            url += f"&__zp_stoken__={stoken}"
        result = _browser_fetch(page, url, method="GET")
        icon, status, detail = _classify(result)
        print(f"\n  chat_messages (/zpchat/history/geekHistoryList): {icon} {status} — {detail}")
        assert True

    def test_chat_messages_zpchat_geekChatHistory(self, browser_ctx):
        page, cookies = browser_ctx
        stoken = cookies.get("__zp_stoken__", "")
        url = f"{BASE}/wapi/zpchat/geekChatHistory.json?securityId=test"
        if stoken:
            url += f"&__zp_stoken__={stoken}"
        result = _browser_fetch(page, url, method="GET")
        icon, status, detail = _classify(result)
        print(f"\n  chat_messages (/zpchat/geekChatHistory): {icon} {status} — {detail}")
        assert True

    def test_greet(self, browser_ctx):
        page, _ = browser_ctx
        url = f"{BASE}/wapi/zpgeek/friend/addchatfriend.json"
        result = _browser_fetch(page, url, method="POST", body={"securityId": "test", "jobId": "test"})
        icon, status, detail = _classify(result)
        print(f"\n  greet:         {icon} {status} — {detail}")
        assert True

    def test_apply(self, browser_ctx):
        page, _ = browser_ctx
        url = f"{BASE}/wapi/zpgeek/resume/apply.json"
        result = _browser_fetch(page, url, method="POST", body={"securityId": "test", "jobId": "test"})
        icon, status, detail = _classify(result)
        print(f"\n  apply:         {icon} {status} — {detail}")
        assert True

    def test_upload_resume(self, browser_ctx):
        page, _ = browser_ctx
        url = f"{BASE}/wapi/zpgeek/resume/upload.json"
        result = _browser_fetch(page, url, method="POST", body={})
        icon, status, detail = _classify(result)
        print(f"\n  upload_resume: {icon} {status} — {detail}")
        assert True

    def test_exchange_contact(self, browser_ctx):
        page, _ = browser_ctx
        url = f"{BASE}/wapi/zpgeek/friend/exchange.json"
        result = _browser_fetch(page, url, method="POST", body={"securityId": "test", "type": "1"})
        icon, status, detail = _classify(result)
        print(f"\n  exchange_contact: {icon} {status} — {detail}")
        assert True

    def test_mark_contact(self, browser_ctx):
        page, _ = browser_ctx
        url = f"{BASE}/wapi/zpgeek/friend/mark.json"
        result = _browser_fetch(page, url, method="POST", body={"securityId": "test", "tag": "1"})
        icon, status, detail = _classify(result)
        print(f"\n  mark_contact:  {icon} {status} — {detail}")
        assert True

    def test_recommend_v1(self, browser_ctx):
        page, cookies = browser_ctx
        stoken = cookies.get("__zp_stoken__", "")
        url = f"{BASE}/wapi/zpgeek/recommend/job/list.json"
        if stoken:
            url += f"?__zp_stoken__={stoken}"
        result = _browser_fetch(page, url, method="GET")
        icon, status, detail = _classify(result)
        print(f"\n  recommend (v1): {icon} {status} — {detail}")
        assert True

    def test_recommend_v2(self, browser_ctx):
        page, cookies = browser_ctx
        stoken = cookies.get("__zp_stoken__", "")
        url = f"{BASE}/wapi/zprelation/interaction/geekGetJob?tag=5&isActive=true"
        if stoken:
            url += f"&__zp_stoken__={stoken}"
        result = _browser_fetch(page, url, method="GET")
        icon, status, detail = _classify(result)
        print(f"\n  recommend_v2:  {icon} {status} — {detail}")
        assert True
