from boss_career_ops.platform.registry import get_active_adapter
from boss_career_ops.config.settings import EXPORTS_DIR
from boss_career_ops.display.error_codes import ErrorCode
from boss_career_ops.display.output import output_json, output_error
from boss_career_ops.display.logger import get_logger
from boss_career_ops.pipeline.manager import PipelineManager
from boss_career_ops.pipeline.stages import Stage

logger = get_logger(__name__)


def run_chat(export_fmt: str):
    adapter = get_active_adapter()
    try:
        chat_list = adapter.get_chat_list()
        if not chat_list:
            output_error(command="chat", message="获取聊天列表失败", code="CHAT_ERROR")
            return
        try:
            pm = PipelineManager()
            with pm:
                from boss_career_ops.pipeline.stages import STAGE_ORDER
                all_pipeline_jobs = pm.list_jobs()
                for contact in chat_list:
                    sid = contact.security_id
                    if not sid:
                        continue
                    for job in all_pipeline_jobs:
                        if job.get("security_id") == sid:
                            current_stage = Stage(job.get("stage", "发现"))
                            comm_idx = STAGE_ORDER.index(Stage.COMMUNICATING)
                            current_idx = STAGE_ORDER.index(current_stage)
                            if current_idx < comm_idx:
                                pm.update_stage(job.get("job_id"), Stage.COMMUNICATING)
                            break
        except Exception as e:
            logger.warning("聊天阶段推进写入 Pipeline 失败: %s", e)
        if export_fmt:
            _export_chat(chat_list, export_fmt)
        else:
            output_json(
                command="chat",
                data=[{"security_id": c.security_id, "name": c.name, "last_message": c.last_message, "time": c.time} for c in chat_list],
                hints={"next_actions": ["bco chatmsg <security_id>", "bco chat --export csv"]},
            )
    except Exception as e:
        output_error(command="chat", message=str(e), code="CHAT_ERROR")


def _export_chat(chat_list: list, fmt: str):
    from pathlib import Path
    import json
    output_dir = EXPORTS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    if fmt == "csv":
        import csv
        output_path = output_dir / "chat.csv"
        with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["security_id", "name", "last_message", "time"])
            for contact in chat_list:
                writer.writerow([
                    contact.security_id,
                    contact.name,
                    contact.last_message,
                    contact.time,
                ])
        output_json(command="chat", data={"exported": str(output_path), "format": "csv"})
    elif fmt == "json":
        output_path = output_dir / "chat.json"
        export_data = [{"security_id": c.security_id, "name": c.name, "last_message": c.last_message, "time": c.time} for c in chat_list]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        output_json(command="chat", data={"exported": str(output_path), "format": "json"})
    else:
        output_error(command="chat", message=f"不支持的导出格式: {fmt}", code=ErrorCode.INVALID_PARAM)
