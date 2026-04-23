from dataclasses import dataclass, field


@dataclass
class JDDocument:
    doc_id: str
    content: str
    job_name: str
    company_name: str
    city: str
    salary_min: int
    salary_max: int
    skills: list[str]
    industry: str
    score: float = 0.0
    grade: str = ""


@dataclass
class ResumeTemplate:
    doc_id: str
    content: str
    job_name: str
    company_name: str
    result: str = ""
    keywords: list[str] = field(default_factory=list)


@dataclass
class InterviewExperience:
    doc_id: str
    content: str
    company_name: str
    job_name: str
    questions: list[str] = field(default_factory=list)
    result: str = ""
