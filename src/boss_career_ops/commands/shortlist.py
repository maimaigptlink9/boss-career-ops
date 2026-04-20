from boss_career_ops.pipeline.manager import PipelineManager
from boss_career_ops.pipeline.stages import Stage
from boss_career_ops.display.output import output_json, output_error


def run_shortlist():
    pm = PipelineManager()
    try:
        with pm:
            jobs = pm.list_jobs()
            shortlisted = [j for j in jobs if j.get("score", 0) >= 3.5]
            output_json(
                command="shortlist",
                data=shortlisted,
                hints={"next_actions": ["bco pipeline", "bco auto-action"]},
            )
    except Exception as e:
        output_error(command="shortlist", message=str(e), code="SHORTLIST_ERROR")
