from boss_career_ops.boss.api.client import BossClient
from boss_career_ops.display.output import output_json, output_error
from boss_career_ops.display.logger import get_logger
from boss_career_ops.pipeline.manager import PipelineManager
from boss_career_ops.pipeline.stages import Stage

logger = get_logger(__name__)


def run_exchange(security_id: str, contact_type: str):
    client = BossClient()
    try:
        resp = client.post("exchange_contact", json_data={"securityId": security_id, "type": contact_type})
        if resp.get("code") == 0:
            try:
                pm = PipelineManager()
                with pm:
                    jobs = pm.list_jobs()
                    for job in jobs:
                        if job.get("security_id") == security_id:
                            pm.update_stage(job.get("job_id"), Stage.COMMUNICATING)
                            break
            except Exception as e:
                logger.warning("交换联系方式阶段推进写入 Pipeline 失败: %s", e)
            output_json(
                command="exchange",
                data={"security_id": security_id, "type": contact_type},
                hints={"next_actions": ["bco chat", "bco pipeline"]},
            )
        else:
            output_error(command="exchange", message=resp.get("message", "交换失败"), code="EXCHANGE_ERROR")
    except Exception as e:
        output_error(command="exchange", message=str(e), code="EXCHANGE_ERROR")
