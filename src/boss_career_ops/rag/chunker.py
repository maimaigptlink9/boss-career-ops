import re

from boss_career_ops.rag.schemas import InterviewExperience, JDDocument, ResumeTemplate


def chunk_jd(doc: JDDocument) -> list[dict]:
    return [
        {
            "content": doc.content,
            "metadata": {
                "doc_id": doc.doc_id,
                "job_name": doc.job_name,
                "company_name": doc.company_name,
                "city": doc.city,
                "salary_min": doc.salary_min,
                "salary_max": doc.salary_max,
                "skills": ",".join(doc.skills),
                "industry": doc.industry,
                "score": doc.score,
                "grade": doc.grade,
            },
        }
    ]


def chunk_resume(doc: ResumeTemplate) -> list[dict]:
    sections = re.split(r"(?=^## )", doc.content, flags=re.MULTILINE)
    chunks = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        header_match = re.match(r"^## (.+)", section)
        section_name = header_match.group(1).strip() if header_match else "概述"
        chunks.append(
            {
                "content": section,
                "metadata": {
                    "doc_id": doc.doc_id,
                    "job_name": doc.job_name,
                    "company_name": doc.company_name,
                    "result": doc.result,
                    "keywords": ",".join(doc.keywords),
                    "section_name": section_name,
                },
            }
        )
    if not chunks:
        chunks.append(
            {
                "content": doc.content,
                "metadata": {
                    "doc_id": doc.doc_id,
                    "job_name": doc.job_name,
                    "company_name": doc.company_name,
                    "result": doc.result,
                    "keywords": ",".join(doc.keywords),
                    "section_name": "全文",
                },
            }
        )
    return chunks


def chunk_interview(doc: InterviewExperience) -> list[dict]:
    return [
        {
            "content": doc.content,
            "metadata": {
                "doc_id": doc.doc_id,
                "company_name": doc.company_name,
                "job_name": doc.job_name,
                "questions": "|".join(doc.questions),
                "result": doc.result,
            },
        }
    ]
