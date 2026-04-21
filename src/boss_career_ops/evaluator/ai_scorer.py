"""AI 增强的评估引擎"""

import json
from typing import Any

from boss_career_ops.ai.provider import get_provider
from boss_career_ops.config.settings import Settings
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)


class AIEvaluator:
    """使用 AI 进行职位匹配度评估"""

    def __init__(self):
        self._provider = get_provider()
        self._settings = Settings()

    def score_job_match(self, job: dict) -> float:
        """
        使用 AI 评估职位与个人档案的匹配度
        
        Args:
            job: 职位数据（包含 jobName, brandName, salaryDesc 等）
            
        Returns:
            匹配度分数 (0.0 - 5.0)
        """
        if not self._provider:
            logger.warning("AI 未配置，使用规则回退")
            return self._rule_based_score(job)

        profile = self._settings.profile

        # 构建用户画像
        user_profile = {
            "name": profile.name,
            "title": profile.title,
            "experience_years": profile.experience_years,
            "skills": profile.skills,
            "expected_salary": {
                "min": profile.expected_salary.min,
                "max": profile.expected_salary.max,
            },
            "preferred_cities": profile.preferred_cities,
            "education": profile.education,
            "career_goals": profile.career_goals,
        }

        # 构建职位信息
        job_info = {
            "job_name": job.get("jobName", ""),
            "company": job.get("brandName", ""),
            "salary": job.get("salaryDesc", ""),
            "location": job.get("cityName", ""),
            "experience": job.get("jobExperience", ""),
            "education": job.get("jobDegree", ""),
            "skills": job.get("skills", []),
            "industry": job.get("brandIndustry", ""),
            "scale": job.get("brandScaleName", ""),
        }

        system_prompt = """你是一个专业的职位匹配评估专家。你的任务是评估候选人与职位的匹配度。

评分标准（总分 5 分）：
- 5 分：完美匹配，强烈推荐
- 4 分：高度匹配，值得投入
- 3 分：一般匹配，需人工判断
- 2 分：不太匹配，谨慎考虑
- 1 分：不匹配，建议跳过

请综合考虑：
1. 技能匹配度（权重 40%）
2. 经验匹配度（权重 20%）
3. 薪资匹配度（权重 20%）
4. 职业发展匹配度（权重 20%）

只返回一个数字（0.0-5.0），不要返回其他内容。"""

        user_prompt = f"""请评估以下候选人与职位的匹配度：

【候选人档案】
{json.dumps(user_profile, ensure_ascii=False, indent=2)}

【职位信息】
{json.dumps(job_info, ensure_ascii=False, indent=2)}

请返回匹配度分数（0.0-5.0）："""

        try:
            response = self._provider.chat(system_prompt, user_prompt)
            # 解析 AI 返回的分数
            score = self._parse_score(response)
            return round(min(5.0, max(0.0, score)), 2)
        except Exception as e:
            logger.error(f"AI 评估失败：{e}，使用规则回退")
            return self._rule_based_score(job)

    def detailed_evaluate(self, job_detail: dict) -> dict:
        """
        使用 AI 对职位进行详细评估（获取职位详情后）
        
        Args:
            job_detail: 完整的职位详情（包含 postDescription）
            
        Returns:
            评估结果字典
        """
        if not self._provider:
            logger.warning("AI 未配置，使用规则回退")
            return self._rule_based_detailed_eval(job_detail)

        profile = self._settings.profile

        user_profile = {
            "title": profile.title,
            "skills": profile.skills,
            "experience_years": profile.experience_years,
            "education": profile.education,
            "career_goals": profile.career_goals,
            "expected_salary": {
                "min": profile.expected_salary.min,
                "max": profile.expected_salary.max,
            },
        }

        job_info = {
            "job_name": job_detail.get("jobName", ""),
            "company": job_detail.get("brandName", ""),
            "salary": job_detail.get("salaryDesc", ""),
            "description": job_detail.get("postDescription", ""),
            "requirements": job_detail.get("jobLabels", []),
            "experience": job_detail.get("jobExperience", ""),
            "education": job_detail.get("jobDegree", ""),
        }

        system_prompt = """你是一个专业的职位评估专家。请对候选人与职位进行全面评估。

请返回 JSON 格式的评估结果：
{
    "scores": {
        "匹配度": <0.0-5.0>,
        "薪资": <0.0-5.0>,
        "地点": <0.0-5.0>,
        "发展": <0.0-5.0>,
        "团队": <0.0-5.0>
    },
    "grade": "<A/B/C/D/F>",
    "recommendation": "<一句话建议>",
    "analysis": "<200 字以内的分析>"
}

评分标准：
- 匹配度：技能、经验、学历与 JD 的匹配程度
- 薪资：薪资范围与预期的对比
- 地点：通勤距离、城市偏好
- 发展：职业成长空间、技术栈前瞻性
- 团队：公司阶段、团队文化

等级划分：
- A: 4.5-5.0 强烈推荐
- B: 3.5-4.4 值得投入
- C: 2.5-3.4 一般
- D: 1.5-2.4 不太匹配
- F: 0.0-1.4 不推荐"""

        user_prompt = f"""请评估以下职位：

【候选人档案】
{json.dumps(user_profile, ensure_ascii=False, indent=2)}

【职位详情】
{json.dumps(job_info, ensure_ascii=False, indent=2)}

请返回 JSON 格式的评估结果："""

        try:
            response = self._provider.chat(system_prompt, user_prompt)
            # 解析 JSON 响应
            result = self._parse_json_response(response)
            return result
        except Exception as e:
            logger.error(f"AI 详细评估失败：{e}，使用规则回退")
            return self._rule_based_detailed_eval(job_detail)

    def _parse_score(self, response: str) -> float:
        """解析 AI 返回的分数"""
        import re

        # 提取数字
        numbers = re.findall(r"\d+\.?\d*", response)
        if numbers:
            return float(numbers[0])
        return 2.5  # 默认值

    def _parse_json_response(self, response: str) -> dict:
        """解析 AI 返回的 JSON"""
        import re

        # 尝试提取 JSON
        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())

        # 如果解析失败，返回默认值
        return {
            "scores": {
                "匹配度": 2.5,
                "薪资": 2.5,
                "地点": 3.0,
                "发展": 3.0,
                "团队": 3.0,
            },
            "grade": "C",
            "recommendation": "AI 解析失败，建议人工判断",
            "analysis": "",
        }

    def _rule_based_score(self, job: dict) -> float:
        """规则回退：简化的匹配度计算"""
        profile = self._settings.profile
        title = job.get("jobName", "").lower()

        # 简单的关键词匹配
        match_count = sum(1 for skill in profile.skills if skill.lower() in title)
        score = 1.0 + (match_count / max(len(profile.skills), 1)) * 3.0
        return round(min(5.0, max(0.0, score)), 2)

    def _rule_based_detailed_eval(self, job: dict) -> dict:
        """规则回退：详细评估"""
        from boss_career_ops.evaluator.engine import EvaluationEngine

        engine = EvaluationEngine()
        return engine.evaluate(job)
