from dataclasses import dataclass
from enum import Enum


class Dimension(str, Enum):
    MATCH = "匹配度"
    SALARY = "薪资"
    LOCATION = "地点"
    GROWTH = "发展"
    TEAM = "团队"


@dataclass
class DimensionWeight:
    dimension: Dimension
    weight: float
    description: str


DIMENSION_WEIGHTS = [
    DimensionWeight(dimension=Dimension.MATCH, weight=0.30, description="技能、经验、学历与 JD 的匹配程度"),
    DimensionWeight(dimension=Dimension.SALARY, weight=0.25, description="薪资范围与预期的对比，行业竞争力"),
    DimensionWeight(dimension=Dimension.LOCATION, weight=0.15, description="通勤距离、城市偏好、远程可能性"),
    DimensionWeight(dimension=Dimension.GROWTH, weight=0.15, description="职业成长空间、技术栈前瞻性、团队规模"),
    DimensionWeight(dimension=Dimension.TEAM, weight=0.15, description="公司阶段、团队文化、面试反馈信号"),
]


def get_weight(dimension: Dimension) -> float:
    for dw in DIMENSION_WEIGHTS:
        if dw.dimension == dimension:
            return dw.weight
    return 0.0
