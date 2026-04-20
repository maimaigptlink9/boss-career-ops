"""commands 包 - 所有 CLI 命令实现"""

from .doctor import run_doctor
from .setup import run_setup
from .login import run_login
from .status import run_status
from .search import run_search
from .recommend import run_recommend
from .evaluate import run_evaluate
from .auto_action import run_auto_action
from .greet import run_greet, run_batch_greet
from .apply import run_apply
from .resume import run_resume
from .chat import run_chat
from .chatmsg import run_chatmsg, run_chat_summary
from .mark import run_mark
from .exchange import run_exchange
from .pipeline import run_pipeline
from .follow_up import run_follow_up
from .digest import run_digest
from .watch import run_watch_add, run_watch_list, run_watch_remove, run_watch_run
from .shortlist import run_shortlist
from .export import run_export
from .interview import run_interview
from .negotiate import run_negotiate
from .dashboard import run_dashboard
from .ai_config import run_ai_config

__all__ = [
    "run_doctor",
    "run_setup",
    "run_login",
    "run_status",
    "run_search",
    "run_recommend",
    "run_evaluate",
    "run_auto_action",
    "run_greet",
    "run_batch_greet",
    "run_apply",
    "run_resume",
    "run_chat",
    "run_chatmsg",
    "run_chat_summary",
    "run_mark",
    "run_exchange",
    "run_pipeline",
    "run_follow_up",
    "run_digest",
    "run_watch_add",
    "run_watch_list",
    "run_watch_remove",
    "run_watch_run",
    "run_shortlist",
    "run_export",
    "run_interview",
    "run_negotiate",
    "run_dashboard",
    "run_ai_config",
]
