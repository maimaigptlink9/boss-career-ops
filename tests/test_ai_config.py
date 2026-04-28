import os
from unittest.mock import patch
from pathlib import Path

from boss_career_ops.config.ai_config import get_ai_config, save_ai_config, get_ai_status, get_providers


class TestGetAiConfig:
    def test_env_variables_take_priority(self):
        with patch.dict(os.environ, {"BCO_LLM_PROVIDER": "deepseek", "BCO_LLM_API_KEY": "sk-test"}):
            config = get_ai_config()
            assert config["source"] == "env"
            assert config["provider"] == "deepseek"
            assert config["api_key"] == "sk-test"

    def test_no_config_returns_none_source(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("boss_career_ops.config.ai_config.AI_CONFIG_FILE", Path("/nonexistent/ai_config.yml")):
                config = get_ai_config()
                assert config["source"] == "none"
                assert config["api_key"] == ""

    def test_file_source_reads_encrypted_key(self, tmp_path):
        config_file = tmp_path / "ai_config.yml"
        with patch("boss_career_ops.config.ai_config.AI_CONFIG_FILE", config_file):
            save_ai_config("deepseek", "sk-from-file")
            with patch.dict(os.environ, {}, clear=True):
                config = get_ai_config()
                assert config["source"] == "file"
                assert config["provider"] == "deepseek"
                assert config["api_key"] == "sk-from-file"


class TestSaveAiConfig:
    def test_saves_encrypted_key(self, tmp_path):
        config_file = tmp_path / "ai_config.yml"
        with patch("boss_career_ops.config.ai_config.AI_CONFIG_FILE", config_file):
            save_ai_config("deepseek", "sk-test-key")
            assert config_file.exists()
            content = config_file.read_text(encoding="utf-8")
            assert "sk-test-key" not in content
            assert "api_key_encrypted" in content


class TestGetAiStatus:
    def test_configured_status(self):
        with patch.dict(os.environ, {"BCO_LLM_PROVIDER": "deepseek", "BCO_LLM_API_KEY": "sk-test"}):
            status = get_ai_status()
            assert status["configured"] is True
            assert status["provider"] == "deepseek"

    def test_not_configured_status(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("boss_career_ops.config.ai_config.AI_CONFIG_FILE", Path("/nonexistent/ai_config.yml")):
                status = get_ai_status()
                assert status["configured"] is False
                assert status["source"] == "none"


class TestGetProviders:
    def test_returns_providers_list(self):
        providers = get_providers()
        assert isinstance(providers, list)
        assert len(providers) > 0
        assert providers[0]["recommended"] is True

    def test_provider_has_required_fields(self):
        providers = get_providers()
        for p in providers:
            assert "id" in p
            assert "name" in p
            assert "description" in p
            assert "recommended" in p
