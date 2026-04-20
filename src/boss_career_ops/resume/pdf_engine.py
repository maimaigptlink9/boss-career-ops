import tempfile
from pathlib import Path
from typing import Any

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
        import re
        html_body = self._simple_md_to_html(md)
        return template.replace("{{CONTENT}}", html_body)

    def _simple_md_to_html(self, md: str) -> str:
        lines = md.split("\n")
        html_lines = []
        for line in lines:
            if line.startswith("<!--"):
                continue
            if line.startswith("# "):
                html_lines.append(f"<h1>{line[2:]}</h1>")
            elif line.startswith("## "):
                html_lines.append(f"<h2>{line[3:]}</h2>")
            elif line.startswith("### "):
                html_lines.append(f"<h3>{line[4:]}</h3>")
            elif line.startswith("- "):
                html_lines.append(f"<li>{line[2:]}</li>")
            elif line.startswith("**") and line.endswith("**"):
                html_lines.append(f"<p><strong>{line[2:-2]}</strong></p>")
            elif line.strip():
                html_lines.append(f"<p>{line}</p>")
            else:
                html_lines.append("<br>")
        return "\n".join(html_lines)

    def _html_to_pdf(self, html_content: str, output_path: Path):
        try:
            from playwright.sync_api import sync_playwright
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
