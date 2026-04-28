import os
from pathlib import Path

import yaml

from boss_career_ops.config.settings import BCO_HOME
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)

AI_CONFIG_FILE = BCO_HOME / "ai_config.yml"
PROVIDERS_FILE = Path(__file__).parent.parent / "data" / "llm_providers.yml"


def get_ai_config() -> dict:
    provider = os.environ.get("BCO_LLM_PROVIDER", "")
    api_key = os.environ.get("BCO_LLM_API_KEY", "")
    if provider and api_key:
        return {"provider": provider, "api_key": api_key, "source": "env"}
    if AI_CONFIG_FILE.exists():
        try:
            config = yaml.safe_load(AI_CONFIG_FILE.read_text(encoding="utf-8")) or {}
        except Exception as e:
            logger.error("读取 AI 配置失败: %s", e)
            return {"provider": "", "api_key": "", "source": "none"}
        encrypted_key = config.get("api_key_encrypted", "")
        api_key = ""
        if encrypted_key:
            try:
                from boss_career_ops.boss.auth.token_store import TokenStore
                store = TokenStore()
                api_key = store.fernet.decrypt(encrypted_key.encode()).decode()
            except Exception as e:
                logger.error("解密 API Key 失败: %s", e)
        return {
            "provider": config.get("provider", "deepseek"),
            "api_key": api_key,
            "source": "file",
        }
    return {"provider": "", "api_key": "", "source": "none"}


def save_ai_config(provider: str, api_key: str):
    from boss_career_ops.boss.auth.token_store import TokenStore
    store = TokenStore()
    encrypted = store.fernet.encrypt(api_key.encode()).decode()
    config = {"provider": provider, "api_key_encrypted": encrypted}
    AI_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    AI_CONFIG_FILE.write_text(yaml.dump(config, allow_unicode=True), encoding="utf-8")
    logger.info("AI 配置已保存: provider=%s", provider)


def get_ai_status() -> dict:
    config = get_ai_config()
    return {
        "configured": bool(config["api_key"]),
        "provider": config["provider"] or "deepseek",
        "source": config["source"],
    }


def get_providers() -> list[dict]:
    if not PROVIDERS_FILE.exists():
        return []
    try:
        data = yaml.safe_load(PROVIDERS_FILE.read_text(encoding="utf-8")) or {}
    except Exception as e:
        logger.error("读取 Provider 配置失败: %s", e)
        return []
    providers = data.get("providers", {})
    result = []
    for key, info in providers.items():
        result.append({
            "id": key,
            "name": info.get("name", key),
            "description": info.get("description", ""),
            "register_url": info.get("register_url", ""),
            "api_key_url": info.get("api_key_url", ""),
            "free_tokens": info.get("free_tokens", ""),
            "pricing_hint": info.get("pricing_hint", ""),
            "base_url": info.get("base_url", ""),
            "default_model": info.get("default_model", ""),
            "recommended": info.get("recommended", False),
        })
    result.sort(key=lambda p: (not p["recommended"], p["name"]))
    return result
