from boss_career_ops.agent.tools import get_job_detail
from boss_career_ops.display.output import output_json, output_error


def run_detail(job_id: str):
    job = get_job_detail(job_id)
    if job is None:
        output_error(command="detail", message="职位不存在", code="NOT_FOUND")
        return
    output_json(command="detail", data=job)
