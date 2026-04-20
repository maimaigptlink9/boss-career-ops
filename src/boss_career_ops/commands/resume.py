from pathlib import Path

from boss_career_ops.resume.generator import ResumeGenerator
from boss_career_ops.resume.pdf_engine import PDFEngine
from boss_career_ops.resume.keywords import KeywordInjector
from boss_career_ops.boss.api.client import BossClient
from boss_career_ops.config.settings import RESUMES_DIR
from boss_career_ops.display.output import output_json, output_error
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)


def run_resume(job_id: str, fmt: str):
    client = BossClient()
    try:
        resp = client.get("job_detail", params={"jobId": job_id})
        if resp.get("code") != 0:
            output_error(command="resume", message="获取职位详情失败", code="DETAIL_ERROR")
            return
        job = resp.get("zpData", {}).get("jobInfo", {})
        generator = ResumeGenerator()
        resume_md = generator.generate(job)
        injector = KeywordInjector()
        jd_text = generator._extract_jd_text(job)
        keywords = injector.extract_from_jd(jd_text)
        resume_md = injector.inject(resume_md, keywords)
        if fmt == "pdf":
            output_dir = RESUMES_DIR
            output_path = output_dir / f"{job_id}.pdf"
            engine = PDFEngine()
            engine.generate(resume_md, output_path)
            output_json(
                command="resume",
                data={"format": "pdf", "path": str(output_path), "keywords_injected": keywords},
                hints={"next_actions": ["bco apply <sid> <jid>"]},
            )
        else:
            output_json(
                command="resume",
                data={"format": "md", "content": resume_md, "keywords_injected": keywords},
                hints={"next_actions": ["bco resume <jid> --format pdf", "bco apply <sid> <jid>"]},
            )
    except Exception as e:
        output_error(command="resume", message=str(e), code="RESUME_ERROR")
