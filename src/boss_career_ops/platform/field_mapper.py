from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any

from boss_career_ops.platform.models import ChatMessage, Contact, Job


class FieldMapper(ABC):

    @abstractmethod
    def map_job(self, raw_data: dict[str, Any]) -> Job:
        ...

    @abstractmethod
    def map_chat_message(self, raw_data: dict[str, Any]) -> ChatMessage:
        ...

    @abstractmethod
    def map_contact(self, raw_data: dict[str, Any]) -> Contact:
        ...


def _parse_salary(salary_desc: str) -> tuple[int, int, int] | None:
    salary_desc = salary_desc.strip()
    if salary_desc in ("面议", "薪资面议", "negotiable"):
        return None
    months = 12
    month_match = re.search(r'(\d+)薪', salary_desc)
    if month_match:
        months = int(month_match.group(1))
    match = re.findall(r'(\d+)\s*[Kk]?\s*[\-~—]\s*(\d+)\s*[Kk]?', salary_desc)
    if match:
        low, high = match[0]
        has_k = bool(re.search(r'\d+\s*[Kk]', salary_desc))
        multiplier = 1000 if has_k else 1
        return int(low) * multiplier, int(high) * multiplier, months
    single = re.findall(r'(\d+)\s*[Kk]', salary_desc)
    if len(single) >= 2:
        return int(single[0]) * 1000, int(single[1]) * 1000, months
    return None


class BossFieldMapper(FieldMapper):

    def map_job(self, raw_data: dict[str, Any]) -> Job:
        salary_desc = str(raw_data.get("salaryDesc", ""))
        salary_range = _parse_salary(salary_desc) if salary_desc else None
        salary_min = salary_range[0] if salary_range else None
        salary_max = salary_range[1] if salary_range else None
        salary_months = salary_range[2] if salary_range else 12

        skills_raw = raw_data.get("skills", "")
        if isinstance(skills_raw, str):
            skills = [s.strip() for s in skills_raw.split(",") if s.strip()] if skills_raw else []
        elif isinstance(skills_raw, list):
            skills = [str(s) for s in skills_raw]
        else:
            skills = []

        job_labels_raw = raw_data.get("jobLabels", [])
        if isinstance(job_labels_raw, list):
            job_labels = [str(l) for l in job_labels_raw]
        elif isinstance(job_labels_raw, str):
            job_labels = [l.strip() for l in job_labels_raw.split("，") if l.strip()]
        else:
            job_labels = []

        return Job(
            job_id=str(raw_data.get("encryptJobId", "")),
            security_id=str(raw_data.get("securityId", "")),
            job_name=str(raw_data.get("jobName", "")),
            company_name=str(raw_data.get("brandName", "")),
            salary_desc=salary_desc,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_months=salary_months,
            city_name=str(raw_data.get("cityName", "")),
            experience=str(raw_data.get("jobExperience", "")),
            education=str(raw_data.get("jobDegree", "")),
            skills=skills,
            job_labels=job_labels,
            description=str(raw_data.get("postDescription", "")),
            brand_stage=str(raw_data.get("brandStageName", "")),
            brand_scale=str(raw_data.get("brandScaleName", "")),
            brand_industry=str(raw_data.get("brandIndustry", "")),
            raw_data=dict(raw_data),
        )

    def map_chat_message(self, raw_data: dict[str, Any]) -> ChatMessage:
        return ChatMessage(
            security_id=str(raw_data.get("securityId", "")),
            sender_name=str(raw_data.get("senderName", "")),
            content=str(raw_data.get("content", "")),
            time=str(raw_data.get("time", "")),
            raw_data=dict(raw_data),
        )

    def map_contact(self, raw_data: dict[str, Any]) -> Contact:
        return Contact(
            security_id=str(raw_data.get("securityId", "")),
            name=str(raw_data.get("name", "")),
            last_message=str(raw_data.get("lastContent", "")),
            time=str(raw_data.get("time", "")),
            raw_data=dict(raw_data),
        )
