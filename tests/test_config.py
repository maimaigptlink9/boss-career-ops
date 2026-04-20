import tempfile
from pathlib import Path
from unittest.mock import patch

from boss_career_ops.config.settings import Settings, Profile, SalaryExpectation
from boss_career_ops.config.thresholds import Thresholds, AutoActionThresholds, RateLimitConfig, CacheConfig


class TestProfile:
    def test_default_values(self):
        p = Profile()
        assert p.name == ""
        assert p.skills == []
        assert p.expected_salary.min == 0
        assert p.expected_salary.max == 0
        assert p.remote_ok is False

    def test_custom_values(self):
        p = Profile(
            name="张三",
            title="Golang工程师",
            experience_years=5,
            skills=["Go", "Docker"],
            expected_salary=SalaryExpectation(min=25000, max=40000),
            preferred_cities=["广州", "深圳"],
            remote_ok=True,
        )
        assert p.name == "张三"
        assert len(p.skills) == 2
        assert p.expected_salary.min == 25000


class TestSettings:
    def test_load_without_config_file(self, tmp_dir):
        s = Settings(
            profile_path=str(tmp_dir / "no_profile.yml"),
            thresholds_path=str(tmp_dir / "no_thresholds.yml"),
            cv_path=str(tmp_dir / "no_cv.md"),
        )
        assert s.profile.name == ""
        assert s.cv_content == ""

    def test_load_with_profile(self, tmp_dir):
        profile_path = tmp_dir / "profile.yml"
        profile_path.write_text("""
name: 测试
title: 工程师
experience_years: 3
skills:
  - Go
  - Python
expected_salary:
  min: 20000
  max: 35000
preferred_cities:
  - 广州
remote_ok: true
education: 本科
""", encoding="utf-8")
        s = Settings(
            profile_path=str(profile_path),
            thresholds_path=str(tmp_dir / "no_thresholds.yml"),
            cv_path=str(tmp_dir / "no_cv.md"),
        )
        assert s.profile.name == "测试"
        assert s.profile.skills == ["Go", "Python"]
        assert s.profile.expected_salary.min == 20000
        assert s.profile.remote_ok is True

    def test_load_with_cv(self, tmp_dir):
        cv_path = tmp_dir / "cv.md"
        cv_path.write_text("# 张三的简历\n\n## 技能\n- Go", encoding="utf-8")
        s = Settings(
            profile_path=str(tmp_dir / "no_profile.yml"),
            thresholds_path=str(tmp_dir / "no_thresholds.yml"),
            cv_path=str(cv_path),
        )
        assert "张三" in s.cv_content
        assert s.cv_configured is True

    def test_profile_configured_false(self, tmp_dir):
        s = Settings(
            profile_path=str(tmp_dir / "no_profile.yml"),
            thresholds_path=str(tmp_dir / "no_thresholds.yml"),
            cv_path=str(tmp_dir / "no_cv.md"),
        )
        assert s.profile_configured is False

    def test_profile_configured_true(self, tmp_dir):
        cv_path = tmp_dir / "cv.md"
        cv_path.write_text("# 简历", encoding="utf-8")
        s = Settings(
            profile_path=str(tmp_dir / "no_profile.yml"),
            thresholds_path=str(tmp_dir / "no_thresholds.yml"),
            cv_path=str(cv_path),
        )
        assert s.profile_configured is True

    def test_reload(self, tmp_dir):
        cv_path = tmp_dir / "cv.md"
        cv_path.write_text("v1", encoding="utf-8")
        s = Settings(
            profile_path=str(tmp_dir / "no_profile.yml"),
            thresholds_path=str(tmp_dir / "no_thresholds.yml"),
            cv_path=str(cv_path),
        )
        assert s.cv_content == "v1"
        cv_path.write_text("v2", encoding="utf-8")
        s.reload()
        assert s.cv_content == "v2"


class TestThresholds:
    def test_defaults_without_file(self, tmp_dir):
        t = Thresholds(thresholds_path=str(tmp_dir / "no.yml"))
        assert t.auto_action.auto_greet_threshold == 4.0
        assert t.auto_action.auto_apply_threshold == 4.5
        assert t.auto_action.skip_threshold == 2.0
        assert t.rate_limit.batch_greet_max == 10
        assert t.cache.default_ttl == 3600

    def test_load_from_file(self, tmp_dir):
        path = tmp_dir / "thresholds.yml"
        path.write_text("""
auto_action:
  auto_greet_threshold: 3.5
  auto_apply_threshold: 4.0
  skip_threshold: 1.5
  confirm_required: false
rate_limit:
  batch_greet_max: 5
cache:
  default_ttl: 7200
""", encoding="utf-8")
        t = Thresholds(thresholds_path=str(path))
        assert t.auto_action.auto_greet_threshold == 3.5
        assert t.auto_action.confirm_required is False
        assert t.rate_limit.batch_greet_max == 5
        assert t.cache.default_ttl == 7200

    def test_reload(self, tmp_dir):
        path = tmp_dir / "thresholds.yml"
        path.write_text("auto_action:\n  auto_greet_threshold: 3.0\n", encoding="utf-8")
        t = Thresholds(thresholds_path=str(path))
        assert t.auto_action.auto_greet_threshold == 3.0
        path.write_text("auto_action:\n  auto_greet_threshold: 4.5\n", encoding="utf-8")
        t.reload()
        assert t.auto_action.auto_greet_threshold == 4.5


class TestAutoActionThresholds:
    def test_defaults(self):
        a = AutoActionThresholds()
        assert a.auto_greet_threshold == 4.0
        assert a.auto_apply_threshold == 4.5
        assert a.skip_threshold == 2.0
        assert a.confirm_required is True


class TestRateLimitConfig:
    def test_defaults(self):
        r = RateLimitConfig()
        assert r.request_delay_min == 1.5
        assert r.batch_greet_max == 10
        assert r.retry_max_attempts == 3
        assert r.retry_base_delay == 5.0
        assert r.retry_max_delay == 60.0
        assert r.search_page_delay_min == 3.0
        assert r.search_page_delay_max == 6.0
        assert r.search_max_pages == 5


class TestCacheConfig:
    def test_defaults(self):
        c = CacheConfig()
        assert c.default_ttl == 3600
        assert c.search_ttl == 1800
