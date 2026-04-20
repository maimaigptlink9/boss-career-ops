from pathlib import Path
from dataclasses import dataclass

import yaml

from boss_career_ops.config.settings import CONFIG_DIR
from boss_career_ops.config.singleton import SingletonMeta
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AutoActionThresholds:
    auto_greet_threshold: float = 4.0
    auto_apply_threshold: float = 4.5
    skip_threshold: float = 2.0
    confirm_required: bool = True


@dataclass
class RateLimitConfig:
    request_delay_min: float = 1.5
    request_delay_max: float = 3.0
    batch_greet_max: int = 10
    batch_greet_delay_min: float = 2.0
    batch_greet_delay_max: float = 5.0
    burst_penalty_multiplier: float = 2.0
    retry_max_attempts: int = 3
    retry_base_delay: float = 5.0
    retry_max_delay: float = 60.0
    search_page_delay_min: float = 3.0
    search_page_delay_max: float = 6.0
    search_max_pages: int = 5


@dataclass
class CacheConfig:
    default_ttl: int = 3600
    search_ttl: int = 1800


class Thresholds(metaclass=SingletonMeta):

    def __init__(self, thresholds_path: str | None = None):
        self._path = Path(thresholds_path) if thresholds_path else CONFIG_DIR / "thresholds.yml"
        self.auto_action = AutoActionThresholds()
        self.rate_limit = RateLimitConfig()
        self.cache = CacheConfig()
        self._load()

    def _load(self):
        if not self._path.exists():
            return
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            aa = data.get("auto_action", {})
            self.auto_action = AutoActionThresholds(
                auto_greet_threshold=aa.get("auto_greet_threshold", 4.0),
                auto_apply_threshold=aa.get("auto_apply_threshold", 4.5),
                skip_threshold=aa.get("skip_threshold", 2.0),
                confirm_required=aa.get("confirm_required", True),
            )
            rl = data.get("rate_limit", {})
            self.rate_limit = RateLimitConfig(
                request_delay_min=rl.get("request_delay_min", 1.5),
                request_delay_max=rl.get("request_delay_max", 3.0),
                batch_greet_max=rl.get("batch_greet_max", 10),
                batch_greet_delay_min=rl.get("batch_greet_delay_min", 2.0),
                batch_greet_delay_max=rl.get("batch_greet_delay_max", 5.0),
                burst_penalty_multiplier=rl.get("burst_penalty_multiplier", 2.0),
                retry_max_attempts=rl.get("retry_max_attempts", 3),
                retry_base_delay=rl.get("retry_base_delay", 5.0),
                retry_max_delay=rl.get("retry_max_delay", 60.0),
                search_page_delay_min=rl.get("search_page_delay_min", 3.0),
                search_page_delay_max=rl.get("search_page_delay_max", 6.0),
                search_max_pages=rl.get("search_max_pages", 5),
            )
            cc = data.get("cache", {})
            self.cache = CacheConfig(
                default_ttl=cc.get("default_ttl", 3600),
                search_ttl=cc.get("search_ttl", 1800),
            )
        except yaml.YAMLError as e:
            logger.error("阈值配置 YAML 语法错误: %s — %s", self._path, e)
            raise ValueError(f"阈值配置语法错误: {self._path}") from e
        except PermissionError as e:
            logger.error("阈值配置权限不足: %s — %s", self._path, e)
            raise
        except Exception as e:
            logger.error("加载阈值配置异常: %s — %s", self._path, e)

    def reload(self):
        self._load()
