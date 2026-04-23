from boss_career_ops.display.logger import get_logger
from boss_career_ops.rag.vector_store import VectorStore

logger = get_logger(__name__)


class Retriever:
    def __init__(self):
        self._store = VectorStore()

    def find_similar_jds(self, query: str, n: int = 10, city: str = "", salary_min: int = 0) -> list[dict]:
        filters = {}
        if city:
            filters["city"] = city
        if salary_min > 0:
            filters["salary_min"] = {"$gte": salary_min}
        results = self._store.search_jd(query, n=n, filters=filters if filters else None)
        logger.info("相似 JD 检索: query=%s, 结果=%d 条", query[:20], len(results))
        return results

    def find_matching_resumes(self, jd_text: str, n: int = 5) -> list[dict]:
        results = self._store.search_resume(jd_text, n=n)
        logger.info("匹配简历检索: 结果=%d 条", len(results))
        return results

    def find_interview_tips(self, company: str, job_name: str, n: int = 5) -> list[dict]:
        query = f"{company} {job_name} 面试"
        results = self._store.search_interview(query, n=n)
        logger.info("面试经验检索: company=%s, job=%s, 结果=%d 条", company, job_name, len(results))
        return results

    def get_skill_market_demand(self, skills: list[str]) -> dict[str, int]:
        demand = {}
        for skill in skills:
            try:
                results = self._store.search_jd(skill, n=100)
                demand[skill] = len(results)
            except Exception as e:
                logger.warning("技能需求检索失败 %s: %s", skill, e)
                demand[skill] = 0
        logger.info("技能市场需求: %s", demand)
        return demand
