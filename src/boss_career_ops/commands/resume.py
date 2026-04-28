from boss_career_ops.resume.generator import ResumeGenerator
from boss_career_ops.resume.pdf_engine import PDFEngine
from boss_career_ops.resume.keywords import KeywordInjector
from boss_career_ops.resume.upload import ResumeUploader
from boss_career_ops.platform.registry import get_active_adapter
from boss_career_ops.config.settings import RESUMES_DIR, Settings
from boss_career_ops.display.output import output_json, output_error
from boss_career_ops.display.logger import get_logger
from boss_career_ops.pipeline.manager import PipelineManager
import json

logger = get_logger(__name__)


def _build_display_name(job, profile) -> str:
    name = getattr(profile, "name", "") or "未命名"
    job_name = job.job_name if hasattr(job, 'job_name') else job.get("job_name", "")
    return f"{name}_{job_name}.pdf"


def run_resume(job_id: str, fmt: str, upload: bool = False):
    adapter = get_active_adapter()
    try:
        job = adapter.get_job_detail(job_id)
        if not job:
            output_error(command="resume", message="获取职位详情失败", code="DETAIL_ERROR")
            return
        job_dict = job.to_dict()
        generator = ResumeGenerator()
        resume_md = None
        # 检查 Agent 润色结果
        try:
            with PipelineManager() as pm:
                ai_result = pm.get_ai_result(job_id, "resume")
                if ai_result:
                    ai_data = json.loads(ai_result["result"])
                    resume_md = ai_data.get("content", "")
        except Exception as e:
            logger.warning("读取 Agent 简历润色结果失败: %s", e)
        if not resume_md:
            resume_md = generator.generate(job_dict)
        if not resume_md:
            output_error(command="resume", message="简历文件 ~/.bco/cv.md 不存在，请先创建。可运行 bco setup 初始化模板", code="CV_NOT_FOUND")
            return
        injector = KeywordInjector()
        jd_text = generator._extract_jd_text(job_dict)
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
