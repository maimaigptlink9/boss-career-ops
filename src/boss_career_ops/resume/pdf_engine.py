import tempfile
from pathlib import Path
from typing import Any

import markdown

from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)

TEMPLATE_DIR = Path(__file__).parent / "templates"
DEFAULT_TEMPLATE = TEMPLATE_DIR / "default.html"


class PDFEngine:
    def __init__(self, template_path: str | Path | None = None):
        self._template_path = Path(template_path) if template_path else DEFAULT_TEMPLATE

    def generate(self, resume_md: str, output_path: str | Path) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        html_content = self._md_to_html(resume_md)
        self._html_to_pdf(html_content, output_path)
        return output_path

    def _md_to_html(self, md: str) -> str:
        try:
            template = self._template_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            template = "<html><body><div id='resume-content'>{{CONTENT}}</div></body></html>"
        html_body = markdown.markdown(md, extensions=['tables', 'fenced_code'])
        return template.replace("{{CONTENT}}", html_body)

    def _html_to_pdf(self, html_content: str, output_path: Path):
        try:
            from patchright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.set_content(html_content)
                page.pdf(path=str(output_path), format="A4", margin={"top": "20mm", "bottom": "20mm", "left": "15mm", "right": "15mm"})
                browser.close()
            logger.info("PDF 生成成功: %s", output_path)
        except ImportError:
            logger.error("Playwright 未安装，无法生成 PDF")
            raise
