import re
from typing import Any

from boss_career_ops.ai.provider import get_provider
from boss_career_ops.config.settings import Settings
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)


class ResumeGenerator:
    def __init__(self):
        self._settings = Settings()
        self._ai_provider = get_provider()

    def generate(self, job: dict) -> str:
        cv = self._settings.cv_content
        profile = self._settings.profile
        if not cv:
            return self._generate_from_profile(job, profile)
        if self._ai_provider:
            polished = self._ai_polish(cv, job)
            if polished:
                return polished
            logger.warning("AI 润色不可用或失败，回退到规则逻辑")
        return self._customize_cv(cv, job, profile)

    def _ai_polish(self, cv_md: str, job: dict) -> str:
        if not self._ai_provider:
            return ""
        jd_text = self._extract_jd_text(job)
        system_prompt = (
            "你是一位资深简历顾问，擅长根据目标岗位的职位描述（JD）优化求职者的简历。"
            "你的原则：1) 突出与JD匹配的经验和技能；2) 尽量量化成果（数字、百分比）；"
            "3) 将ATS关键词自然融入简历文本；4) 绝不编造不存在的工作经历或技能；"
            "5) 保持原始简历的结构和章节不变；6) 输出纯Markdown格式，不要添加代码块标记。"
        )
        user_prompt = (
            f"请根据以下目标岗位的JD，润色我的简历。\n\n"
            f"## 目标岗位JD\n{jd_text}\n\n"
            f"## 我的原始简历\n{cv_md}\n\n"
            f"请直接输出润色后的完整简历Markdown，不要解释。"
        )
        try:
            result = self._ai_provider.chat(system=system_prompt, user=user_prompt)
            if result and len(result.strip()) > len(cv_md) * 0.3:
                return result.strip()
            logger.warning("AI 润色结果校验失败（空或过短），回退到规则逻辑")
            return ""
        except Exception as e:
            logger.warning("AI 润色调用失败: %s，回退到规则逻辑", e)
            return ""

    def _customize_cv(self, cv: str, job: dict, profile: Any) -> str:
        jd_text = self._extract_jd_text(job)
        jd_skills = self._extract_skills_from_jd(jd_text)
        lines = cv.split("\n")
        result_lines = []
        skills_section_found = False
        for line in lines:
            if "技能" in line and line.strip().startswith("#"):
                skills_section_found = True
                result_lines.append(line)
                for skill in jd_skills:
                    if skill and skill not in cv:
                        result_lines.append(f"- {skill}")
                continue
            result_lines.append(line)
        if not skills_section_found and jd_skills:
            result_lines.append("")
            result_lines.append("## 核心技能")
            for skill in jd_skills:
                result_lines.append(f"- {skill}")
        header = f"<!-- 针对 {job.get('jobName', '')} @ {job.get('brandName', '')} 定制 -->"
        return header + "\n" + "\n".join(result_lines)

    def _generate_from_profile(self, job: dict, profile: Any) -> str:
        lines = []
        lines.append(f"# {profile.name or '求职者'}")
        lines.append("")
        lines.append(f"**{profile.title or '职位'}** | {profile.experience_years} 年经验")
        lines.append("")
        lines.append("## 联系方式")
        lines.append("")
        lines.append("## 核心技能")
        lines.append("")
        for skill in profile.skills:
            lines.append(f"- {skill}")
        lines.append("")
        lines.append("## 工作经历")
        lines.append("")
        lines.append("## 教育背景")
        lines.append("")
        if profile.education:
            lines.append(f"- {profile.education}")
        return "\n".join(lines)

    def _extract_jd_text(self, job: dict) -> str:
        parts = [
            job.get("jobName", ""),
            job.get("skills", ""),
            job.get("postDescription", ""),
            job.get("jobLabels", ""),
        ]
        return " ".join(str(p) for p in parts if p)

    def _extract_skills_from_jd(self, jd_text: str) -> list[str]:
        common_skills = [
            "Python", "Java", "Go", "Golang", "Rust", "C++", "JavaScript", "TypeScript",
            "React", "Vue", "Angular", "Node.js", "Django", "Flask", "FastAPI",
            "Spring", "Spring Boot", "Kubernetes", "Docker", "AWS", "Azure", "GCP",
            "MySQL", "PostgreSQL", "Redis", "MongoDB", "Kafka", "RabbitMQ",
            "Git", "CI/CD", "Linux", "Nginx", "Microservices",
            "Machine Learning", "Deep Learning", "NLP", "Computer Vision",
            "LLM", "AI", "Data Engineering", "ETL",
        ]
        found = []
        jd_lower = jd_text.lower()
        for skill in common_skills:
            if skill.lower() in jd_lower:
                found.append(skill)
        return found
