from boss_career_ops.evaluator.dimensions import Dimension, get_weight


GRADE_RANGES = {
    "A": (4.5, 5.0),
    "B": (3.5, 4.4),
    "C": (2.5, 3.4),
    "D": (1.5, 2.4),
    "F": (0.0, 1.4),
}

GRADE_LABELS = {
    "A": "强烈推荐，立即行动",
    "B": "值得投入，优先处理",
    "C": "一般，需人工判断",
    "D": "不太匹配，谨慎考虑",
    "F": "不推荐",
}


def calculate_weighted_score(scores: dict[str, float]) -> float:
    total = 0.0
    for dim in Dimension:
        score = scores.get(dim.value, 0.0)
        weight = get_weight(dim)
        total += score * weight
    return round(min(5.0, max(0.0, total)), 2)


def score_to_grade(score: float) -> str:
    for grade, (low, high) in GRADE_RANGES.items():
        if low <= score <= high:
            return grade
    return "F"


def grade_label(grade: str) -> str:
    return GRADE_LABELS.get(grade, "未知")


def get_recommendation(grade: str) -> str:
    return GRADE_LABELS.get(grade, "未知等级")
