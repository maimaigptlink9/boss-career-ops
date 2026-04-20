from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from boss_career_ops.config.settings import CONFIG_DIR
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)

AI_CONFIG_PATH = CONFIG_DIR / "ai.yml"


@dataclass
class AIConfig:
    provider: str = "openai_compat"
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    max_tokens: int = 1024
    temperature: float = 0.3

    @property
    def configured(self) -> bool:
        return bool(self.api_key)


def load_ai_config() -> AIConfig:
    if not AI_CONFIG_PATH.exists():
        return AIConfig()
    try:
        with open(AI_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return AIConfig(
            provider=data.get("provider", "openai_compat"),
            api_key=data.get("api_key", ""),
            base_url=data.get("base_url", "https://api.openai.com/v1"),
            model=data.get("model", "gpt-4o-mini"),
            max_tokens=data.get("max_tokens", 1024),
            temperature=data.get("temperature", 0.3),
        )
    except Exception as e:
        logger.error("AI 配置加载失败: %s", e)
        return AIConfig()


def save_ai_config(config: AIConfig) -> None:
    AI_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "provider": config.provider,
        "api_key": config.api_key,
        "base_url": config.base_url,
        "model": config.model,
        "max_tokens": config.max_tokens,
        "temperature": config.temperature,
    }
    with open(AI_CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
    logger.info("AI 配置已保存: %s", AI_CONFIG_PATH)
