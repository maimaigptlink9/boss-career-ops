import re
from typing import Any


ATS_KEYWORD_CATEGORIES = {
    "技术栈": [
        "Python", "Java", "Go", "Golang", "Rust", "C++", "JavaScript", "TypeScript",
        "React", "Vue", "Angular", "Node.js", "Django", "Flask", "FastAPI",
        "Spring", "Spring Boot", "Kubernetes", "Docker", "AWS", "Azure", "GCP",
        "MySQL", "PostgreSQL", "Redis", "MongoDB", "Kafka", "RabbitMQ",
    ],
    "方法论": [
        "Agile", "Scrum", "CI/CD", "DevOps", "TDD", "BDD", "Microservices",
        "RESTful", "GraphQL", "SOLID", "Design Pattern",
    ],
    "软技能": [
        "团队协作", "沟通能力", "项目管理", "领导力", "问题解决", "跨部门",
    ],
}


class KeywordInjector:
    def extract_from_jd(self, jd_text: str) -> list[str]:
        keywords = []
        jd_lower = jd_text.lower()
        for category, words in ATS_KEYWORD_CATEGORIES.items():
            for word in words:
                if word.lower() in jd_lower:
                    keywords.append(word)
        return keywords

    def inject(self, resume_md: str, keywords: list[str]) -> str:
        existing_words = set(re.findall(r"\b\w+\b", resume_md.lower()))
        missing = [kw for kw in keywords if kw.lower() not in existing_words]
        if not missing:
            return resume_md
        injection = "\n\n<!-- ATS 关键词 -->\n"
        injection += " ".join(missing)
        return resume_md + injection
