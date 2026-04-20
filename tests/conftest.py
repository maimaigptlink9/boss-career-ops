import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


from boss_career_ops.config.singleton import SingletonMeta


def _reset_singleton(cls):
    SingletonMeta.reset(cls)


@pytest.fixture(autouse=True)
def reset_singletons():
    singletons = []
    try:
        from boss_career_ops.config.settings import Settings
        singletons.append(Settings)
    except Exception:
        pass
    try:
        from boss_career_ops.config.thresholds import Thresholds
        singletons.append(Thresholds)
    except Exception:
        pass
    try:
        from boss_career_ops.hooks.manager import HookManager
        singletons.append(HookManager)
    except Exception:
        pass
    try:
        from boss_career_ops.boss.api.endpoints import Endpoints
        singletons.append(Endpoints)
    except Exception:
        pass
    try:
        from boss_career_ops.boss.api.client import BossClient
        singletons.append(BossClient)
    except Exception:
        pass
    try:
        from boss_career_ops.boss.auth.manager import AuthManager
        singletons.append(AuthManager)
    except Exception:
        pass
    try:
        from boss_career_ops.boss.auth.token_store import TokenStore
        singletons.append(TokenStore)
    except Exception:
        pass
    try:
        from boss_career_ops.boss.browser_client import BrowserClient
        singletons.append(BrowserClient)
    except Exception:
        pass
    try:
        from boss_career_ops.pipeline.manager import PipelineManager
        singletons.append(PipelineManager)
    except Exception:
        pass

    for cls in singletons:
        _reset_singleton(cls)

    yield

    for cls in singletons:
        _reset_singleton(cls)


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def sample_job():
    return {
        "jobName": "Golang后端工程师",
        "brandName": "测试公司",
        "salaryDesc": "20-40K",
        "cityName": "广州",
        "jobLabels": ["五险一金", "双休"],
        "skills": "Go,Docker,Kubernetes",
        "jobExperience": "3-5年",
        "jobDegree": "本科",
        "postDescription": "负责后端服务开发，需要Go语言经验",
        "brandStageName": "B轮",
        "brandScaleName": "100-499人",
        "brandIndustry": "互联网",
        "securityId": "sec123",
        "encryptJobId": "job456",
    }
