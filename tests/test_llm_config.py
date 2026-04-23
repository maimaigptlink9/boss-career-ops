import os
from unittest.mock import patch

from boss_career_ops.agent.llm import get_llm, is_llm_available


class TestGetLlmNoApiKey:
    @patch.dict(os.environ, {}, clear=True)
    def test_returns_none_without_api_key(self):
        import boss_career_ops.agent.llm as llm_mod
        llm_mod._llm_instance = None
        result = get_llm()
        assert result is None

    @patch.dict(os.environ, {"BCO_LLM_API_KEY": ""}, clear=True)
    def test_returns_none_with_empty_api_key(self):
        import boss_career_ops.agent.llm as llm_mod
        llm_mod._llm_instance = None
        result = get_llm()
        assert result is None


class TestIsLlmAvailable:
    @patch.dict(os.environ, {}, clear=True)
    def test_false_when_no_api_key(self):
        assert is_llm_available() is False

    @patch.dict(os.environ, {"BCO_LLM_API_KEY": ""}, clear=True)
    def test_false_when_empty_api_key(self):
        assert is_llm_available() is False

    @patch.dict(os.environ, {"BCO_LLM_API_KEY": "sk-test"}, clear=True)
    def test_true_when_api_key_set(self):
        assert is_llm_available() is True


class TestGetLlmWithDeepseek:
    @patch.dict(
        os.environ,
        {"BCO_LLM_API_KEY": "sk-test", "BCO_LLM_PROVIDER": "deepseek"},
        clear=True,
    )
    def test_returns_chat_openai_instance(self):
        import boss_career_ops.agent.llm as llm_mod
        llm_mod._llm_instance = None
        result = get_llm()
        from langchain_openai import ChatOpenAI
        assert isinstance(result, ChatOpenAI)

    @patch.dict(
        os.environ,
        {"BCO_LLM_API_KEY": "sk-test", "BCO_LLM_PROVIDER": "deepseek"},
        clear=True,
    )
    def test_deepseek_default_base_url(self):
        import boss_career_ops.agent.llm as llm_mod
        llm_mod._llm_instance = None
        result = get_llm()
        assert result.openai_api_base == "https://api.deepseek.com/v1"

    @patch.dict(
        os.environ,
        {"BCO_LLM_API_KEY": "sk-test", "BCO_LLM_PROVIDER": "deepseek"},
        clear=True,
    )
    def test_deepseek_default_model(self):
        import boss_career_ops.agent.llm as llm_mod
        llm_mod._llm_instance = None
        result = get_llm()
        assert result.model_name == "deepseek-chat"


class TestProviderDefaults:
    @patch.dict(
        os.environ,
        {"BCO_LLM_API_KEY": "sk-test", "BCO_LLM_PROVIDER": "openai"},
        clear=True,
    )
    def test_openai_default_model(self):
        import boss_career_ops.agent.llm as llm_mod
        llm_mod._llm_instance = None
        result = get_llm()
        assert result.model_name == "gpt-4o-mini"

    @patch.dict(
        os.environ,
        {"BCO_LLM_API_KEY": "sk-test", "BCO_LLM_PROVIDER": "local", "BCO_LLM_BASE_URL": "http://localhost:11434/v1"},
        clear=True,
    )
    def test_local_default_model(self):
        import boss_career_ops.agent.llm as llm_mod
        llm_mod._llm_instance = None
        result = get_llm()
        assert result.model_name == "llama3"
        assert result.openai_api_base == "http://localhost:11434/v1"

    @patch.dict(
        os.environ,
        {
            "BCO_LLM_API_KEY": "sk-test",
            "BCO_LLM_PROVIDER": "deepseek",
            "BCO_LLM_BASE_URL": "https://custom.api.com/v1",
            "BCO_LLM_MODEL": "custom-model",
        },
        clear=True,
    )
    def test_custom_base_url_and_model_override(self):
        import boss_career_ops.agent.llm as llm_mod
        llm_mod._llm_instance = None
        result = get_llm()
        assert result.openai_api_base == "https://custom.api.com/v1"
        assert result.model_name == "custom-model"


class TestLlmCaching:
    @patch.dict(
        os.environ,
        {"BCO_LLM_API_KEY": "sk-test", "BCO_LLM_PROVIDER": "deepseek"},
        clear=True,
    )
    def test_cached_instance_returned(self):
        import boss_career_ops.agent.llm as llm_mod
        llm_mod._llm_instance = None
        first = get_llm()
        second = get_llm()
        assert first is second


class TestLlmInitErrorHandling:
    @patch.dict(
        os.environ,
        {"BCO_LLM_API_KEY": "sk-test", "BCO_LLM_PROVIDER": "deepseek"},
        clear=True,
    )
    @patch("langchain_openai.ChatOpenAI", side_effect=ValueError("无效的 API 密钥"))
    def test_returns_none_on_init_exception(self, mock_chat):
        import boss_career_ops.agent.llm as llm_mod
        llm_mod._llm_instance = None
        result = get_llm()
        assert result is None

    @patch.dict(
        os.environ,
        {"BCO_LLM_API_KEY": "sk-test", "BCO_LLM_PROVIDER": "deepseek"},
        clear=True,
    )
    @patch("langchain_openai.ChatOpenAI", side_effect=ConnectionError("网络不可达"))
    def test_returns_none_on_connection_error(self, mock_chat):
        import boss_career_ops.agent.llm as llm_mod
        llm_mod._llm_instance = None
        result = get_llm()
        assert result is None

    @patch.dict(
        os.environ,
        {"BCO_LLM_API_KEY": "sk-test", "BCO_LLM_PROVIDER": "deepseek"},
        clear=True,
    )
    @patch("langchain_openai.ChatOpenAI", side_effect=Exception("未知错误"))
    def test_returns_none_on_generic_exception(self, mock_chat):
        import boss_career_ops.agent.llm as llm_mod
        llm_mod._llm_instance = None
        result = get_llm()
        assert result is None
