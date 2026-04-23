from boss_career_ops.platform.adapter import PlatformAdapter
from boss_career_ops.platform.models import (
    AuthStatus,
    ChatMessage,
    Contact,
    Job,
    OperationResult,
)
from boss_career_ops.platform.registry import (
    get_active_adapter,
    register_adapter,
)

__all__ = [
    "PlatformAdapter",
    "Job",
    "ChatMessage",
    "Contact",
    "AuthStatus",
    "OperationResult",
    "get_active_adapter",
    "register_adapter",
]
