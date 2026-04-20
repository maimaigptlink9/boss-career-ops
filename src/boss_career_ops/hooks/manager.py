from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from boss_career_ops.config.singleton import SingletonMeta
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)


class HookAction(Enum):
    CONTINUE = "continue"
    VETO = "veto"
    MODIFY = "modify"


@dataclass
class HookResult:
    action: HookAction = HookAction.CONTINUE
    modified_data: Any = None
    reason: str = ""


HookCallback = Callable[[Any], HookResult]


class HookManager(metaclass=SingletonMeta):
    def __init__(self):
        self._hooks: dict[str, list[HookCallback]] = {}

    def register(self, hook_name: str, callback: HookCallback):
        if hook_name not in self._hooks:
            self._hooks[hook_name] = []
        self._hooks[hook_name].append(callback)
        logger.info("注册 Hook: %s", hook_name)

    def unregister(self, hook_name: str, callback: HookCallback):
        if hook_name in self._hooks:
            self._hooks[hook_name] = [
                cb for cb in self._hooks[hook_name] if cb is not callback
            ]

    async def execute_before(self, hook_name: str, data: Any = None) -> HookResult:
        combined_result = HookResult(action=HookAction.CONTINUE)
        for callback in self._hooks.get(hook_name, []):
            try:
                result = callback(data)
                if result.action == HookAction.VETO:
                    logger.info("Hook %s 返回 veto: %s", hook_name, result.reason)
                    return result
                if result.action == HookAction.MODIFY and result.modified_data is not None:
                    data = result.modified_data
                    combined_result.modified_data = data
            except Exception as e:
                logger.error("Hook %s 执行异常: %s", hook_name, e)
        combined_result.modified_data = data
        return combined_result

    async def execute_after(self, hook_name: str, data: Any = None):
        for callback in self._hooks.get(hook_name, []):
            try:
                callback(data)
            except Exception as e:
                logger.error("Hook %s 执行异常: %s", hook_name, e)

    def has_hooks(self, hook_name: str) -> bool:
        return bool(self._hooks.get(hook_name, []))

    def list_hooks(self) -> dict[str, int]:
        return {name: len(callbacks) for name, callbacks in self._hooks.items()}

    def clear(self):
        self._hooks.clear()
