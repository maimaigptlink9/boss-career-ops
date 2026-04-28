import os
from unittest.mock import MagicMock, patch

import pytest

from boss_career_ops.agent.llm import (
    _FALLBACK_DEFAULTS,
    _load_provider_defaults,
    _PROVIDERS_FILE,
    get_llm,
    reset_llm,
)


class TestLoadProviderDefaults:
    def test_loaded_from_yaml(self):
        defaults = _load_provider_defaults()
        assert "deepseek" in defaults
        assert defaults["deepseek"]["base_url"] == "https://api.deepseek.com/v1"
        assert defaults["deepseek"]["model"] == "deepseek-chat"

    def test_yaml_contains_all_providers(self):
        defaults = _load_provider_defaults()
        expected_providers = ["deepseek", "qwen", "zhipu", "moonshot", "siliconflow", "openai", "local"]
        for p in expected_providers:
            assert p in defaults, f"缺少 provider: {p}"

    def test_each_provider_has_required_keys(self):
        defaults = _load_provider_defaults()
        for name, config in defaults.items():
            assert "base_url" in config, f"{name} 缺少 base_url"
            assert "model" in config, f"{name} 缺少 model"

    def test_openai_base_url_is_none(self):
        defaults = _load_provider_defaults()
        assert defaults["openai"]["base_url"] is None

    def test_local_provider_loaded(self):
        defaults = _load_provider_defaults()
        assert defaults["local"]["model"] == "llama3"
        assert defaults["local"]["base_url"] is None

    def test_fallback_when_yaml_missing(self):
        with patch("boss_career_ops.agent.llm._PROVIDERS_FILE", new="/nonexistent/path.yml"):
            defaults = _load_provider_defaults()
        assert defaults == _FALLBACK_DEFAULTS

    def test_fallback_when_yaml_invalid(self):
        with patch("builtins.open", side_effect=Exception("read error")):
            defaults = _load_provider_defaults()
        assert defaults == _FALLBACK_DEFAULTS

    def test_empty_base_url_becomes_none(self):
        defaults = _load_provider_defaults()
        assert defaults["openai"]["base_url"] is None
        assert defaults["local"]["base_url"] is None


class TestGetLlm:
    def setup_method(self):
        reset_llm()

    def teardown_method(self):
        reset_llm()
        for key in ["BCO_LLM_API_KEY", "BCO_LLM_PROVIDER", "BCO_LLM_BASE_URL", "BCO_LLM_MODEL"]:
            os.environ.pop(key, None)

    @patch("langchain_openai.ChatOpenAI", return_value=MagicMock())
    def test_deepseek_provider(self, mock_chat):
        os.environ["BCO_LLM_API_KEY"] = "test-key"
        os.environ["BCO_LLM_PROVIDER"] = "deepseek"
        with patch("boss_career_ops.config.ai_config.get_ai_config", return_value={"api_key": "", "provider": ""}):
            result = get_llm()
        assert result is not None
        call_kwargs = mock_chat.call_args[1]
        assert call_kwargs["model"] == "deepseek-chat"
        assert call_kwargs["base_url"] == "https://api.deepseek.com/v1"

    @patch("langchain_openai.ChatOpenAI", return_value=MagicMock())
    def test_qwen_provider(self, mock_chat):
        os.environ["BCO_LLM_API_KEY"] = "test-key"
        os.environ["BCO_LLM_PROVIDER"] = "qwen"
        with patch("boss_career_ops.config.ai_config.get_ai_config", return_value={"api_key": "", "provider": ""}):
            result = get_llm()
        assert result is not None
        call_kwargs = mock_chat.call_args[1]
        assert call_kwargs["model"] == "qwen-plus"
        assert call_kwargs["base_url"] == "https://dashscope.aliyuncs.com/compatible-mode/v1"

    @patch("langchain_openai.ChatOpenAI", return_value=MagicMock())
    def test_unknown_provider_falls_back_to_deepseek(self, mock_chat):
        os.environ["BCO_LLM_API_KEY"] = "test-key"
        os.environ["BCO_LLM_PROVIDER"] = "unknown_provider"
        with patch("boss_career_ops.config.ai_config.get_ai_config", return_value={"api_key": "", "provider": ""}):
            result = get_llm()
        assert result is not None
        call_kwargs = mock_chat.call_args[1]
        assert call_kwargs["model"] == "deepseek-chat"

    def test_no_api_key_returns_none(self):
        os.environ.pop("BCO_LLM_API_KEY", None)
        with patch("boss_career_ops.config.ai_config.get_ai_config", return_value={"api_key": "", "provider": ""}):
            result = get_llm()
        assert result is None

    @patch("langchain_openai.ChatOpenAI", return_value=MagicMock())
    def test_env_overrides_defaults(self, mock_chat):
        os.environ["BCO_LLM_API_KEY"] = "test-key"
        os.environ["BCO_LLM_PROVIDER"] = "deepseek"
        os.environ["BCO_LLM_MODEL"] = "custom-model"
        os.environ["BCO_LLM_BASE_URL"] = "https://custom.api.com/v1"
        with patch("boss_career_ops.config.ai_config.get_ai_config", return_value={"api_key": "", "provider": ""}):
            result = get_llm()
        assert result is not None
        call_kwargs = mock_chat.call_args[1]
        assert call_kwargs["model"] == "custom-model"
        assert call_kwargs["base_url"] == "https://custom.api.com/v1"
