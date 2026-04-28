import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from boss_career_ops.config.settings import Settings, Profile, SalaryExpectation
from boss_career_ops.config.thresholds import Thresholds, AutoActionThresholds, RateLimitConfig, CacheConfig
from boss_career_ops.errors import ConfigError


class TestProfile:
    def test_default_values(self):
        p = Profile()
        assert p.name == ""
        assert p.skills == []
        assert p.expected_salary.min is None
        assert p.expected_salary.max is None
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

    def test_salary_expectation_defaults_are_none(self):
        s = SalaryExpectation()
        assert s.min is None
        assert s.max is None

    def test_negative_experience_years_clamped(self, tmp_dir):
        profile_path = tmp_dir / "profile.yml"
        profile_path.write_text("""
name: 测试
experience_years: -5
""", encoding="utf-8")
        s = Settings(
            profile_path=str(profile_path),
            thresholds_path=str(tmp_dir / "no_thresholds.yml"),
            cv_path=str(tmp_dir / "no_cv.md"),
        )
        assert s.profile.experience_years == 0

    def test_salary_min_exceeds_max_raises_config_error(self, tmp_dir):
        profile_path = tmp_dir / "profile.yml"
        profile_path.write_text("""
expected_salary:
  min: 40000
  max: 20000
""", encoding="utf-8")
        with pytest.raises(ConfigError) as exc_info:
            Settings(
                profile_path=str(profile_path),
                thresholds_path=str(tmp_dir / "no_thresholds.yml"),
                cv_path=str(tmp_dir / "no_cv.md"),
            )
        assert exc_info.value.code == "INVALID_SALARY_RANGE"

    def test_salary_min_equals_max_is_valid(self, tmp_dir):
        profile_path = tmp_dir / "profile.yml"
        profile_path.write_text("""
expected_salary:
  min: 20000
  max: 20000
""", encoding="utf-8")
        s = Settings(
            profile_path=str(profile_path),
            thresholds_path=str(tmp_dir / "no_thresholds.yml"),
            cv_path=str(tmp_dir / "no_cv.md"),
        )
        assert s.profile.expected_salary.min == 20000
        assert s.profile.expected_salary.max == 20000

    def test_salary_max_zero_skips_validation(self, tmp_dir):
        profile_path = tmp_dir / "profile.yml"
        profile_path.write_text("""
expected_salary:
  min: 40000
  max: 0
""", encoding="utf-8")
        s = Settings(
            profile_path=str(profile_path),
            thresholds_path=str(tmp_dir / "no_thresholds.yml"),
            cv_path=str(tmp_dir / "no_cv.md"),
        )
        assert s.profile.expected_salary.min == 40000
        assert s.profile.expected_salary.max == 0

    def test_salary_none_when_not_in_yaml(self, tmp_dir):
        profile_path = tmp_dir / "profile.yml"
        profile_path.write_text("""
name: 测试
""", encoding="utf-8")
        s = Settings(
            profile_path=str(profile_path),
            thresholds_path=str(tmp_dir / "no_thresholds.yml"),
            cv_path=str(tmp_dir / "no_cv.md"),
        )
        assert s.profile.expected_salary.min is None
        assert s.profile.expected_salary.max is None


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

    def test_auto_greet_threshold_below_range_raises(self, tmp_dir):
        path = tmp_dir / "thresholds.yml"
        path.write_text("""
auto_action:
  auto_greet_threshold: -1
""", encoding="utf-8")
        with pytest.raises(ConfigError) as exc_info:
            Thresholds(thresholds_path=str(path))
        assert exc_info.value.code == "INVALID_THRESHOLD_RANGE"
        assert "auto_greet_threshold" in exc_info.value.message

    def test_auto_greet_threshold_above_range_raises(self, tmp_dir):
        path = tmp_dir / "thresholds.yml"
        path.write_text("""
auto_action:
  auto_greet_threshold: 6
""", encoding="utf-8")
        with pytest.raises(ConfigError) as exc_info:
            Thresholds(thresholds_path=str(path))
        assert exc_info.value.code == "INVALID_THRESHOLD_RANGE"

    def test_request_delay_min_below_range_raises(self, tmp_dir):
        path = tmp_dir / "thresholds.yml"
        path.write_text("""
rate_limit:
  request_delay_min: 0.1
""", encoding="utf-8")
        with pytest.raises(ConfigError) as exc_info:
            Thresholds(thresholds_path=str(path))
        assert "request_delay_min" in exc_info.value.message

    def test_request_delay_max_less_than_min_raises(self, tmp_dir):
        path = tmp_dir / "thresholds.yml"
        path.write_text("""
rate_limit:
  request_delay_min: 5.0
  request_delay_max: 2.0
""", encoding="utf-8")
        with pytest.raises(ConfigError) as exc_info:
            Thresholds(thresholds_path=str(path))
        assert "request_delay_max" in exc_info.value.message

    def test_batch_greet_max_below_range_raises(self, tmp_dir):
        path = tmp_dir / "thresholds.yml"
        path.write_text("""
rate_limit:
  batch_greet_max: 0
""", encoding="utf-8")
        with pytest.raises(ConfigError) as exc_info:
            Thresholds(thresholds_path=str(path))
        assert "batch_greet_max" in exc_info.value.message

    def test_batch_greet_max_above_range_raises(self, tmp_dir):
        path = tmp_dir / "thresholds.yml"
        path.write_text("""
rate_limit:
  batch_greet_max: 200
""", encoding="utf-8")
        with pytest.raises(ConfigError) as exc_info:
            Thresholds(thresholds_path=str(path))
        assert "batch_greet_max" in exc_info.value.message

    def test_retry_max_attempts_below_range_raises(self, tmp_dir):
        path = tmp_dir / "thresholds.yml"
        path.write_text("""
rate_limit:
  retry_max_attempts: 0
""", encoding="utf-8")
        with pytest.raises(ConfigError) as exc_info:
            Thresholds(thresholds_path=str(path))
        assert "retry_max_attempts" in exc_info.value.message

    def test_retry_max_attempts_above_range_raises(self, tmp_dir):
        path = tmp_dir / "thresholds.yml"
        path.write_text("""
rate_limit:
  retry_max_attempts: 15
""", encoding="utf-8")
        with pytest.raises(ConfigError) as exc_info:
            Thresholds(thresholds_path=str(path))
        assert "retry_max_attempts" in exc_info.value.message

    def test_valid_boundary_values_pass(self, tmp_dir):
        path = tmp_dir / "thresholds.yml"
        path.write_text("""
auto_action:
  auto_greet_threshold: 0
rate_limit:
  request_delay_min: 0.5
  request_delay_max: 0.5
  batch_greet_max: 1
  retry_max_attempts: 1
""", encoding="utf-8")
        t = Thresholds(thresholds_path=str(path))
        assert t.auto_action.auto_greet_threshold == 0
        assert t.rate_limit.request_delay_min == 0.5
        assert t.rate_limit.batch_greet_max == 1
        assert t.rate_limit.retry_max_attempts == 1


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
