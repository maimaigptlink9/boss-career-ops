import asyncio

from boss_career_ops.config.thresholds import Thresholds
from boss_career_ops.pipeline.manager import PipelineManager
from boss_career_ops.pipeline.stages import Stage
from boss_career_ops.display.output import output_json
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)


async def execute_auto_actions():
    thresholds = Thresholds()
    pm = PipelineManager()
    with pm:
        jobs = pm.list_jobs(stage=Stage.EVALUATED.value)
        results = {"auto_greet": [], "auto_apply": [], "skipped": [], "confirm_required": []}
        for job in jobs:
            score = job.get("score", 0.0)
            job_id = job.get("job_id", "")
            sid = job.get("security_id", "")
            if score >= thresholds.auto_action.auto_apply_threshold:
                from boss_career_ops.commands.apply import _apply_single
                result = await _apply_single(sid, job_id)
                results["auto_apply"].append({"job_id": job_id, "result": result})
                if result.get("ok"):
                    pm.update_stage(job_id, Stage.APPLIED)
            elif score >= thresholds.auto_action.auto_greet_threshold:
                from boss_career_ops.commands.greet import _greet_single
                result = await _greet_single(sid, job_id)
                results["auto_greet"].append({"job_id": job_id, "result": result})
            elif score < thresholds.auto_action.skip_threshold:
                results["skipped"].append({"job_id": job_id, "score": score})
            else:
                results["confirm_required"].append({"job_id": job_id, "score": score, "job_name": job.get("job_name", "")})
        return results
