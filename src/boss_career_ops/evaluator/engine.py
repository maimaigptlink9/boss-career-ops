import re
from pathlib import Path
from typing import Any

import yaml

from boss_career_ops.evaluator.dimensions import Dimension
from boss_career_ops.evaluator.scorer import calculate_weighted_score, score_to_grade, grade_label, get_recommendation
from boss_career_ops.evaluator.utils import extract_jd_text
from boss_career_ops.config.settings import Settings, BCO_HOME, CONFIG_DIR
from boss_career_ops.display.logger import get_logger
from boss_career_ops.platform.models import Job
from boss_career_ops.platform.field_mapper import parse_salary

logger = get_logger(__name__)

_SYNONYMS_FILE = Path(__file__).parent.parent / "data" / "skill_synonyms.yml"
_CUSTOM_SYNONYMS_FILE = CONFIG_DIR / "skill_synonyms.yml"

EDUCATION_LEVELS: dict[str, int] = {
    "初中": 1, "中专": 2, "高中": 2, "大专": 3, "专科": 3,
    "本科": 4, "硕士": 5, "博士": 6,
}

NEARBY_CITIES: dict[str, list[str]] = {
    "广州": ["深圳", "佛山", "东莞", "珠海", "中山"],
    "深圳": ["广州", "东莞", "惠州", "珠海"],
    "北京": ["天津", "石家庄", "廊坊"],
    "上海": ["苏州", "杭州", "南京", "无锡", "嘉兴"],
    "杭州": ["上海", "南京", "苏州", "宁波"],
    "成都": ["重庆", "绵阳"],
    "武汉": ["长沙", "郑州", "南昌"],
    "南京": ["上海", "杭州", "苏州", "合肥"],
    "西安": ["郑州", "兰州"],
    "厦门": ["福州", "泉州"],
}

GROWTH_KEYWORDS: dict[str, list[str]] = {
    "技术": ["晋升", "技术栈", "架构", "负责人", "lead", "技术经理", "技术总监", "cto"],
    "产品": ["产品线", "产品矩阵", "产品负责人", "产品总监", "产品规划", "从0到1"],
    "运营": ["运营体系", "运营总监", "增长空间", "业务线", "独立负责", "全栈运营"],
    "市场": ["品牌建设", "市场总监", "cmo", "市场体系", "品牌矩阵", "全渠道"],
    "设计": ["设计体系", "设计规范", "设计负责人", "设计总监", "ux团队", "设计语言"],
    "数据": ["数据体系", "数据团队", "数据负责人", "数据总监", "数据平台", "数据驱动"],
    "管理": ["团队管理", "管理岗", "带团队", "管理经验", "团队建设", "人员管理"],
    "通用": ["成长", "培训", "晋升通道", "职业发展", "内部转岗", "期权", "股权激励", "核心成员"],
}

TEAM_KEYWORDS: dict[str, list[str]] = {
    "技术": ["技术氛围", "开源", "code review", "技术分享", "工程师文化"],
    "产品": ["产品文化", "用户导向", "数据驱动", "快速迭代", "敏捷"],
    "运营": ["结果导向", "目标清晰", "扁平管理", "快速决策"],
    "通用": ["扁平化", "弹性工作", "远程办公", "团队氛围好", "年轻团队", "核心业务"],
}

AVOID_PATTERNS: list[tuple[str, str]] = [
    ("外包", "外包"),
    ("劳务派遣", "劳务派遣"),
    ("代招", "代招"),
    ("驻场", "驻场"),
]


def _skill_matches_jd(skill: str, jd_text: str, synonyms: dict[str, list[str]] | None = None) -> bool:
    jd_lower = jd_text.lower()
    skill_lower = skill.lower()
    syn = synonyms if synonyms is not None else {}
    variants = [skill_lower] + [s.lower() for s in syn.get(skill_lower, [])]
    for variant in variants:
        pattern = rf'\b{re.escape(variant)}\b'
        if re.search(pattern, jd_lower):
            return True
    return False


class EvaluationEngine:
    def __init__(self):
        self._settings = Settings()
        self._synonyms = self._load_synonyms()

    def _load_synonyms(self) -> dict[str, list[str]]:
        data: dict[str, list[str]] = {}
        try:
            with open(_SYNONYMS_FILE, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
        except FileNotFoundError:
            raw = {}
        for key, val in raw.items():
            if isinstance(val, list):
                data[str(key)] = val
            elif isinstance(val, str):
                data[str(key)] = [val]
        if _CUSTOM_SYNONYMS_FILE.exists():
            try:
                with open(_CUSTOM_SYNONYMS_FILE, "r", encoding="utf-8") as f:
                    custom = yaml.safe_load(f) or {}
                for key, val in custom.items():
                    syns = val if isinstance(val, list) else [val]
                    if key in data:
                        data[key] = list(set(data[key] + syns))
                    else:
                        data[key] = syns
            except Exception:
                pass
        return data

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
        match_reasons = []
        mismatch_reasons = []
        jd_text = self._extract_jd_text(job)
        matched_skills = [s for s in profile.skills if _skill_matches_jd(s, jd_text, self._synonyms)]
        missing_skills = [s for s in profile.skills if not _skill_matches_jd(s, jd_text, self._synonyms)]
        if matched_skills:
            match_reasons.append(f"技能匹配: {', '.join(matched_skills)}")
        if missing_skills:
            mismatch_reasons.append(f"技能缺失: {', '.join(missing_skills)}")
        salary_desc = job.salary_desc or ""
        job_min = job.salary_min
        job_max = job.salary_max
        months = job.salary_months
        if (job_min is None or job_max is None) and salary_desc:
            salary_range = parse_salary(salary_desc)
            if salary_range:
                job_min, job_max, months = salary_range
        if job_min is not None and job_max is not None and (profile.expected_salary.min or profile.expected_salary.max):
            annual_max = job_max * months
            expected_max = profile.expected_salary.max or 0
            expected_min = profile.expected_salary.min or 0
            if annual_max >= expected_max * 12:
                match_reasons.append(f"薪资超预期: {salary_desc}")
            elif annual_max < expected_min * 12:
                mismatch_reasons.append(f"薪资低于期望: {salary_desc}，期望 {expected_min // 1000}-{expected_max // 1000}K")
        city_name = job.city_name
        if city_name:
            if city_name in profile.preferred_cities:
                match_reasons.append(f"目标城市: {city_name}")
            else:
                mismatch_reasons.append(f"非目标城市: {city_name}")
        has_description = bool(job.description and job.description.strip())
        result = {
            "scores": scores,
            "total_score": total,
            "grade": grade,
            "grade_label": grade_label(grade),
            "recommendation": get_recommendation(grade),
            "job_name": job.job_name,
            "company_name": job.company_name,
            "salary_desc": job.salary_desc,
            "match_reasons": match_reasons,
            "mismatch_reasons": mismatch_reasons,
            "confidence": "full" if has_description else "preliminary",
            "confidence_note": "" if has_description else "基于标题和技能列表的初步评估，查看详情后评分可能变化",
        }
        hints = []
        if not profile.skills and not cv:
            hints.append("⚠️ profile.skills 为空，匹配度评分不可靠，请运行 bco setup 配置")
        if not profile.expected_salary.min and not profile.expected_salary.max:
            hints.append("⚠️ expected_salary 未设置，薪资评分默认 1.0")
        if not profile.preferred_cities:
            hints.append("⚠️ preferred_cities 未设置，地点评分默认 1.0")
        if hints:
            result["hints"] = hints
        return result

    def _detect_job_category(self, job_name: str) -> str:
        name = job_name.lower()
        domain = None
        if any(kw in name for kw in ["数据分析师", "bi", "数据挖掘"]):
            domain = "数据"
        elif any(kw in name for kw in ["开发", "工程师", "架构", "运维", "测试", "后端", "前端", "算法", "数据开发"]):
            domain = "技术"
        elif any(kw in name for kw in ["产品", "pm"]):
            domain = "产品"
        elif any(kw in name for kw in ["运营", "增长"]):
            domain = "运营"
        elif any(kw in name for kw in ["市场", "品牌", "营销", "投放", "pr"]):
            domain = "市场"
        elif any(kw in name for kw in ["设计", "ui", "ux", "视觉", "交互"]):
            domain = "设计"
        if any(kw in name for kw in ["总监", "主管", "负责人"]):
            return "管理"
        if domain:
            return domain
        if any(kw in name for kw in ["经理"]):
            return "管理"
        return "通用"

    def _score_match(self, job: Job) -> float:
        profile = self._settings.profile
        cv = self._settings.cv_content
        if not profile.skills and not cv:
            return 1.0
        title = job.job_name
        skills_field = ",".join(job.skills) if job.skills else ""
        description = job.description
        title_matches = sum(1 for s in profile.skills if _skill_matches_jd(s, title, self._synonyms))
        skills_matches = sum(1 for s in profile.skills if _skill_matches_jd(s, skills_field, self._synonyms))
        desc_matches = sum(1 for s in profile.skills if _skill_matches_jd(s, description, self._synonyms))
        total_skills = len(profile.skills) if profile.skills else 1
        weighted = title_matches * 1.5 + skills_matches * 1.0 + desc_matches * 0.5
        max_weighted = total_skills * 1.5
        skill_score = weighted / max_weighted if max_weighted > 0 else 0.5
        score = 0.5 + skill_score * 4.0
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
                salary_range = parse_salary(salary_desc)
                if salary_range:
                    job_min, job_max, months = salary_range
        if job_min is None or job_max is None:
            return 1.0
        annual_min = job_min * months
        annual_max = job_max * months
        expected_min = profile.expected_salary.min or 0
        expected_max = profile.expected_salary.max or 0
        if expected_min == 0 and expected_max == 0:
            return 1.0
        if annual_max >= expected_max * 12:
            return 5.0
        if annual_min >= expected_min * 12:
            ratio = (annual_min - expected_min * 12) / max(1, (expected_max - expected_min) * 12)
            return 3.5 + ratio * 1.5
        if annual_max >= expected_min * 12:
            ratio = (annual_max - expected_min * 12) / max(1, (expected_max - expected_min) * 12)
            return 2.0 + ratio * 1.5
        ratio = annual_max / max(1, expected_min * 12)
        return max(0.0, ratio * 2.0)

    def _score_location(self, job: Job) -> float:
        profile = self._settings.profile
        city_name = job.city_name
        if not city_name and not profile.preferred_cities:
            return 1.0
        if not profile.preferred_cities:
            return 1.0
        if city_name in profile.preferred_cities:
            return 5.0
        for city in profile.preferred_cities:
            nearby = NEARBY_CITIES.get(city, [])
            if city_name in nearby:
                return 3.5
        job_labels = job.job_labels or []
        if profile.remote_ok and any("远程" in str(l) for l in job_labels):
            return 3.5
        return 1.0

    def _score_growth(self, job: Job) -> float:
        score = 1.5
        jd_text = self._extract_jd_text(job)
        category = self._detect_job_category(job.job_name)
        keywords = GROWTH_KEYWORDS.get(category, []) + GROWTH_KEYWORDS.get("通用", [])
        for kw in keywords:
            if kw.lower() in jd_text.lower():
                score += 0.4
        brand_stage = job.brand_stage
        if brand_stage in ["A轮", "B轮", "C轮", "D轮及以上"]:
            score += 0.5
        elif brand_stage == "已上市":
            score += 0.3
        return min(5.0, max(0.0, round(score, 2)))

    def _score_team(self, job: Job) -> float:
        score = 1.5
        jd_text = self._extract_jd_text(job)
        category = self._detect_job_category(job.job_name)
        keywords = TEAM_KEYWORDS.get(category, []) + TEAM_KEYWORDS.get("通用", [])
        for kw in keywords:
            if kw.lower() in jd_text.lower():
                score += 0.4
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
                for pattern_name, pattern_text in AVOID_PATTERNS:
                    if item.lower() == pattern_name.lower() and pattern_text.lower() in (brand_industry or "").lower():
                        score -= 1.0
                if item.lower() not in [p[0].lower() for p in AVOID_PATTERNS]:
                    if item.lower() in (brand_industry or "").lower():
                        score -= 1.0
        return min(5.0, max(0.0, round(score, 2)))

    def _extract_jd_text(self, job: Job) -> str:
        return extract_jd_text(job)
