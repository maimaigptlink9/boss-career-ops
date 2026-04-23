from boss_career_ops.pipeline.manager import PipelineManager
from boss_career_ops.display.output import output_json, output_error


def run_pipeline():
    pm = PipelineManager()
    try:
        with pm:
            jobs = pm.list_jobs()
            output_json(
                command="pipeline",
                data=jobs,
                hints={"next_actions": ["bco auto-action", "bco follow-up", "bco digest"]},
            )
    except Exception as e:
        output_error(command="pipeline", message=str(e), code="PIPELINE_ERROR")
