from pathlib import Path

from boss_career_ops.resume.generator import ResumeGenerator
from boss_career_ops.resume.pdf_engine import PDFEngine
from boss_career_ops.resume.keywords import KeywordInjector
from boss_career_ops.resume.upload import ResumeUploader
from boss_career_ops.boss.api.client import BossClient
from boss_career_ops.config.settings import RESUMES_DIR, Settings
from boss_career_ops.display.output import output_json, output_error
from boss_career_ops.display.logger import get_logger
from boss_career_ops.pipeline.manager import PipelineManager

logger = get_logger(__name__)


def _build_display_name(job: dict, profile) -> str:
    name = getattr(profile, "name", "") or "未命名"
    job_name = job.get("jobName", "") or "未命名"
    return f"{name}_{job_name}.pdf"


def run_resume(job_id: str, fmt: str, upload: bool = False):
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
        upload_result = None
        if fmt == "pdf":
            output_dir = RESUMES_DIR
            output_path = output_dir / f"{job_id}.pdf"
            engine = PDFEngine()
            engine.generate(resume_md, output_path)
            if upload:
                settings = Settings()
                display_name = _build_display_name(job, settings.profile)
                uploader = ResumeUploader()
                upload_result = uploader.upload(output_path, display_name)
            try:
                pm = PipelineManager()
                with pm:
                    pm.upsert_job(job_id=job_id)
                    pm.update_job_data(job_id, {"resume_generated": True, "resume_format": fmt})
            except Exception as e:
                logger.warning("简历生成 Pipeline 写入失败: %s", e)
            data = {"format": "pdf", "path": str(output_path), "keywords_injected": keywords}
            if upload_result:
                data["upload"] = upload_result
            output_json(
                command="resume",
                data=data,
                hints={"next_actions": ["bco apply <sid> <jid>"]},
            )
        else:
            try:
                pm = PipelineManager()
                with pm:
                    pm.upsert_job(job_id=job_id)
                    pm.update_job_data(job_id, {"resume_generated": True, "resume_format": fmt})
            except Exception as e:
                logger.warning("简历生成 Pipeline 写入失败: %s", e)
            output_json(
                command="resume",
                data={"format": "md", "content": resume_md, "keywords_injected": keywords},
                hints={"next_actions": ["bco resume <jid> --format pdf", "bco apply <sid> <jid>"]},
            )
    except Exception as e:
        output_error(command="resume", message=str(e), code="RESUME_ERROR")
