from boss_career_ops.platform.registry import get_active_adapter
from boss_career_ops.config.settings import Settings
from boss_career_ops.evaluator.utils import extract_jd_text
from boss_career_ops.pipeline.manager import PipelineManager
from boss_career_ops.display.output import output_json, output_error
from boss_career_ops.display.logger import get_logger
import json

logger = get_logger(__name__)


def run_interview(job_id: str):
    adapter = get_active_adapter()
    settings = Settings()
    try:
        job = adapter.get_job_detail(job_id)
        if not job:
            output_error(command="interview", message="获取职位详情失败", code="DETAIL_ERROR")
            return
        prep = _generate_interview_prep(job, settings)
        if prep.get("ok") is False:
            output_error(command="interview", message=prep.get("error", "面试准备失败"), code=prep.get("code", "INTERVIEW_ERROR"))
            return
        output_json(
            command="interview",
            data=prep,
            hints={"next_actions": ["bco negotiate <jid>", "bco pipeline"]},
        )
    except Exception as e:
        output_error(command="interview", message=str(e), code="INTERVIEW_ERROR")


def _generate_interview_prep(job, settings) -> dict:
    # 先检查 Agent 生成的面试准备
    job_id = job.job_id if hasattr(job, 'job_id') else ""
    if job_id:
        try:
            with PipelineManager() as pm:
                ai_result = pm.get_ai_result(job_id, "interview_prep")
                if ai_result:
                    ai_data = json.loads(ai_result["result"])
                    ai_data["source"] = "agent"
                    ai_data["ok"] = True
                    return ai_data
        except Exception as e:
            logger.warning("读取 Agent 面试准备失败: %s", e)
    return {
        "ok": False,
        "error": "面试准备功能需要 Agent 支持。请先使用 bco agent-evaluate 读取职位数据，然后让 Agent 生成面试准备方案，再通过 bco agent-save interview-prep 保存",
        "code": "AI_RESULT_NOT_FOUND",
    }


def _extract_jd_text(job) -> str:
    return extract_jd_text(job)


def _extract_company_info(job) -> dict:
    return {
        "name": job.company_name,
        "industry": job.brand_industry,
        "scale": job.brand_scale,
        "stage": job.brand_stage,
    }
