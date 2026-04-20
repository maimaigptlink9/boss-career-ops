from boss_career_ops.ai.config import AIConfig, load_ai_config, save_ai_config
from boss_career_ops.ai.provider import reset_provider
from boss_career_ops.display.output import output_json, output_error
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)


def run_ai_config(
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    provider: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    show: bool = False,
):
    config = load_ai_config()
    if show:
        masked_key = config.api_key[:8] + "..." if len(config.api_key) > 8 else "(未设置)"
        output_json(
            command="ai-config",
            data={
                "provider": config.provider,
                "api_key": masked_key,
                "base_url": config.base_url,
                "model": config.model,
                "max_tokens": config.max_tokens,
                "temperature": config.temperature,
                "configured": config.configured,
            },
        )
        return
    updated = False
    if api_key is not None:
        config.api_key = api_key
        updated = True
    if base_url is not None:
        config.base_url = base_url
        updated = True
    if model is not None:
        config.model = model
        updated = True
    if provider is not None:
        config.provider = provider
        updated = True
    if max_tokens is not None:
        config.max_tokens = max_tokens
        updated = True
    if temperature is not None:
        config.temperature = temperature
        updated = True
    if not updated:
        output_error(command="ai-config", message="未提供任何配置项，使用 --api-key / --base-url / --model 等参数", code="INVALID_PARAM")
        return
    save_ai_config(config)
    reset_provider()
    output_json(
        command="ai-config",
        data={"message": "AI 配置已更新", "provider": config.provider, "model": config.model, "configured": config.configured},
    )
