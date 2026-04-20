from boss_career_ops.pipeline.manager import PipelineManager
from boss_career_ops.display.output import output_json, output_error


def run_digest():
    pm = PipelineManager()
    try:
        with pm:
            summary = pm.get_daily_summary()
            output_json(
                command="digest",
                data=summary,
                hints={"next_actions": ["bco pipeline", "bco follow-up"]},
            )
    except Exception as e:
        output_error(command="digest", message=str(e), code="DIGEST_ERROR")
