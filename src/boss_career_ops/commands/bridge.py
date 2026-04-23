import httpx

from boss_career_ops.bridge.daemon import DEFAULT_HOST, DEFAULT_PORT


def _format_uptime(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
    return "".join(parts)


def run_bridge_status():
    from boss_career_ops.bridge.client import BridgeClient

    bridge = BridgeClient()

    if not bridge.is_available():
        print("Bridge Daemon: 未运行", flush=True)
        print("提示: 运行 bco login 会自动启动 Bridge Daemon", flush=True)
        return

    try:
        with httpx.Client(proxy=None) as client:
            resp = client.get(f"{bridge._bridge_url}/status", timeout=5.0)
        if resp.status_code != 200:
            print("Bridge Daemon: 未运行", flush=True)
            print("提示: 运行 bco login 会自动启动 Bridge Daemon", flush=True)
            return
        data = resp.json()
    except Exception:
        print("Bridge Daemon: 未运行", flush=True)
        print("提示: 运行 bco login 会自动启动 Bridge Daemon", flush=True)
        return

    uptime = data.get("uptime_seconds", 0)
    ext_count = data.get("extensions_connected", 0)
    print(f"Bridge Daemon: 运行中 ({DEFAULT_HOST}:{DEFAULT_PORT}, 运行 {_format_uptime(uptime)})", flush=True)
    print(f"Chrome 扩展: {'已连接' if ext_count > 0 else '未连接'} ({ext_count} 个)", flush=True)

    last_fetch = data.get("last_cookie_fetch")
    if last_fetch is None:
        print("上次 Cookie 获取: 无记录", flush=True)
    else:
        valid = last_fetch.get("valid", False)
        missing = last_fetch.get("missing", [])
        wt2_ok = "wt2" not in missing
        stoken_ok = "stoken" not in missing
        mark = "✓ 有效" if valid else "✗ 不完整"
        detail = f"(wt2: {'✓' if wt2_ok else '✗'}, stoken: {'✓' if stoken_ok else '✗'})"
        print(f"上次 Cookie 获取: {mark} {detail}", flush=True)


def run_bridge_test():
    from boss_career_ops.bridge.client import BridgeClient

    bridge = BridgeClient()

    # 步骤 1: Daemon 连通性
    print("[1/3] Daemon 连通性...", end=" ", flush=True)
    if not bridge.is_available():
        print(f"✗ (连接 {DEFAULT_HOST}:{DEFAULT_PORT} 失败)", flush=True)
        print("提示: 运行 bco login 会自动启动 Bridge Daemon", flush=True)
        return

    try:
        with httpx.Client(proxy=None) as client:
            resp = client.get(f"{bridge._bridge_url}/status", timeout=5.0)
        if resp.status_code != 200:
            print(f"✗ (连接 {DEFAULT_HOST}:{DEFAULT_PORT} 失败)", flush=True)
            print("提示: 运行 bco login 会自动启动 Bridge Daemon", flush=True)
            return
        data = resp.json()
    except Exception:
        print(f"✗ (连接 {DEFAULT_HOST}:{DEFAULT_PORT} 失败)", flush=True)
        print("提示: 运行 bco login 会自动启动 Bridge Daemon", flush=True)
        return

    print("✓", flush=True)

    # 步骤 2: Chrome 扩展连接
    ext_count = data.get("extensions_connected", 0)
    print(f"[2/3] Chrome 扩展连接...", end=" ", flush=True)
    if ext_count == 0:
        print("✗ (无扩展连接)", flush=True)
        print("提示: 请检查以下事项：", flush=True)
        print("  1. 打开 chrome://extensions/，确认「Boss-Career-Ops Bridge」扩展已启用", flush=True)
        print("  2. 确认 manifest.json 的 host_permissions 包含 http://127.0.0.1:18765/*", flush=True)
        print("  3. 修改 manifest.json 后需在 chrome://extensions/ 点击刷新按钮重新加载", flush=True)
        return
    print(f"✓ ({ext_count} 个)", flush=True)

    # 步骤 3: Cookie 获取
    print("[3/3] Cookie 获取...", end=" ", flush=True)
    try:
        cookies = bridge.get_cookies()
        if not cookies:
            print("✗ (未获取到 Cookie)", flush=True)
            print("提示: 请确认 Chrome 中已登录 BOSS 直聘（打开 zhipin.com 检查登录状态）", flush=True)
            return

        missing = []
        if not cookies.get("wt2"):
            missing.append("wt2")
        has_stoken = any(cookies.get(a) for a in ["stoken", "__zp_stoken__"])
        if not has_stoken:
            missing.append("stoken")

        cookie_count = len(cookies)
        if not missing:
            print(f"✓ (获取到 {cookie_count} 个 Cookie，登录态有效)", flush=True)
        else:
            print(f"✗ (获取到 {cookie_count} 个 Cookie，缺少: {', '.join(missing)})", flush=True)
    except Exception as e:
        print(f"✗ (获取失败: {e})", flush=True)
