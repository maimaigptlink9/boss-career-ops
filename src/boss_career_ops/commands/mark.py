from boss_career_ops.boss.api.client import BossClient
from boss_career_ops.display.output import output_json, output_error


def run_mark(security_id: str, tag: str):
    client = BossClient()
    try:
        resp = client.post("mark_contact", json_data={"securityId": security_id, "tag": tag})
        if resp.get("code") == 0:
            output_json(
                command="mark",
                data={"security_id": security_id, "tag": tag},
                hints={"next_actions": ["bco chat", "bco pipeline"]},
            )
        else:
            output_error(command="mark", message=resp.get("message", "标记失败"), code="MARK_ERROR")
    except Exception as e:
        output_error(command="mark", message=str(e), code="MARK_ERROR")
