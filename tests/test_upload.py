from pathlib import Path
from unittest.mock import MagicMock, patch

from boss_career_ops.resume.upload import ResumeUploader
from boss_career_ops.display.error_codes import ErrorCode


class TestResumeUploader:
    def test_upload_file_not_exists(self):
        uploader = ResumeUploader(browser=MagicMock())
        result = uploader.upload(Path("/nonexistent/file.pdf"), "test.pdf")
        assert result["ok"] is False
        assert result["code"] == ErrorCode.RESUME_UPLOAD_ERROR

    def test_upload_bridge_and_browser_unavailable(self, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_text("fake pdf content")
        mock_browser = MagicMock()
        mock_browser.ensure_connected.return_value = False
        with patch("boss_career_ops.resume.upload.BridgeClient") as MockBridge:
            mock_bridge = MockBridge.return_value
            mock_bridge.is_available.return_value = False
            uploader = ResumeUploader(browser=mock_browser)
            result = uploader.upload(pdf, "张三_Golang.pdf")
            assert result["ok"] is False
            assert result["code"] == ErrorCode.APPLY_BROWSER_ERROR

    def test_upload_via_browser_success(self, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_text("fake pdf content")
        mock_page = MagicMock()
        mock_file_input = MagicMock()
        mock_page.query_selector.side_effect = [
            mock_file_input,
            None,
            None,
            MagicMock(),
        ]
        mock_browser = MagicMock()
        mock_browser.ensure_connected.return_value = True
        mock_browser.get_page.return_value = mock_page
        with patch("boss_career_ops.resume.upload.BridgeClient") as MockBridge:
            mock_bridge = MockBridge.return_value
            mock_bridge.is_available.return_value = False
            uploader = ResumeUploader(browser=mock_browser)
            result = uploader.upload(pdf, "张三_Golang.pdf")
            assert result["ok"] is True
            assert "张三_Golang.pdf" in result.get("display_name", "")

    def test_upload_no_file_input(self, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_text("fake pdf content")
        mock_page = MagicMock()
        mock_page.query_selector.return_value = None
        mock_browser = MagicMock()
        mock_browser.ensure_connected.return_value = True
        mock_browser.get_page.return_value = mock_page
        with patch("boss_career_ops.resume.upload.BridgeClient") as MockBridge:
            mock_bridge = MockBridge.return_value
            mock_bridge.is_available.return_value = False
            uploader = ResumeUploader(browser=mock_browser)
            result = uploader.upload(pdf, "test.pdf")
            assert result["ok"] is False
            assert result["code"] == ErrorCode.RESUME_UPLOAD_ERROR
