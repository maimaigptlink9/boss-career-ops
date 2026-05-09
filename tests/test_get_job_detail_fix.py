import pytest
from unittest.mock import MagicMock, patch

from boss_career_ops.platform.adapters.boss.adapter import BossAdapter
from boss_career_ops.platform.models import Job


@pytest.fixture
def adapter():
    with patch("boss_career_ops.platform.adapters.boss.adapter.BossClient") as MockClient, \
         patch("boss_career_ops.platform.adapters.boss.adapter.AuthManager") as MockAuth, \
         patch("boss_career_ops.platform.adapters.boss.adapter.BossFieldMapper") as MockMapper:
        adapter = BossAdapter()
        adapter._client = MockClient.return_value
        adapter._mapper = MockMapper.return_value
        adapter._mapper.map_job = MagicMock(side_effect=lambda d: Job(
            job_id=d.get("encryptJobId", ""),
            security_id=d.get("securityId", ""),
            job_name=d.get("jobName", ""),
            company_name=d.get("brandName", ""),
            description=str(d.get("jobDetail", "") or d.get("postDescription", "")),
            raw_data=dict(d),
        ))
        yield adapter


def test_encryptJobId_uses_job_id_not_security_id(adapter):
    adapter._client.get.return_value = {
        "code": 0,
        "zpData": {
            "jobInfo": {
                "encryptJobId": "enc123",
                "jobName": "测试职位",
                "brandName": "测试公司",
            },
        },
    }
    adapter.get_job_detail(job_id="enc123", security_id="sec456")
    adapter._client.get.assert_called_once_with("job_detail", params={"encryptJobId": "enc123"})


def test_jobDetail_extracted_and_injected(adapter):
    adapter._client.get.return_value = {
        "code": 0,
        "zpData": {
            "jobInfo": {
                "encryptJobId": "enc123",
                "jobName": "测试职位",
                "brandName": "测试公司",
            },
            "jobDetail": "这是完整的职位描述内容",
        },
    }
    job = adapter.get_job_detail(job_id="enc123")
    assert job is not None
    assert job.description == "这是完整的职位描述内容"
    assert job.raw_data.get("jobDetail") == "这是完整的职位描述内容"


def test_postDescription_used_when_jobDetail_empty(adapter):
    adapter._client.get.return_value = {
        "code": 0,
        "zpData": {
            "jobInfo": {
                "encryptJobId": "enc123",
                "jobName": "测试职位",
                "brandName": "测试公司",
                "postDescription": "来自postDescription的描述",
            },
            "jobDetail": "",
        },
    }
    job = adapter.get_job_detail(job_id="enc123")
    assert job is not None
    assert job.description == "来自postDescription的描述"


def test_jobDetail_takes_priority_over_postDescription(adapter):
    adapter._client.get.return_value = {
        "code": 0,
        "zpData": {
            "jobInfo": {
                "encryptJobId": "enc123",
                "jobName": "测试职位",
                "brandName": "测试公司",
                "postDescription": "简短描述",
            },
            "jobDetail": "完整JD内容",
        },
    }
    job = adapter.get_job_detail(job_id="enc123")
    assert job is not None
    assert job.description == "完整JD内容"
