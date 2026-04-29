from boss_career_ops.pipeline.manager import PipelineManager, STATUS_ACTIVE, STATUS_DISMISSED
from boss_career_ops.display.output import output_json, output_error


def run_pipeline_list(stage: str | None = None, status_filter: str = "active"):
    pm = PipelineManager()
    try:
        with pm:
            if status_filter == "all":
                status = None
            elif status_filter == "dismissed":
                status = STATUS_DISMISSED
            else:
                status = STATUS_ACTIVE
            jobs = pm.list_jobs(stage=stage, status=status)
            output_json(
                command="pipeline list",
                data=jobs,
                hints={"next_actions": ["bco pipeline dismiss <jid>", "bco evaluate --pending"]},
            )
    except Exception as e:
        output_error(command="pipeline list", message=str(e), code="PIPELINE_ERROR")


def run_pipeline_dismiss(job_ids: tuple[str, ...] = (), score_below: float | None = None, grade: str | None = None):
    pm = PipelineManager()
    try:
        with pm:
            count = 0
            if score_below is not None:
                count = pm.batch_dismiss_by_score(score_below)
                output_json(
                    command="pipeline dismiss",
                    data={"action": "dismiss_by_score", "max_score": score_below, "count": count},
                )
                return
            if grade is not None:
                grades = [g.strip() for g in grade.split(",") if g.strip()]
                count = pm.batch_dismiss_by_grade(grades)
                output_json(
                    command="pipeline dismiss",
                    data={"action": "dismiss_by_grade", "grades": grades, "count": count},
                )
                return
            if job_ids:
                count = pm.batch_dismiss(list(job_ids))
                output_json(
                    command="pipeline dismiss",
                    data={"action": "dismiss", "job_ids": list(job_ids), "count": count},
                )
                return
            output_error(
                command="pipeline dismiss",
                message="请指定职位ID或使用 --score-below / --grade 过滤条件",
                code="INVALID_PARAM",
                hints={"next_actions": [
                    "bco pipeline dismiss <jid1> <jid2>",
                    "bco pipeline dismiss --score-below 40",
                    "bco pipeline dismiss --grade D,E",
                ]},
            )
    except Exception as e:
        output_error(command="pipeline dismiss", message=str(e), code="PIPELINE_ERROR")


def run_pipeline_restore(job_ids: tuple[str, ...] = ()):
    pm = PipelineManager()
    try:
        with pm:
            count = pm.batch_restore(list(job_ids))
            output_json(
                command="pipeline restore",
                data={"action": "restore", "job_ids": list(job_ids), "count": count},
            )
    except Exception as e:
        output_error(command="pipeline restore", message=str(e), code="PIPELINE_ERROR")
