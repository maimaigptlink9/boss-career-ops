import os
from pathlib import Path
from typing import Callable, Optional

from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)

_llm_instance = None

_CONFIG_PROVIDER = None

_PROVIDERS_FILE = Path(__file__).parent.parent / "data" / "llm_providers.yml"

_FALLBACK_DEFAULTS = {
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
    },
    "openai": {
        "base_url": None,
        "model": "gpt-4o-mini",
    },
    "local": {
        "base_url": None,
        "model": "llama3",
    },
}


def _load_provider_defaults() -> dict:
    import yaml
    try:
        with open(_PROVIDERS_FILE, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        providers = data.get("providers", {})
        defaults = {}
        for name, config in providers.items():
            defaults[name] = {
                "base_url": config.get("base_url") or None,
                "model": config.get("default_model", config.get("model")),
            }
        return defaults
    except Exception:
        return dict(_FALLBACK_DEFAULTS)


PROVIDER_DEFAULTS = _load_provider_defaults()


def set_config_provider(provider: Optional[Callable[[], dict]]) -> None:
    """注入外部配置提供者，避免对 ai_config 的动态导入依赖"""
    global _CONFIG_PROVIDER
    _CONFIG_PROVIDER = provider


def _resolve_api_config() -> tuple[str, str, str, str]:
    """从环境变量和注入的配置提供者解析 LLM 配置

    优先级：环境变量 > 注入的配置提供者 > 默认值
    返回：(api_key, provider, base_url, model)
    """
    api_key = os.environ.get("BCO_LLM_API_KEY", "")
    provider_from_env = bool(os.environ.get("BCO_LLM_PROVIDER", ""))
    provider = os.environ.get("BCO_LLM_PROVIDER", "deepseek").lower()
    base_url = os.environ.get("BCO_LLM_BASE_URL", "")
    model = os.environ.get("BCO_LLM_MODEL", "")

    if not api_key and _CONFIG_PROVIDER is not None:
        try:
            cfg = _CONFIG_PROVIDER()
            fallback_key = cfg.get("api_key", "")
            if fallback_key:
                api_key = fallback_key
                if not provider_from_env:
                    provider = cfg.get("provider", "deepseek").lower()
                if not base_url:
                    base_url = cfg.get("base_url", "")
                if not model:
                    model = cfg.get("model", "")
        except Exception:
            pass

    return api_key, provider, base_url, model


try:
    from boss_career_ops.config.ai_config import get_ai_config
    set_config_provider(get_ai_config)
except ImportError:
    pass


def get_llm():
    global _llm_instance
    if _llm_instance is not None:
        return _llm_instance

    api_key, provider, base_url, model = _resolve_api_config()

    if not api_key:
        logger.info("未配置 BCO_LLM_API_KEY，LLM 不可用")
        return None

    defaults = PROVIDER_DEFAULTS.get(provider, PROVIDER_DEFAULTS["deepseek"])

    if not base_url:
        base_url = defaults["base_url"] or ""
    if not model:
        model = defaults["model"]

    if provider == "local" and not base_url:
        logger.warning("local 提供者必须指定 BCO_LLM_BASE_URL")

    from langchain_openai import ChatOpenAI

    kwargs = {
        "model": model,
        "api_key": api_key,
    }
    if base_url:
        kwargs["base_url"] = base_url

    try:
        _llm_instance = ChatOpenAI(**kwargs)
        logger.info("LLM 已初始化: provider=%s, model=%s", provider, model)
    except Exception as e:
        logger.error("LLM 初始化失败: %s", e)
        _llm_instance = None
    return _llm_instance


def reset_llm():
    global _llm_instance
    _llm_instance = None


def is_llm_available() -> bool:
    if os.environ.get("BCO_LLM_API_KEY", ""):
        return True
    if _CONFIG_PROVIDER is not None:
        try:
            cfg = _CONFIG_PROVIDER()
            return bool(cfg.get("api_key", ""))
        except Exception:
            pass
    return False
