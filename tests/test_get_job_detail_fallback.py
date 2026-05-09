from unittest.mock import MagicMock

from boss_career_ops.platform.adapters.boss.adapter import BossAdapter
from boss_career_ops.platform.models import Job


def _make_adapter():
    adapter = BossAdapter.__new__(BossAdapter)
    adapter._client = MagicMock()
    adapter._auth = MagicMock()
    adapter._mapper = MagicMock()
    adapter._browser = MagicMock()
    return adapter


class TestGetJobDetailFallback:

    def test_job_detail_api_success_returns_directly(self):
        adapter = _make_adapter()
        adapter._client.get.return_value = {
            "code": 0,
            "zpData": {
                "jobInfo": {"jobName": "AI工程师", "encryptJobId": "jid1"},
                "jobDetail": "负责Agent开发",
            },
        }
        mock_job = Job(job_id="jid1", job_name="AI工程师", raw_data={"encryptJobId": "jid1"})
        adapter._mapper.map_job.return_value = mock_job
        adapter.get_job_card = MagicMock()
        adapter._get_job_detail_via_browser = MagicMock()

        result = adapter.get_job_detail("jid1", security_id="sec123")

        assert result is mock_job
        adapter._mapper.map_job.assert_called_once()
        adapter.get_job_card.assert_not_called()
        adapter._get_job_detail_via_browser.assert_not_called()

    def test_risk_blocked_triggers_job_card_fallback(self):
        adapter = _make_adapter()
        adapter._client.get.return_value = {
            "_risk_blocked": True,
            "code": 99,
            "message": "环境存在异常",
        }
        card_job = Job(job_id="jid1", raw_data={"encryptJobId": "jid1"})
        adapter.get_job_card = MagicMock(return_value=card_job)
        adapter._get_job_detail_via_browser = MagicMock()

        result = adapter.get_job_detail("jid1", security_id="sec123")

        assert result is card_job
        assert result.raw_data.get("_card_fetched") is True
        adapter.get_job_card.assert_called_once_with("sec123", "")
        adapter._get_job_detail_via_browser.assert_not_called()

    def test_nonzero_code_triggers_job_card_fallback(self):
        adapter = _make_adapter()
        adapter._client.get.return_value = {
            "code": 7,
            "message": "参数错误",
        }
        card_job = Job(job_id="jid1", raw_data={"encryptJobId": "jid1"})
        adapter.get_job_card = MagicMock(return_value=card_job)
        adapter._get_job_detail_via_browser = MagicMock()

        result = adapter.get_job_detail("jid1", security_id="sec123")

        assert result is card_job
        assert result.raw_data.get("_card_fetched") is True
        adapter.get_job_card.assert_called_once_with("sec123", "")
        adapter._get_job_detail_via_browser.assert_not_called()

    def test_job_card_success_returns_card_fetched_flag(self):
        adapter = _make_adapter()
        adapter._client.get.return_value = {
            "code": 0,
            "zpData": {},
        }
        card_job = Job(job_id="jid1", raw_data={"encryptJobId": "jid1"})
        adapter.get_job_card = MagicMock(return_value=card_job)
        adapter._get_job_detail_via_browser = MagicMock()

        result = adapter.get_job_detail("jid1", security_id="sec123")

        assert result is card_job
        assert result.raw_data.get("_card_fetched") is True

    def test_job_card_failure_triggers_browser_fallback(self):
        adapter = _make_adapter()
        adapter._client.get.return_value = {
            "code": 7,
            "message": "参数错误",
        }
        adapter.get_job_card = MagicMock(return_value=None)
        browser_job = Job(job_id="jid1", raw_data={"encryptJobId": "jid1"})
        adapter._get_job_detail_via_browser = MagicMock(return_value=browser_job)

        result = adapter.get_job_detail("jid1", security_id="sec123")

        assert result is browser_job
        assert result.raw_data.get("_browser_fetched") is True
        adapter.get_job_card.assert_called_once_with("sec123", "")
        adapter._get_job_detail_via_browser.assert_called_once_with("sec123", job_id="jid1")

    def test_empty_security_id_skips_job_card_tries_browser(self):
        adapter = _make_adapter()
        adapter._client.get.return_value = {
            "code": 7,
            "message": "参数错误",
        }
        adapter.get_job_card = MagicMock()
        browser_job = Job(job_id="jid1", raw_data={"encryptJobId": "jid1"})
        adapter._get_job_detail_via_browser = MagicMock(return_value=browser_job)

        result = adapter.get_job_detail("jid1", security_id="", lid="lid1")

        assert result is browser_job
        assert result.raw_data.get("_browser_fetched") is True
        adapter.get_job_card.assert_not_called()
        adapter._get_job_detail_via_browser.assert_called_once_with("", job_id="jid1")

    def test_all_channels_fail_returns_risk_blocked_job(self):
        adapter = _make_adapter()
        adapter._client.get.return_value = {
            "_risk_blocked": True,
            "code": 99,
            "message": "环境存在异常",
        }
        adapter.get_job_card = MagicMock(return_value=None)
        adapter._get_job_detail_via_browser = MagicMock(return_value=None)

        result = adapter.get_job_detail("jid1", security_id="sec123")

        assert result is not None
        assert result.raw_data.get("_risk_blocked") is True
        adapter.get_job_card.assert_called_once_with("sec123", "")
        adapter._get_job_detail_via_browser.assert_called_once_with("sec123", job_id="jid1")
