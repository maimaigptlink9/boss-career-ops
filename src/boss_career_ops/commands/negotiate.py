from boss_career_ops.boss.api.client import BossClient
from boss_career_ops.ai.provider import get_provider
from boss_career_ops.config.settings import Settings
from boss_career_ops.display.output import output_json, output_error
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)


def run_negotiate(job_id: str):
    client = BossClient()
    settings = Settings()
    try:
        resp = client.get("job_detail", params={"jobId": job_id})
        if resp.get("code") != 0:
            output_error(command="negotiate", message="获取职位详情失败", code="DETAIL_ERROR")
            return
        job = resp.get("zpData", {}).get("jobInfo", {})
        negotiation = _generate_negotiation(job, settings)
        output_json(
            command="negotiate",
            data=negotiation,
            hints={"next_actions": ["bco pipeline", "bco interview <jid>"]},
        )
    except Exception as e:
        output_error(command="negotiate", message=str(e), code="NEGOTIATE_ERROR")


def _generate_negotiation(job: dict, settings) -> dict:
    salary_desc = job.get("salaryDesc", "")
    profile = settings.profile
    expected = profile.expected_salary
    provider = get_provider()
    if provider is not None:
        try:
            ai_result = _ai_negotiate(provider, job, profile, salary_desc)
            if ai_result:
                ai_result["source"] = "ai"
                return ai_result
        except Exception as e:
            logger.warning("AI 谈判辅助失败，回退到规则模板: %s", e)
    strategies = _rule_strategies(expected, salary_desc)
    return {
        "job_name": job.get("jobName", ""),
        "company_name": job.get("brandName", ""),
        "salary_range": salary_desc,
        "expected_salary": f"{expected.min}-{expected.max}K" if expected.max > 0 else "未设置",
        "strategies": strategies,
        "scripts": [
            "「基于我的经验和市场行情，我期望的薪资范围是 X-YK，您看是否有空间？」",
            "我非常看好这个机会，如果薪资能达到 XK，我可以立即确认。」",
            "「除了基础薪资，我想了解一下期权、签字费等其他福利安排。」",
        ],
        "market_reference": "建议在 BOSS 直聘、拉勾、脉脉等平台查询同岗位薪资范围",
        "source": "rule",
    }


def _ai_negotiate(provider, job: dict, profile, salary_desc: str) -> dict | None:
    import json as _json
    system_prompt = (
        "你是 BOSS 直聘求职助手，专注薪资谈判。请根据职位信息和求职者期望生成谈判策略，"
        "输出 JSON 格式："
        '{"strategies":["策略1","策略2","策略3","策略4","策略5"],'
        '"scripts":["话术1","话术2","话术3"],'
        '"market_analysis":"市场分析",'
        '"counter_offer_range":"建议报价范围",'
        '"red_flags":["注意点1","注意点2"]}'
    )
    expected_str = f"{profile.expected_salary.min}-{profile.expected_salary.max}K" if profile.expected_salary.max > 0 else "未设置"
    skills_str = ", ".join(profile.skills) if profile.skills else "未提供"
    user_prompt = (
        f"职位: {job.get('jobName', '')}\n"
        f"公司: {job.get('brandName', '')}\n"
        f"薪资范围: {salary_desc}\n"
        f"求职者期望: {expected_str}\n"
        f"求职者技能: {skills_str}\n"
        f"经验年限: {profile.experience_years}年"
    )
    result = provider.chat(system_prompt, user_prompt)
    data = _json.loads(result) if isinstance(result, str) else None
    if data and isinstance(data, dict):
        data["job_name"] = job.get("jobName", "")
        data["company_name"] = job.get("brandName", "")
        data["salary_range"] = salary_desc
        data["expected_salary"] = expected_str
        return data
    return None


def _rule_strategies(expected, salary_desc: str) -> list[str]:
    strategies = []
    if expected.max > 0:
        strategies.append(f"锚定高位：先提出 {expected.max}K，留出谈判空间")
        strategies.append(f"底线坚守：低于 {expected.min}K 不接受")
    else:
        strategies.append("先让对方报价，了解预算范围")
        strategies.append("根据市场行情合理报价")
    strategies.extend([
        "多维度谈判：薪资不够，争取期权/签字费/远程/灵活工时",
        "竞品对比：提及其他 offer 作为谈判筹码",
        "地理折扣：如果异地，要求搬迁补贴或远程工作",
        "绩效挂钩：基础薪资低时，争取高绩效奖金比例",
    ])
    return strategies
