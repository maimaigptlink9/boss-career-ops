from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Job:
    job_id: str = ""
    security_id: str = ""
    job_name: str = ""
    company_name: str = ""
    salary_desc: str = ""
    salary_min: int | None = None
    salary_max: int | None = None
    salary_months: int = 12
    city_name: str = ""
    experience: str = ""
    education: str = ""
    skills: list[str] = field(default_factory=list)
    job_labels: list[str] = field(default_factory=list)
    description: str = ""
    brand_stage: str = ""
    brand_scale: str = ""
    brand_industry: str = ""
    raw_data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "security_id": self.security_id,
            "job_name": self.job_name,
            "company_name": self.company_name,
            "salary_desc": self.salary_desc,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "salary_months": self.salary_months,
            "city_name": self.city_name,
            "experience": self.experience,
            "education": self.education,
            "skills": self.skills,
            "job_labels": self.job_labels,
            "description": self.description,
            "brand_stage": self.brand_stage,
            "brand_scale": self.brand_scale,
            "brand_industry": self.brand_industry,
        }

    @classmethod
    def normalize(cls, job: Job | dict[str, Any]) -> Job:
        if isinstance(job, Job):
            return job
        if not isinstance(job, dict):
            raise TypeError(f"不支持的职位数据类型: {type(job)}")
        _BOSS_KEYS = {"encryptJobId", "jobName", "brandName", "salaryDesc"}
        if _BOSS_KEYS & job.keys():
            from boss_career_ops.platform.field_mapper import BossFieldMapper
            return BossFieldMapper().map_job(job)
        valid = {k: v for k, v in job.items() if k in cls.__dataclass_fields__}
        if "raw_data" not in valid:
            valid["raw_data"] = dict(job)
        return cls(**valid)


@dataclass
class ChatMessage:
    security_id: str = ""
    sender_name: str = ""
    content: str = ""
    time: str = ""
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class Contact:
    security_id: str = ""
    name: str = ""
    last_message: str = ""
    time: str = ""
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class AuthStatus:
    ok: bool = False
    missing: list[str] = field(default_factory=list)
    message: str = ""


@dataclass
class OperationResult:
    ok: bool = False
    message: str = ""
    code: str = ""
    data: dict[str, Any] = field(default_factory=dict)
