import shutil
import tempfile
from pathlib import Path

from boss_career_ops.boss.browser_client import BrowserClient
from boss_career_ops.bridge.client import BridgeClient
from boss_career_ops.platform.adapter import PlatformBrowser
from boss_career_ops.display.error_codes import ErrorCode
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)

RESUME_MANAGE_URL = "https://www.zhipin.com/web/geek/resume"


class ResumeUploader:
    def __init__(self, browser: BrowserClient | PlatformBrowser | None = None):
        if browser is None:
            self._browser = BrowserClient()
        elif isinstance(browser, PlatformBrowser):
            self._browser = browser.inner
        else:
            self._browser = browser

    def upload(self, pdf_path: Path, display_name: str) -> dict:
        if not pdf_path.exists():
            return {"ok": False, "message": f"PDF 文件不存在: {pdf_path}", "code": ErrorCode.RESUME_UPLOAD_ERROR}
        tmp_path = None
        try:
            tmp_dir = tempfile.mkdtemp(prefix="bco_upload_")
            tmp_path = Path(tmp_dir) / display_name
            shutil.copy2(pdf_path, tmp_path)
            if self._browser.is_bridge_available():
                bridge = BridgeClient()
                result = self._upload_via_bridge(bridge, tmp_path)
                if result.get("ok"):
                    return result
                logger.warning("Bridge 上传失败: %s，尝试 CDP/patchright", result.get("message"))
            if self._browser.ensure_connected():
                result = self._upload_via_browser(tmp_path)
                return result
            return {"ok": False, "message": "浏览器通道全部不可用，无法上传简历", "code": ErrorCode.APPLY_BROWSER_ERROR}
        except Exception as e:
            logger.error("简历上传异常: %s", e)
            return {"ok": False, "message": str(e), "code": ErrorCode.RESUME_UPLOAD_ERROR}
        finally:
            if tmp_path and tmp_path.parent.exists():
                try:
                    shutil.rmtree(tmp_path.parent)
                except Exception:
                    logger.debug("临时目录清理失败: %s", tmp_path.parent)

    def _upload_via_bridge(self, bridge: BridgeClient, file_path: Path) -> dict:
        try:
            nav = bridge.navigate(RESUME_MANAGE_URL)
            if not nav.ok:
                return {"ok": False, "message": f"Bridge 导航失败: {nav.error}"}
            upload_btn_result = bridge.click(".upload-resume-btn")
            if not upload_btn_result.ok:
                upload_btn_result = bridge.click("[ka='resume-upload']")
            file_input_js = """
            (function() {
                var input = document.querySelector('input[type="file"]');
                if (!input) return {ok: false, error: '未找到文件输入框'};
                return {ok: true};
            })()
            """
            check = bridge.execute_js(file_input_js)
            if not check.ok:
                return {"ok": False, "message": "简历上传页面未就绪"}
            return {"ok": False, "message": "Bridge 通道暂不支持文件上传，请使用浏览器通道"}
        except Exception as e:
            return {"ok": False, "message": str(e)}

    def _upload_via_browser(self, file_path: Path) -> dict:
        page = None
        try:
            page = self._browser.get_page()
            page.goto(RESUME_MANAGE_URL, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2000)
            file_input = page.query_selector('input[type="file"]')
            if not file_input:
                upload_btn = page.query_selector(".upload-resume-btn") or page.query_selector("[ka='resume-upload']")
                if upload_btn:
                    upload_btn.click()
                    page.wait_for_timeout(1000)
                file_input = page.query_selector('input[type="file"]')
            if not file_input:
                return {"ok": False, "message": "未找到简历上传入口", "code": ErrorCode.RESUME_UPLOAD_ERROR}
            file_input.set_input_files(str(file_path))
            page.wait_for_timeout(5000)
            success_indicators = [
                page.query_selector(".resume-upload-success"),
                page.query_selector(".upload-success"),
                page.query_selector("[class*='success']"),
            ]
            if any(success_indicators):
                logger.info("简历上传成功: %s", file_path.name)
                return {"ok": True, "message": "简历上传成功", "display_name": file_path.name}
            logger.info("简历上传已提交（无法确认最终状态）: %s", file_path.name)
            return {"ok": True, "message": "简历上传已提交", "display_name": file_path.name}
        except Exception as e:
            return {"ok": False, "message": f"浏览器上传失败: {e}", "code": ErrorCode.RESUME_UPLOAD_ERROR}
        finally:
            if page:
                try:
                    page.close()
                except Exception:
                    pass
