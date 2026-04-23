import sys
import importlib

from boss_career_ops.display.output import output_json, output_error
from boss_career_ops.config.settings import (
    CONFIG_DIR, CV_PATH,
    EXPORTS_DIR, RESUMES_DIR,
)


REQUIRED_PACKAGES = [
    "click",
    "httpx",
    "patchright",
    "playwright",
    "textual",
    "rich",
    "yaml",
    "cryptography",
    "aiohttp",
    "portalocker",
]


def _check_python_version() -> dict:
    version = sys.version_info
    ok = version >= (3, 12)
    return {
        "name": "Python 版本",
        "ok": ok,
        "detail": f"{version.major}.{version.minor}.{version.micro}",
        "required": ">=3.12",
    }


def _check_dependencies() -> list[dict]:
    results = []
    for pkg in REQUIRED_PACKAGES:
        try:
            mod = importlib.import_module(pkg)
            version = getattr(mod, "__version__", "已安装")
            results.append({
                "name": f"依赖: {pkg}",
                "ok": True,
                "detail": str(version),
            })
        except ImportError:
            results.append({
                "name": f"依赖: {pkg}",
                "ok": False,
                "detail": "未安装",
            })
    return results


def _check_browser_driver() -> dict:
    try:
        from patchright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        return {
            "name": "Chromium 浏览器驱动",
            "ok": True,
            "detail": "patchright Chromium 可用",
        }
    except Exception as e:
        return {
            "name": "Chromium 浏览器驱动",
            "ok": False,
            "detail": f"不可用: {e}",
        }


def _check_config_files() -> list[dict]:
    results = []
    profile_path = CONFIG_DIR / "profile.yml"
    thresholds_path = CONFIG_DIR / "thresholds.yml"
    results.append({
        "name": "个人档案 (profile.yml)",
        "ok": profile_path.exists(),
        "detail": str(profile_path) if profile_path.exists() else "不存在，请运行 bco setup",
    })
    results.append({
        "name": "阈值配置 (thresholds.yml)",
        "ok": thresholds_path.exists(),
        "detail": str(thresholds_path) if thresholds_path.exists() else "不存在，请运行 bco setup",
    })
    results.append({
        "name": "简历文件 (cv.md)",
        "ok": CV_PATH.exists(),
        "detail": str(CV_PATH) if CV_PATH.exists() else "不存在，请运行 bco setup",
    })
    return results


def _check_data_dirs() -> list[dict]:
    results = []
    for label, dir_path in [
        ("导出目录", EXPORTS_DIR),
        ("简历输出目录", RESUMES_DIR),
    ]:
        results.append({
            "name": f"{label} ({dir_path.name}/)",
            "ok": dir_path.exists(),
            "detail": str(dir_path) if dir_path.exists() else "将在首次使用时自动创建",
        })
    return results


def _check_login_status() -> dict:
    try:
        from boss_career_ops.platform.registry import get_active_adapter
        adapter = get_active_adapter()
        status = adapter.check_auth_status()
        if status.ok:
            return {
                "name": "登录状态",
                "ok": True,
                "detail": "已登录",
            }
        return {
            "name": "登录状态",
            "ok": False,
            "detail": "未登录，请运行 bco login",
        }
    except Exception as e:
        return {
            "name": "登录状态",
            "ok": False,
            "detail": f"检查失败: {e}",
        }


def run_doctor():
    checks = []
    checks.append(_check_python_version())
    checks.extend(_check_dependencies())
    checks.append(_check_browser_driver())
    checks.extend(_check_config_files())
    checks.extend(_check_data_dirs())
    checks.append(_check_login_status())

    all_ok = all(c["ok"] for c in checks)
    failed = [c for c in checks if not c["ok"]]

    if all_ok:
        output_json(
            command="doctor",
            data=checks,
            hints={"next_actions": ["bco login", "bco search \"关键词\" --city 城市"]},
        )
    else:
        output_json(
            command="doctor",
            data=checks,
            hints={"next_actions": [f"修复: {c['name']} — {c['detail']}" for c in failed]},
        )
