from enum import Enum


class Stage(str, Enum):
    DISCOVERED = "发现"
    EVALUATED = "评估"
    APPLIED = "投递"
    COMMUNICATING = "沟通"
    INTERVIEW = "面试"
    OFFER = "offer"


STAGE_ORDER = [
    Stage.DISCOVERED,
    Stage.EVALUATED,
    Stage.APPLIED,
    Stage.COMMUNICATING,
    Stage.INTERVIEW,
    Stage.OFFER,
]


def next_stage(current: Stage) -> Stage | None:
    idx = STAGE_ORDER.index(current)
    if idx < len(STAGE_ORDER) - 1:
        return STAGE_ORDER[idx + 1]
    return None

