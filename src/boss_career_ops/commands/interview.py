from boss_career_ops.boss.api.client import BossClient
from boss_career_ops.ai.provider import get_provider
from boss_career_ops.config.settings import Settings
from boss_career_ops.display.output import output_json, output_error
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)


def run_interview(job_id: str):
    client = BossClient()
    settings = Settings()
    try:
        resp = client.get("job_detail", params={"jobId": job_id})
        if resp.get("code") != 0:
            output_error(command="interview", message="获取职位详情失败", code="DETAIL_ERROR")
            return
        job = resp.get("zpData", {}).get("jobInfo", {})
        prep = _generate_interview_prep(job, settings)
        output_json(
            command="interview",
            data=prep,
            hints={"next_actions": ["bco negotiate <jid>", "bco pipeline"]},
        )
    except Exception as e:
        output_error(command="interview", message=str(e), code="INTERVIEW_ERROR")


def _generate_interview_prep(job: dict, settings) -> dict:
    jd_text = _extract_jd_text(job)
    company_info = _extract_company_info(job)
    provider = get_provider()
    if provider is not None:
        try:
            ai_result = _ai_interview_prep(provider, jd_text, company_info, settings)
            if ai_result:
                ai_result["source"] = "ai"
                return ai_result
        except Exception as e:
            logger.warning("AI 面试准备失败，回退到规则模板: %s", e)
    tech_questions = _generate_tech_questions(jd_text)
    star_stories = _generate_star_prompts(settings)
    return {
        "job_name": job.get("jobName", ""),
        "company_name": job.get("brandName", ""),
        "tech_questions": tech_questions,
        "star_stories": star_stories,
        "company_info": company_info,
        "tips": [
            "准备 3-5 个 STAR 故事（情境-任务-行动-结果）",
            "研究公司产品和技术栈",
            "准备反问面试官的问题",
            "了解薪资市场行情",
        ],
        "source": "rule",
    }


def _ai_interview_prep(provider, jd_text: str, company_info: dict, settings) -> dict | None:
    import json as _json
    system_prompt = (
        "你是 BOSS 直聘求职助手，专注面试准备。请根据 JD 和公司信息生成面试准备方案，"
        "输出 JSON 格式："
        '{"tech_questions":["问题1","问题2","问题3","问题4","问题5","问题6"],'
        '"star_stories":["STAR提示1","STAR提示2","STAR提示3"],'
        '"company_research":"公司研究方向",'
        '"reverse_questions":["反问1","反问2","反问3"],'
        '"tips":["提示1","提示2","提示3"]}'
    )
    profile_text = f"求职者技能: {', '.join(settings.profile.skills)}" if settings.profile.skills else ""
    user_prompt = f"JD 内容:\n{jd_text}\n\n公司信息: {company_info}\n{profile_text}"
    result = provider.chat(system_prompt, user_prompt)
    data = _json.loads(result) if isinstance(result, str) else None
    if data and isinstance(data, dict):
        data["company_info"] = company_info
        return data
    return None


def _extract_jd_text(job: dict) -> str:
    parts = [job.get("jobName", ""), job.get("skills", ""), job.get("postDescription", "")]
    return " ".join(str(p) for p in parts if p)


def _generate_tech_questions(jd_text: str) -> list[str]:
    questions = []
    tech_keywords = {
        "Python": ["Python 的 GIL 机制是什么？", "描述 Python 的内存管理机制"],
        "Go": ["Goroutine 和线程的区别？", "Go 的 channel 有哪些使用模式？"],
        "Java": ["JVM 内存模型是怎样的？", "Spring Boot 的自动配置原理"],
        "React": ["React 的虚拟 DOM 原理？", "Hooks 的使用注意事项"],
        "Kubernetes": ["Pod 的生命周期？", "Service 和 Ingress 的区别？"],
        "Docker": ["Docker 的网络模式有哪些？", "多阶段构建的优势"],
        "MySQL": ["索引优化策略？", "事务隔离级别及区别"],
        "Redis": ["Redis 的持久化方案？", "缓存穿透/击穿/雪崩的解决方案"],
        "AI": ["如何评估模型效果？", "过拟合的解决方案"],
        "LLM": ["RAG 的实现流程？", "Prompt Engineering 最佳实践"],
    }
    jd_lower = jd_text.lower()
    for tech, qs in tech_keywords.items():
        if tech.lower() in jd_lower:
            questions.extend(qs)
    if not questions:
        questions = ["请描述你最熟悉的技术栈和项目经验", "如何解决技术难题？举例说明"]
    return questions[:6]


def _generate_star_prompts(settings) -> list[str]:
    return [
        "描述一个你解决过的最复杂的技术问题（S-T-A-R）",
        "描述一次你在团队中发挥关键作用的经历",
        "描述一个你主动推动改进的案例",
        "描述一次你处理紧急线上故障的经历",
        "描述一个你从失败中学到教训的经历",
    ]


def _extract_company_info(job: dict) -> dict:
    return {
        "name": job.get("brandName", ""),
        "industry": job.get("brandIndustry", ""),
        "scale": job.get("brandScaleName", ""),
        "stage": job.get("brandStageName", ""),
    }
