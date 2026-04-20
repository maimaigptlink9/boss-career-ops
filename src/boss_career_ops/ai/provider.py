from abc import ABC, abstractmethod
from typing import Any

from boss_career_ops.ai.config import AIConfig, load_ai_config
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)


class AIProvider(ABC):
    @abstractmethod
    def chat(self, system: str, user: str) -> str: ...


class OpenAICompatProvider(AIProvider):
    def __init__(self, config: AIConfig):
        import httpx

        self._config = config
        self._client = httpx.Client(
            base_url=config.base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {config.api_key}"},
            timeout=60.0,
        )

    def chat(self, system: str, user: str) -> str:
        resp = self._client.post(
            "/chat/completions",
            json={
                "model": self._config.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "max_tokens": self._config.max_tokens,
                "temperature": self._config.temperature,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


_cached_provider: AIProvider | None = None


def get_provider(config: AIConfig | None = None) -> AIProvider | None:
    global _cached_provider
    if _cached_provider is not None:
        return _cached_provider
    if config is None:
        config = load_ai_config()
    if not config.configured:
        logger.debug("AI 未配置，跳过")
        return None
    if config.provider == "openai_compat":
        try:
            _cached_provider = OpenAICompatProvider(config)
            return _cached_provider
        except Exception as e:
            logger.error("AI Provider 初始化失败: %s", e)
            return None
    logger.warning("未知 AI Provider: %s", config.provider)
    return None


def reset_provider() -> None:
    global _cached_provider
    _cached_provider = None
