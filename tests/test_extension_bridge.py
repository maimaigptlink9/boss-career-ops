import json
import os

import pytest


EXTENSION_DIR = os.path.join(os.path.dirname(__file__), "..", "extension")


def _read_manifest() -> dict:
    path = os.path.join(EXTENSION_DIR, "manifest.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _read_background_js() -> str:
    path = os.path.join(EXTENSION_DIR, "background.js")
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestExtensionManifest:
    def test_alarms_permission(self):
        manifest = _read_manifest()
        assert "alarms" in manifest["permissions"], "manifest 缺少 alarms 权限，Service Worker 重连无法唤醒"

    def test_scripting_permission(self):
        manifest = _read_manifest()
        assert "scripting" in manifest["permissions"], "manifest 缺少 scripting 权限，click/type_text/execute_js 命令无法执行"

    def test_host_permissions_include_localhost(self):
        manifest = _read_manifest()
        hosts = manifest.get("host_permissions", [])
        assert any("127.0.0.1" in h for h in hosts), "host_permissions 缺少 127.0.0.1，扩展无法连接 Daemon"

    def test_cookies_permission(self):
        manifest = _read_manifest()
        assert "cookies" in manifest["permissions"], "manifest 缺少 cookies 权限，无法读取 BOSS 登录态"

    def test_service_worker_defined(self):
        manifest = _read_manifest()
        assert manifest["background"]["service_worker"] == "background.js"


class TestExtensionBackgroundJs:
    def test_uses_chrome_alarms(self):
        js = _read_background_js()
        assert "chrome.alarms" in js, "background.js 未使用 chrome.alarms，Service Worker 被杀后无法重连"

    def test_no_setTimeout_reconnect(self):
        js = _read_background_js()
        assert "setTimeout" not in js, "background.js 仍使用 setTimeout，Service Worker 被杀后定时器会丢失"

    def test_has_onAlarm_listener(self):
        js = _read_background_js()
        assert "chrome.alarms.onAlarm" in js, "background.js 缺少 onAlarm 监听器"

    def test_has_reconnect_alarm_name(self):
        js = _read_background_js()
        assert "bco-reconnect" in js, "background.js 缺少重连闹钟名称"

    def test_connect_function_exists(self):
        js = _read_background_js()
        assert "function connect()" in js, "background.js 缺少 connect 函数"

    def test_onclose_schedules_reconnect(self):
        js = _read_background_js()
        assert "scheduleReconnect" in js, "background.js onclose 未调用 scheduleReconnect"

    def test_onopen_clears_alarm(self):
        js = _read_background_js()
        assert "chrome.alarms.clear" in js, "background.js 连接成功后未清除重连闹钟"
