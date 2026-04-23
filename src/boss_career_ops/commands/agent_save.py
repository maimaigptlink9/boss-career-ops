import json

from boss_career_ops.agent.tools import write_evaluation, write_resume, write_chat_summary, write_interview_prep
from boss_career_ops.display.output import output_json, output_error
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)


def run_agent_save_evaluate(job_id: str, score: float, grade: str, analysis: str, scores_detail: str | None = None):
    try:
        detail = None
        if scores_detail:
            try:
                detail = json.loads(scores_detail)
            except json.JSONDecodeError:
                output_error(command="agent-save", message="scores_detail 不是有效的 JSON", code="INVALID_PARAM")
                return
        write_evaluation(job_id, score, grade, analysis, scores_detail=detail)
        output_json(
            command="agent-save",
            data={"task_type": "evaluate", "job_id": job_id, "score": score, "grade": grade},
        )
    except Exception as e:
        output_error(command="agent-save", message=f"保存评估结果失败: {e}", code="SAVE_ERROR")


def run_agent_save_resume(job_id: str, content: str):
    try:
        write_resume(job_id, content)
        output_json(
            command="agent-save",
            data={"task_type": "resume", "job_id": job_id},
        )
    except Exception as e:
        output_error(command="agent-save", message=f"保存简历润色结果失败: {e}", code="SAVE_ERROR")


def run_agent_save_chat_summary(security_id: str, data: str):
    try:
        summary_data = json.loads(data)
        write_chat_summary(security_id, summary_data)
        output_json(
            command="agent-save",
            data={"task_type": "chat_summary", "security_id": security_id},
        )
    except json.JSONDecodeError:
        output_error(command="agent-save", message="data 不是有效的 JSON", code="INVALID_PARAM")
    except Exception as e:
        output_error(command="agent-save", message=f"保存聊天摘要失败: {e}", code="SAVE_ERROR")


def run_agent_save_interview_prep(job_id: str, data: str):
    try:
        prep_data = json.loads(data)
        write_interview_prep(job_id, prep_data)
        output_json(
            command="agent-save",
            data={"task_type": "interview_prep", "job_id": job_id},
        )
    except json.JSONDecodeError:
        output_error(command="agent-save", message="data 不是有效的 JSON", code="INVALID_PARAM")
    except Exception as e:
        output_error(command="agent-save", message=f"保存面试准备失败: {e}", code="SAVE_ERROR")
