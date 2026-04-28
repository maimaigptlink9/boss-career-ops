import json

from boss_career_ops.display.logger import get_logger
from boss_career_ops.pipeline.manager import PipelineManager
from boss_career_ops.platform.field_mapper import normalize_skills, parse_salary
from boss_career_ops.rag.embedder import Embedder
from boss_career_ops.rag.schemas import InterviewExperience, JDDocument, ResumeTemplate
from boss_career_ops.rag.vector_store import VectorStore

logger = get_logger(__name__)


class Indexer:
    def __init__(self):
        self._store = VectorStore()
        self._embedder = Embedder()

    def index_from_pipeline(self) -> int:
        count = 0
        with PipelineManager() as pm:
            jobs = pm.list_jobs()
            for job in jobs:
                doc = self._job_to_jd_document(job)
                if doc:
                    try:
                        self._store.add_jd(doc)
                        count += 1
                    except Exception as e:
                        logger.warning("JD 索引失败 %s: %s", job.get("job_id", ""), e)
        logger.info("Pipeline 索引完成: %d 条", count)
        return count

    def index_single_jd(self, job_id: str) -> None:
        with PipelineManager() as pm:
            job = pm.get_job(job_id)
            if not job:
                logger.warning("职位不存在: %s", job_id)
                return
            doc = self._job_to_jd_document(job)
            if doc:
                self._store.add_jd(doc)
                logger.info("单条 JD 索引完成: %s", job_id)

    def index_resume_result(self, job_id: str, resume_md: str, result: str) -> None:
        with PipelineManager() as pm:
            job = pm.get_job(job_id)
            if not job:
                logger.warning("职位不存在: %s", job_id)
                return
            data = json.loads(job.get("data", "{}"))
            doc = ResumeTemplate(
                doc_id=f"resume_{job_id}",
                content=resume_md,
                job_name=job.get("job_name", ""),
                company_name=job.get("company_name", ""),
                result=result,
                keywords=data.get("skills", []),
            )
            self._store.add_resume_template(doc)
            logger.info("简历结果索引完成: %s", job_id)

    def reindex_all(self) -> int:
        self._store._client.delete_collection("jd_knowledge")
        self._store._client.delete_collection("resume_templates")
        self._store._client.delete_collection("interview_experience")
        self._store = VectorStore()
        logger.info("全量重建索引开始")
        return self.index_from_pipeline()

    def _job_to_jd_document(self, job: dict) -> JDDocument | None:
        data = json.loads(job.get("data", "{}"))
        salary_desc = job.get("salary_desc", "")
        salary_range = parse_salary(salary_desc) if salary_desc else None
        salary_min = salary_range[0] if salary_range else 0
        salary_max = salary_range[1] if salary_range else 0

        content_parts = []
        job_name = job.get("job_name", "")
        company_name = job.get("company_name", "")
        if job_name:
            content_parts.append(f"职位: {job_name}")
        if company_name:
            content_parts.append(f"公司: {company_name}")
        if salary_desc:
            content_parts.append(f"薪资: {salary_desc}")
        description = data.get("description", data.get("postDescription", ""))
        if description:
            content_parts.append(description)
        content = "\n".join(content_parts)
        if not content.strip():
            return None

        skills = data.get("skills", [])
        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(",") if s.strip()]

        return JDDocument(
            doc_id=job.get("job_id", ""),
            content=content,
            job_name=job_name,
            company_name=company_name,
            city=data.get("city_name", data.get("cityName", "")),
            salary_min=salary_min,
            salary_max=salary_max,
            skills=skills,
            industry=data.get("brand_industry", data.get("brandIndustry", "")),
            score=job.get("score", 0.0),
            grade=job.get("grade", ""),
        )
