import re
from typing import Any

from boss_career_ops.evaluator.dimensions import Dimension
from boss_career_ops.evaluator.scorer import calculate_weighted_score, score_to_grade, grade_label
from boss_career_ops.config.settings import Settings
from boss_career_ops.display.logger import get_logger

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

    def evaluate(self, job: dict) -> dict:
        scores = {
            Dimension.MATCH.value: self._score_match(job),
            Dimension.SALARY.value: self._score_salary(job),
            Dimension.LOCATION.value: self._score_location(job),
            Dimension.GROWTH.value: self._score_growth(job),
            Dimension.TEAM.value: self._score_team(job),
        }
        total = calculate_weighted_score(scores)
        grade = score_to_grade(total)
        return {
            "scores": scores,
            "total_score": total,
            "grade": grade,
            "grade_label": grade_label(grade),
            "recommendation": self._get_recommendation(grade),
            "job_name": job.get("jobName", ""),
            "company_name": job.get("brandName", ""),
            "salary_desc": job.get("salaryDesc", ""),
        }

    def _score_match(self, job: dict) -> float:
        profile = self._settings.profile
        cv = self._settings.cv_content
        if not profile.skills and not cv:
            return 2.5
        title = str(job.get("jobName", ""))
        skills_field = str(job.get("skills", ""))
        description = str(job.get("postDescription", ""))
        title_matches = sum(1 for s in profile.skills if _skill_matches_jd(s, title))
        skills_matches = sum(1 for s in profile.skills if _skill_matches_jd(s, skills_field))
        desc_matches = sum(1 for s in profile.skills if _skill_matches_jd(s, description))
        total_skills = len(profile.skills) if profile.skills else 1
        weighted = title_matches * 1.5 + skills_matches * 1.0 + desc_matches * 0.5
        max_weighted = total_skills * 1.5
        skill_score = weighted / max_weighted if max_weighted > 0 else 0.5
        score = 1.0 + skill_score * 3.0
        if profile.education and profile.education in self._extract_jd_text(job):
            score += 0.5
        if profile.experience_years > 0:
            exp_required = job.get("jobExperience", "")
            if not exp_required or "不限" in exp_required:
                score += 0.3
        return min(5.0, max(0.0, round(score, 2)))

    def _score_salary(self, job: dict) -> float:
        profile = self._settings.profile
        salary_desc = job.get("salaryDesc", "")
        if not salary_desc:
            return 2.5
        salary_range = self._parse_salary(salary_desc)
        if not salary_range:
            return 2.5
        job_min, job_max, months = salary_range
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

    def _score_location(self, job: dict) -> float:
        profile = self._settings.profile
        city_name = job.get("cityName", "")
        if not city_name and not profile.preferred_cities:
            return 3.0
        if not profile.preferred_cities:
            return 3.0
        if city_name in profile.preferred_cities:
            return 4.5
        job_labels = job.get("jobLabels", []) or []
        if profile.remote_ok and any("远程" in str(l) for l in job_labels):
            return 4.0
        return 2.0

    def _score_growth(self, job: dict) -> float:
        score = 3.0
        jd_text = self._extract_jd_text(job)
        growth_keywords = ["晋升", "成长", "培训", "技术栈", "架构", "负责人", "lead", "管理"]
        for kw in growth_keywords:
            if kw.lower() in jd_text.lower():
                score += 0.3
        brand_stage = job.get("brandStageName", "")
        if brand_stage in ["A轮", "B轮", "C轮", "D轮及以上"]:
            score += 0.5
        elif brand_stage == "已上市":
            score += 0.3
        return min(5.0, max(0.0, round(score, 2)))

    def _score_team(self, job: dict) -> float:
        score = 3.0
        brand_scale = job.get("brandScaleName", "")
        if brand_scale in ["100-499人", "500-999人"]:
            score += 0.5
        elif brand_scale in ["1000-9999人", "10000人以上"]:
            score += 0.3
        brand_industry = job.get("brandIndustry", "")
        profile = self._settings.profile
        if profile.career_goals and brand_industry.lower() in profile.career_goals.lower():
            score += 0.5
        if profile.avoid:
            avoid_items = [a.strip() for a in profile.avoid.split(",") if a.strip()]
            for item in avoid_items:
                if item.lower() in (brand_industry or "").lower():
                    score -= 1.0
        return min(5.0, max(0.0, round(score, 2)))

    def _extract_jd_text(self, job: dict) -> str:
        parts = [
            job.get("jobName", ""),
            job.get("jobLabels", ""),
            job.get("skills", ""),
            job.get("jobExperience", ""),
            job.get("jobDegree", ""),
            job.get("postDescription", ""),
        ]
        return " ".join(str(p) for p in parts if p)

    def _parse_salary(self, salary_desc: str) -> tuple[int, int, int] | None:
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
            low_val = int(low) * multiplier
            high_val = int(high) * multiplier
            return low_val, high_val, months
        single = re.findall(r'(\d+)\s*[Kk]', salary_desc)
        if len(single) >= 2:
            return int(single[0]) * 1000, int(single[1]) * 1000, months
        return None

    def _get_recommendation(self, grade: str) -> str:
        recommendations = {
            "A": "强烈推荐！立即行动，优先投递",
            "B": "值得投入，建议优先处理",
            "C": "一般匹配，需人工判断是否值得投入",
            "D": "匹配度低，谨慎考虑",
            "F": "不推荐，建议跳过",
        }
        return recommendations.get(grade, "未知")
