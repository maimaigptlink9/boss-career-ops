import re
from typing import Any

from boss_career_ops.evaluator.dimensions import Dimension
from boss_career_ops.evaluator.scorer import calculate_weighted_score, score_to_grade, grade_label, get_recommendation
from boss_career_ops.config.settings import Settings
from boss_career_ops.display.logger import get_logger
from boss_career_ops.platform.models import Job
from boss_career_ops.platform.field_mapper import _parse_salary

logger = get_logger(__name__)

SKILL_SYNONYMS: dict[str, list[str]] = {
    "go": ["golang", "go语言"],
    "k8s": ["kubernetes"],
    "js": ["javascript"],
    "ts": ["typescript"],
    "py": ["python"],
    "rn": ["react native"],
    "pg": ["postgresql"],
    "mysql": ["mariadb"],
    "cv": ["opencv", "computer vision"],
    "ml": ["machine learning"],
    "dl": ["deep learning"],
    "nlp": ["natural language processing"],
    "devops": ["sre", "platform engineering"],
    "kafka": ["apache kafka"],
    "es": ["elasticsearch"],
}

EDUCATION_LEVELS: dict[str, int] = {
    "初中": 1, "中专": 2, "高中": 2, "大专": 3, "专科": 3,
    "本科": 4, "硕士": 5, "博士": 6,
}

def _skill_matches_jd(skill: str, jd_text: str) -> bool:
    jd_lower = jd_text.lower()
    skill_lower = skill.lower()
    variants = [skill_lower] + [s.lower() for s in SKILL_SYNONYMS.get(skill_lower, [])]
    for variant in variants:
        pattern = rf'\b{re.escape(variant)}\b'
        if re.search(pattern, jd_lower):
            return True
    return False


class EvaluationEngine:
    def __init__(self):
        self._settings = Settings()

    def evaluate(self, job: Job | dict[str, Any]) -> dict:
        job = Job.normalize(job)
        profile = self._settings.profile
        cv = self._settings.cv_content
        scores = {
            Dimension.MATCH.value: self._score_match(job),
            Dimension.SALARY.value: self._score_salary(job),
            Dimension.LOCATION.value: self._score_location(job),
            Dimension.GROWTH.value: self._score_growth(job),
            Dimension.TEAM.value: self._score_team(job),
        }
        total = calculate_weighted_score(scores)
        grade = score_to_grade(total)
        result = {
            "scores": scores,
            "total_score": total,
            "grade": grade,
            "grade_label": grade_label(grade),
            "recommendation": get_recommendation(grade),
            "job_name": job.job_name,
            "company_name": job.company_name,
            "salary_desc": job.salary_desc,
        }
        hints = []
        if not profile.skills and not cv:
            hints.append("⚠️ profile.skills 为空，匹配度评分不可靠，请运行 bco setup 配置")
        if profile.expected_salary.min == 0 and profile.expected_salary.max == 0:
            hints.append("⚠️ expected_salary 未设置，薪资评分默认 3.0")
        if not profile.preferred_cities:
            hints.append("⚠️ preferred_cities 未设置，地点评分默认 3.0")
        if hints:
            result["hints"] = hints
        return result

    def _score_match(self, job: Job) -> float:
        profile = self._settings.profile
        cv = self._settings.cv_content
        if not profile.skills and not cv:
            return 2.5
        title = job.job_name
        skills_field = ",".join(job.skills) if job.skills else ""
        description = job.description
        title_matches = sum(1 for s in profile.skills if _skill_matches_jd(s, title))
        skills_matches = sum(1 for s in profile.skills if _skill_matches_jd(s, skills_field))
        desc_matches = sum(1 for s in profile.skills if _skill_matches_jd(s, description))
        total_skills = len(profile.skills) if profile.skills else 1
        weighted = title_matches * 1.5 + skills_matches * 1.0 + desc_matches * 0.5
        max_weighted = total_skills * 1.5
        skill_score = weighted / max_weighted if max_weighted > 0 else 0.5
        score = 1.0 + skill_score * 3.0
        if profile.education:
            user_level = EDUCATION_LEVELS.get(profile.education, 0)
            if user_level > 0:
                jd_text = self._extract_jd_text(job)
                jd_level = 0
                for edu_name, level in EDUCATION_LEVELS.items():
                    if edu_name in jd_text and level > jd_level:
                        jd_level = level
                if jd_level == 0 or user_level >= jd_level:
                    score += 0.5
        if profile.experience_years > 0:
            exp_required = job.experience
            if not exp_required or "不限" in exp_required:
                score += 0.3
        return min(5.0, max(0.0, round(score, 2)))

    def _score_salary(self, job: Job) -> float:
        profile = self._settings.profile
        job_min = job.salary_min
        job_max = job.salary_max
        months = job.salary_months
        if job_min is None or job_max is None:
            salary_desc = job.salary_desc
            if salary_desc:
                salary_range = _parse_salary(salary_desc)
                if salary_range:
                    job_min, job_max, months = salary_range
        if job_min is None or job_max is None:
            return 2.5
        annual_min = job_min * months
        annual_max = job_max * months
        expected_min = profile.expected_salary.min
        expected_max = profile.expected_salary.max
        if expected_min == 0 and expected_max == 0:
            return 3.0
        if annual_max >= expected_max * 12:
            return 4.5
        if annual_min >= expected_min * 12:
            return 4.0
        if annual_max >= expected_min * 12:
            return 3.0
        ratio = annual_max / (expected_min * 12) if expected_min > 0 else 0.5
        return min(5.0, max(0.0, round(ratio * 3.0, 2)))

    def _score_location(self, job: Job) -> float:
        profile = self._settings.profile
        city_name = job.city_name
        if not city_name and not profile.preferred_cities:
            return 3.0
        if not profile.preferred_cities:
            return 3.0
        if city_name in profile.preferred_cities:
            return 4.5
        job_labels = job.job_labels or []
        if profile.remote_ok and any("远程" in str(l) for l in job_labels):
            return 4.0
        return 2.0

    def _score_growth(self, job: Job) -> float:
        score = 3.0
        jd_text = self._extract_jd_text(job)
        growth_keywords = ["晋升", "成长", "培训", "技术栈", "架构", "负责人", "lead", "管理"]
        for kw in growth_keywords:
            if kw.lower() in jd_text.lower():
                score += 0.3
        brand_stage = job.brand_stage
        if brand_stage in ["A轮", "B轮", "C轮", "D轮及以上"]:
            score += 0.5
        elif brand_stage == "已上市":
            score += 0.3
        return min(5.0, max(0.0, round(score, 2)))

    def _score_team(self, job: Job) -> float:
        score = 3.0
        brand_scale = job.brand_scale
        if brand_scale in ["100-499人", "500-999人"]:
            score += 0.5
        elif brand_scale in ["1000-9999人", "10000人以上"]:
            score += 0.3
        brand_industry = job.brand_industry
        profile = self._settings.profile
        if profile.career_goals and brand_industry.lower() in profile.career_goals.lower():
            score += 0.5
        if profile.avoid:
            avoid_items = [a.strip() for a in profile.avoid.split(",") if a.strip()]
            for item in avoid_items:
                if item.lower() in (brand_industry or "").lower():
                    score -= 1.0
        return min(5.0, max(0.0, round(score, 2)))

    def _extract_jd_text(self, job: Job) -> str:
        parts = [
            job.job_name,
            ",".join(job.job_labels) if job.job_labels else "",
            ",".join(job.skills) if job.skills else "",
            job.experience,
            job.education,
            job.description,
        ]
        return " ".join(str(p) for p in parts if p)

