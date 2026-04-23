from unittest.mock import patch, MagicMock

from boss_career_ops.boss.auth.token_store import TokenStore


class TestTokenStore:
    def test_save_and_load(self, tmp_dir):
        with patch("boss_career_ops.boss.auth.token_store.TOKEN_DIR", tmp_dir):
            with patch("boss_career_ops.boss.auth.token_store.TOKEN_FILE", tmp_dir / "tokens.enc"):
                with patch("boss_career_ops.boss.auth.token_store.LOCK_FILE", tmp_dir / "tokens.lock"):
                    store = TokenStore()
                    tokens = {"wt2": "test_wt2", "stoken": "test_stoken"}
                    store.save(tokens)
                    loaded = store.load()
                    assert loaded["wt2"] == "test_wt2"
                    assert loaded["stoken"] == "test_stoken"

    def test_load_no_file(self, tmp_dir):
        with patch("boss_career_ops.boss.auth.token_store.TOKEN_DIR", tmp_dir):
            with patch("boss_career_ops.boss.auth.token_store.TOKEN_FILE", tmp_dir / "tokens.enc"):
                store = TokenStore()
                result = store.load()
                assert result is None

    def test_check_quality_valid(self, tmp_dir):
        with patch("boss_career_ops.boss.auth.token_store.TOKEN_DIR", tmp_dir):
            with patch("boss_career_ops.boss.auth.token_store.TOKEN_FILE", tmp_dir / "tokens.enc"):
                with patch("boss_career_ops.boss.auth.token_store.LOCK_FILE", tmp_dir / "tokens.lock"):
                    store = TokenStore()
                    store.save({"wt2": "val", "stoken": "val"})
                    result = store.check_quality()
                    assert result["ok"] is True

    def test_check_quality_missing(self, tmp_dir):
        with patch("boss_career_ops.boss.auth.token_store.TOKEN_DIR", tmp_dir):
            with patch("boss_career_ops.boss.auth.token_store.TOKEN_FILE", tmp_dir / "tokens.enc"):
                store = TokenStore()
                result = store.check_quality()
                assert result["ok"] is False

    def test_check_quality_incomplete(self, tmp_dir):
        with patch("boss_career_ops.boss.auth.token_store.TOKEN_DIR", tmp_dir):
            with patch("boss_career_ops.boss.auth.token_store.TOKEN_FILE", tmp_dir / "tokens.enc"):
                with patch("boss_career_ops.boss.auth.token_store.LOCK_FILE", tmp_dir / "tokens.lock"):
                    store = TokenStore()
                    store.save({"wt2": "val"})
                    result = store.check_quality()
                    assert result["ok"] is False
                    assert "stoken" in result["missing"]
