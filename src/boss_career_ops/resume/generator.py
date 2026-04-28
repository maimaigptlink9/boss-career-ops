import re
from typing import Any

from boss_career_ops.config.settings import Settings
from boss_career_ops.evaluator.utils import extract_jd_text


class ResumeGenerator:
    def __init__(self):
        self._settings = Settings()

    def generate(self, job: dict) -> str:
        cv = self._settings.cv_content
        profile = self._settings.profile
        if not cv:
            return ""
        return self._customize_cv(cv, job, profile)

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
        header = f"<!-- 针对 {job.get('job_name', '')} @ {job.get('company_name', '')} 定制 -->"
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
        return extract_jd_text(job)

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
