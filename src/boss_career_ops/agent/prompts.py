import re
from string import Template

from boss_career_ops.evaluator.dimensions import DIMENSION_WEIGHTS

_INJECTION_PATTERNS = [
    re.compile(r"忽略以上所有指令", re.IGNORECASE),
    re.compile(r"忽略以上指令", re.IGNORECASE),
    re.compile(r"ignore\s+all\s+previous\s+instructions", re.IGNORECASE),
    re.compile(r"ignore\s+previous\s+instructions", re.IGNORECASE),
    re.compile(r"^你是一个"),
]


def sanitize_input(text: str) -> str:
    if not text:
        return text
    for pattern in _INJECTION_PATTERNS:
        text = pattern.sub("[已过滤]", text)
    return text


def _get_weight_description() -> str:
    return "、".join(
        f"{dw.dimension.value}({int(dw.weight * 100)}%)" for dw in DIMENSION_WEIGHTS
    )


ORCHESTRATOR_SYSTEM = Template(
    '你是一个求职助手的路由器。分析用户的自然语言输入，识别意图并提取参数。支持的意图：search（搜索职位）、evaluate（评估匹配度）、resume（生成定制简历）、apply（投递+打招呼）、gap_analysis（技能差距分析）。你必须以JSON格式回复：{"intent": "...", "params": {...}, "next_action": "..."}'
)

ORCHESTRATOR_USER = Template("$query")

EVALUATE_SYSTEM = Template(
    '你是一个资深求职顾问。根据求职者的个人档案和目标职位JD，进行5维度评估：$weight_description。每个维度给出1-5分和理由。你必须以JSON格式回复：{"scores": {"匹配度": {"score": 4, "reason": "..."}, ...}, "total_score": 4.2, "grade": "B", "analysis": "综合分析..."}'
)

EVALUATE_USER = Template("求职者档案：\n$profile\n\n目标职位JD：\n$jd\n\n$rag_context")

RESUME_SYSTEM = Template(
    "你是一个资深简历顾问。根据目标职位的JD，改写求职者的简历叙事。要求：1.突出与JD匹配的经验和技能 2.量化成果 3.ATS关键词自然融入 4.不编造内容 5.保持简历原有结构。直接输出改写后的Markdown简历。"
)

RESUME_USER = Template("原始简历：\n$cv\n\n目标职位JD：\n$jd\n\n$rag_context")

APPLY_SYSTEM = Template(
    "你是一个求职沟通专家。根据目标职位的JD和求职者的简历，生成一段个性化的打招呼语。要求：1.简洁有力，不超过100字 2.突出1-2个最匹配的优势 3.语气专业但友好 4.不要用模板化的表达。直接输出打招呼语文本。"
)

APPLY_USER = Template("求职者简历摘要：\n$cv_summary\n\n目标职位JD：\n$jd")

GAP_ANALYSIS_SYSTEM = Template(
    '你是一个职业发展顾问。分析求职者当前技能与目标职位要求的差距，给出优先级排序和学习建议。你必须以JSON格式回复：{"missing_skills": [{"skill": "...", "priority": "high/medium/low", "suggestion": "..."}], "overall_assessment": "..."}'
)

GAP_ANALYSIS_USER = Template("求职者技能：\n$skills\n\n目标职位JD列表：\n$jds")

SEARCH_STRATEGY_SYSTEM = Template(
    '你是一个搜索策略专家。根据用户的求职意向，生成多组搜索关键词组合，以覆盖更多相关职位。你必须以JSON格式回复：{"keywords": ["关键词1", "关键词2", ...]}'
)

SEARCH_STRATEGY_USER = Template("用户搜索意图：$query")
