from boss_career_ops.agent.tools import get_job_detail, list_pipeline_jobs
from boss_career_ops.display.output import output_json, output_error
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)


def run_agent_evaluate(job_id: str | None = None, stage: str | None = None, limit: int = 10):
    if job_id:
        job = get_job_detail(job_id)
        if not job:
            output_error(
                command="agent-evaluate",
                message=f"未找到职位: {job_id}",
                code="JOB_NOT_FOUND",
            )
            return
        output_json(
            command="agent-evaluate",
            data=job,
            hints={"next_actions": [
                "分析职位数据后，使用 bco agent-save evaluate --job-id <id> --score <score> --grade <grade> --analysis \"<分析>\" 保存评估结果",
            ]},
        )
    else:
        jobs = list_pipeline_jobs(stage=stage)
        if not jobs:
            output_error(
                command="agent-evaluate",
                message="未找到职位" + (f"（阶段: {stage}）" if stage else ""),
                code="JOB_NOT_FOUND",
            )
            return
        jobs = jobs[:limit]
        output_json(
            command="agent-evaluate",
            data={"count": len(jobs), "jobs": jobs},
            hints={"next_actions": [
                "对每个职位分析后，使用 bco agent-save evaluate --job-id <id> --score <score> --grade <grade> --analysis \"<分析>\" 保存评估结果",
            ]},
        )
