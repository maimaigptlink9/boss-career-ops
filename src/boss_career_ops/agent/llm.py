import os

from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)

_llm_instance = None

PROVIDER_DEFAULTS = {
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


def get_llm():
    global _llm_instance
    if _llm_instance is not None:
        return _llm_instance

    api_key = os.environ.get("BCO_LLM_API_KEY", "")
    if not api_key:
        logger.info("未配置 BCO_LLM_API_KEY，LLM 不可用")
        return None

    provider = os.environ.get("BCO_LLM_PROVIDER", "deepseek").lower()
    base_url = os.environ.get("BCO_LLM_BASE_URL", "")
    model = os.environ.get("BCO_LLM_MODEL", "")

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


def is_llm_available() -> bool:
    return bool(os.environ.get("BCO_LLM_API_KEY", ""))
