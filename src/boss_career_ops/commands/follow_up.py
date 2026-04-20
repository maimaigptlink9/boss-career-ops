from boss_career_ops.pipeline.manager import PipelineManager
from boss_career_ops.display.output import output_json, output_error


def run_follow_up():
    pm = PipelineManager()
    try:
        with pm:
            stale = pm.get_stale_jobs(days=3)
            output_json(
                command="follow-up",
                data=stale,
                hints={"next_actions": ["bco greet <sid> <jid>", "bco pipeline"]},
            )
    except Exception as e:
        output_error(command="follow-up", message=str(e), code="FOLLOW_UP_ERROR")
