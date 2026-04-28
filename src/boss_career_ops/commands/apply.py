from boss_career_ops.platform.registry import get_active_adapter
from boss_career_ops.display.error_codes import ErrorCode
from boss_career_ops.display.output import output_json, output_error
from boss_career_ops.display.logger import get_logger
from boss_career_ops.pipeline.manager import PipelineManager
from boss_career_ops.pipeline.stages import Stage

logger = get_logger(__name__)


def _upload_resume_before_apply(job_id: str) -> dict:
    from boss_career_ops.resume.generator import ResumeGenerator
    from boss_career_ops.resume.pdf_engine import PDFEngine
    from boss_career_ops.resume.keywords import KeywordInjector
    from boss_career_ops.config.settings import RESUMES_DIR, Settings

    adapter = get_active_adapter()
    job = adapter.get_job_detail(job_id)
    if job is None:
        return {"ok": False, "message": "获取职位详情失败"}
    job_dict = job.to_dict()
    generator = ResumeGenerator()
    resume_md = generator.generate(job_dict)
    injector = KeywordInjector()
    jd_text = generator._extract_jd_text(job_dict)
    keywords = injector.extract_from_jd(jd_text)
    resume_md = injector.inject(resume_md, keywords)
    output_path = RESUMES_DIR / f"{job_id}.pdf"
    engine = PDFEngine()
    engine.generate(resume_md, output_path)
    settings = Settings()
    name = getattr(settings.profile, "name", "") or "未命名"
    job_name = job.job_name or "未命名"
    display_name = f"{name}_{job_name}.pdf"
    result = adapter.upload_resume(str(output_path), display_name)
    return {"ok": result.ok, "message": result.message, "code": result.code}


def run_apply(security_id: str, job_id: str, resume_job_id: str = ""):
    if resume_job_id:
        upload_result = _upload_resume_before_apply(resume_job_id)
        if not upload_result.get("ok"):
            output_error(
                command="apply",
                message=f"简历上传失败: {upload_result.get('message', '')}",
                code=upload_result.get("code", "RESUME_UPLOAD_ERROR"),
                hints={"next_actions": ["bco resume <jid> --format pdf --upload"]},
            )
            return
    adapter = get_active_adapter()
    result = adapter.apply(security_id, job_id)
    if result.ok:
        try:
            pm = PipelineManager()
            with pm:
                pm.upsert_job(job_id=job_id, security_id=security_id)
                pm.update_stage(job_id, Stage.APPLIED)
        except Exception as e:
            logger.warning("投递阶段推进写入 Pipeline 失败: %s", e)
        output_json(
            command="apply",
            data={"ok": result.ok, "message": result.message, "code": result.code},
            hints={"next_actions": ["bco pipeline", "bco follow-up"]},
        )
    else:
        output_error(
            command="apply",
            message=result.message,
            code=result.code or "APPLY_ERROR",
            hints={"next_actions": ["bco status", "bco login"]},
        )
