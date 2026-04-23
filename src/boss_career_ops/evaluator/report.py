from boss_career_ops.evaluator.dimensions import DIMENSION_WEIGHTS


def generate_report(evaluation: dict) -> str:
    lines = []
    lines.append(f"# 职位评估报告")
    lines.append("")
    lines.append(f"**{evaluation.get('job_name', '')}** — {evaluation.get('company_name', '')}")
    lines.append(f"薪资: {evaluation.get('salary_desc', '未知')}")
    lines.append("")
    lines.append(f"## 综合评分")
    lines.append("")
    lines.append(f"| 指标 | 值 |")
    lines.append(f"|------|------|")
    lines.append(f"| 加权总分 | {evaluation.get('total_score', 0)} |")
    lines.append(f"| 等级 | {evaluation.get('grade', '')} — {evaluation.get('grade_label', '')} |")
    lines.append(f"| 建议 | {evaluation.get('recommendation', '')} |")
    lines.append("")
    lines.append(f"## 维度评分")
    lines.append("")
    lines.append(f"| 维度 | 权重 | 评分 |")
    lines.append(f"|------|------|------|")
    scores = evaluation.get("scores", {})
    for dw in DIMENSION_WEIGHTS:
        score = scores.get(dw.dimension.value, 0.0)
        lines.append(f"| {dw.dimension.value} | {dw.weight:.0%} | {score} |")
    lines.append("")
    lines.append(f"## 建议")
    lines.append("")
    lines.append(evaluation.get("recommendation", ""))
    return "\n".join(lines)
