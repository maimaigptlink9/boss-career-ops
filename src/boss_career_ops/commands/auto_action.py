import asyncio

from boss_career_ops.pipeline.auto_action import execute_auto_actions
from boss_career_ops.display.output import output_json, output_error


def run_auto_action():
    try:
        results = asyncio.run(execute_auto_actions())
        output_json(
            command="auto-action",
            data=results,
            hints={"next_actions": ["bco pipeline", "bco follow-up"]},
        )
    except Exception as e:
        output_error(command="auto-action", message=str(e), code="AUTO_ACTION_ERROR")
