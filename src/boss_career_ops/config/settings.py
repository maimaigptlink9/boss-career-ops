import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any

import yaml

from boss_career_ops.config.singleton import SingletonMeta
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)


BCO_HOME = Path(os.environ.get("BCO_HOME", str(Path.home() / ".bco")))
CONFIG_DIR = BCO_HOME / "config"
CV_PATH = BCO_HOME / "cv.md"
EXPORTS_DIR = BCO_HOME / "exports"
RESUMES_DIR = BCO_HOME / "resumes"




@dataclass
class SalaryExpectation:
    min: int = 0
    max: int = 0


@dataclass
class Profile:
    name: str = ""
    title: str = ""
    experience_years: int = 0
    skills: list[str] = field(default_factory=list)
    expected_salary: SalaryExpectation = field(default_factory=SalaryExpectation)
    preferred_cities: list[str] = field(default_factory=list)
    remote_ok: bool = False
    education: str = ""
    career_goals: str = ""
    avoid: str = ""


class Settings(metaclass=SingletonMeta):

    def __init__(self, profile_path: str | None = None, thresholds_path: str | None = None, cv_path: str | None = None):
        self._profile_path = Path(profile_path) if profile_path else CONFIG_DIR / "profile.yml"
        self._thresholds_path = Path(thresholds_path) if thresholds_path else CONFIG_DIR / "thresholds.yml"
        self._cv_path = Path(cv_path) if cv_path else CV_PATH
        self.profile = self._load_profile()
        self.cv_content = self._load_cv()
        self.platform = self._load_platform()

    def _load_profile(self) -> Profile:
        if not self._profile_path.exists():
            logger.info("配置文件不存在，使用默认值: %s", self._profile_path)
            return Profile()
        try:
            with open(self._profile_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            salary_data = data.get("expected_salary", {})
            return Profile(
                name=data.get("name", ""),
                title=data.get("title", ""),
                experience_years=data.get("experience_years", 0),
                skills=data.get("skills", []),
                expected_salary=SalaryExpectation(
                    min=salary_data.get("min", 0) if isinstance(salary_data, dict) else 0,
                    max=salary_data.get("max", 0) if isinstance(salary_data, dict) else 0,
                ),
                preferred_cities=data.get("preferred_cities", []),
                remote_ok=data.get("remote_ok", False),
                education=data.get("education", ""),
                career_goals=data.get("career_goals", ""),
                avoid=data.get("avoid", ""),
            )
        except FileNotFoundError:
            logger.warning("配置文件消失: %s", self._profile_path)
            return Profile()
        except yaml.YAMLError as e:
            logger.error("配置文件 YAML 语法错误: %s — %s", self._profile_path, e)
            raise ValueError(f"配置文件语法错误: {self._profile_path}") from e
        except PermissionError as e:
            logger.error("配置文件权限不足: %s — %s", self._profile_path, e)
            raise PermissionError(f"无法读取配置文件: {self._profile_path}") from e

    def _load_cv(self) -> str:
        if not self._cv_path.exists():
            return ""
        try:
            with open(self._cv_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            logger.warning("简历文件消失: %s", self._cv_path)
            return ""
        except PermissionError as e:
            logger.error("简历文件权限不足: %s — %s", self._cv_path, e)
            raise

    def _load_platform(self) -> str:
        platform_config = CONFIG_DIR / "platform.yml"
        if platform_config.exists():
            try:
                with open(platform_config, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                return str(data.get("platform", "boss"))
            except Exception:
                pass
        return "boss"


