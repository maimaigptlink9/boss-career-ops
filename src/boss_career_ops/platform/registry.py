from __future__ import annotations

from typing import Any

from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)

_registry: dict[str, type] = {}
_active_adapter = None
_auto_registered = False


def _auto_register() -> None:
    global _auto_registered
    if _auto_registered:
        return
    _auto_registered = True
    try:
        from boss_career_ops.platform.adapters.boss.adapter import BossAdapter
        register_adapter("boss", BossAdapter)
    except ImportError:
        logger.debug("BossAdapter 导入失败，跳过自动注册")


def register_adapter(name: str, adapter_class: type) -> None:
    _registry[name] = adapter_class
    logger.debug("注册平台适配器: %s → %s", name, adapter_class.__name__)


def get_registered_platforms() -> list[str]:
    return list(_registry.keys())


def reset_adapter() -> None:
    global _active_adapter, _auto_registered
    _active_adapter = None
    _auto_registered = False


def get_active_adapter():
    global _active_adapter
    if _active_adapter is not None:
        return _active_adapter
    _auto_register()
    from boss_career_ops.config.settings import Settings
    settings = Settings()
    platform_name = getattr(settings, "platform", "boss") or "boss"
    adapter_class = _registry.get(platform_name)
    if adapter_class is None:
        raise ValueError(
            f"不支持的平台: {platform_name}，已注册平台: {list(_registry.keys())}"
        )
    _active_adapter = adapter_class()
    return _active_adapter


