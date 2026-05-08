import json
from unittest.mock import MagicMock, patch

import pytest

from boss_career_ops.agent.tools import _ensure_job_description, _JD_MAX_RETRIES, _JD_RETRY_BASE_DELAY
from boss_career_ops.platform.models import Job


def _make_job(job_id="job1", security_id="sec1", data="{}"):
    return {"job_id": job_id, "security_id": security_id, "data": data}


def _make_api_job(description="Python开发", skills="Python", raw_data=None):
    job = MagicMock()
    job.description = description
    job.skills = skills
    job.raw_data = raw_data or {}
    return job


class TestJdStatusOkWhenDescriptionExists:
    def test_no_update_when_description_and_status_already_set(self):
        pm = MagicMock()
        job = _make_job(data=json.dumps({"description": "Python开发", "jd_status": "ok"}))
        _ensure_job_description(pm, job)
        pm.update_job_data.assert_not_called()

    def test_writes_jd_status_ok_when_description_present_but_status_missing(self):
        pm = MagicMock()
        job = _make_job(data=json.dumps({"description": "Python开发"}))
        _ensure_job_description(pm, job)
        pm.update_job_data.assert_called_once_with("job1", {"jd_status": "ok"})


class TestJdStatusMissingWhenNoDetailId:
    def test_writes_jd_status_missing_when_both_ids_empty(self):
        pm = MagicMock()
        job = {"job_id": "", "security_id": "", "data": "{}"}
        _ensure_job_description(pm, job)
        pm.update_job_data.assert_called_once_with("", {"jd_status": "missing"})

    def test_writes_jd_status_missing_when_no_security_id_and_no_job_id(self):
        pm = MagicMock()
        job = {"job_id": "", "security_id": "", "data": "{}"}
        _ensure_job_description(pm, job)
        pm.update_job_data.assert_called_once_with("", {"jd_status": "missing"})


@patch("boss_career_ops.agent.tools.time.sleep")
@patch("boss_career_ops.agent.tools.get_active_adapter")
class TestJdStatusFetchFailedApiReturnsNone:
    def test_writes_fetch_failed_after_retries_exhausted(self, mock_get_adapter, mock_sleep):
        mock_adapter = MagicMock()
        mock_adapter.get_job_detail.return_value = None
        mock_get_adapter.return_value = mock_adapter
        pm = MagicMock()
        job = _make_job()
        _ensure_job_description(pm, job)
        assert mock_adapter.get_job_detail.call_count == _JD_MAX_RETRIES
        pm.update_job_data.assert_called_once_with("job1", {"jd_status": "fetch_failed"})
        assert mock_sleep.call_count == _JD_MAX_RETRIES - 1


@patch("boss_career_ops.agent.tools.time.sleep")
@patch("boss_career_ops.agent.tools.get_active_adapter")
class TestJdStatusFetchFailedApiReturnsNoDescription:
    def test_writes_fetch_failed_when_api_returns_no_description(self, mock_get_adapter, mock_sleep):
        mock_adapter = MagicMock()
        api_job = _make_api_job(description="")
        mock_adapter.get_job_detail.return_value = api_job
        mock_get_adapter.return_value = mock_adapter
        pm = MagicMock()
        job = _make_job()
        _ensure_job_description(pm, job)
        assert mock_adapter.get_job_detail.call_count == _JD_MAX_RETRIES
        pm.update_job_data.assert_called_once_with("job1", {"jd_status": "fetch_failed"})


@patch("boss_career_ops.agent.tools.time.sleep")
@patch("boss_career_ops.agent.tools.get_active_adapter")
class TestJdStatusBlocked:
    def test_writes_blocked_when_risk_blocked_and_browser_fallback_fails(self, mock_get_adapter, mock_sleep):
        mock_adapter = MagicMock()
        api_job = _make_api_job(description="", raw_data={"_risk_blocked": True})
        mock_adapter.get_job_detail.return_value = api_job
        mock_get_adapter.return_value = mock_adapter
        pm = MagicMock()
        job = _make_job()
        _ensure_job_description(pm, job)
        assert mock_adapter.get_job_detail.call_count == _JD_MAX_RETRIES
        pm.update_job_data.assert_called_once_with("job1", {"jd_status": "blocked"})


@patch("boss_career_ops.agent.tools.time.sleep")
@patch("boss_career_ops.agent.tools.get_active_adapter")
@patch("boss_career_ops.agent.tools.PipelineManager._extract_job_data")
class TestJdStatusOkOnSuccess:
    def test_writes_ok_and_data_source_on_success(self, mock_extract, mock_get_adapter, mock_sleep):
        mock_adapter = MagicMock()
        api_job = _make_api_job(description="Python开发")
        mock_adapter.get_job_detail.return_value = api_job
        mock_get_adapter.return_value = mock_adapter
        mock_extract.return_value = {"description": "Python开发", "data_source": "detail_api"}
        pm = MagicMock()
        job = _make_job()
        _ensure_job_description(pm, job)
        mock_extract.assert_called_once_with(api_job, data_source="detail_api")
        update_call_args = pm.update_job_data.call_args
        assert update_call_args[0][0] == "job1"
        assert update_call_args[0][1]["jd_status"] == "ok"
        assert update_call_args[0][1]["data_source"] == "detail_api"
        assert "description" in json.loads(job["data"])


@patch("boss_career_ops.agent.tools.time.sleep")
@patch("boss_career_ops.agent.tools.get_active_adapter")
@patch("boss_career_ops.agent.tools.PipelineManager._extract_job_data")
class TestJdStatusBrowserFetch:
    def test_writes_browser_fetch_data_source_when_browser_fetched(self, mock_extract, mock_get_adapter, mock_sleep):
        mock_adapter = MagicMock()
        api_job = _make_api_job(description="Python开发", raw_data={"_browser_fetched": True})
        mock_adapter.get_job_detail.return_value = api_job
        mock_get_adapter.return_value = mock_adapter
        mock_extract.return_value = {"description": "Python开发", "data_source": "browser_fetch"}
        pm = MagicMock()
        job = _make_job()
        _ensure_job_description(pm, job)
        mock_extract.assert_called_once_with(api_job, data_source="browser_fetch")
        update_call_args = pm.update_job_data.call_args
        assert update_call_args[0][1]["jd_status"] == "ok"
        assert update_call_args[0][1]["data_source"] == "browser_fetch"


@patch("boss_career_ops.agent.tools.time.sleep")
@patch("boss_career_ops.agent.tools.get_active_adapter")
@patch("boss_career_ops.agent.tools.PipelineManager._extract_job_data")
class TestRetrySucceedsOnSecondAttempt:
    def test_succeeds_on_retry(self, mock_extract, mock_get_adapter, mock_sleep):
        mock_adapter = MagicMock()
        api_job_ok = _make_api_job(description="Python开发")
        mock_adapter.get_job_detail.side_effect = [None, api_job_ok]
        mock_get_adapter.return_value = mock_adapter
        mock_extract.return_value = {"description": "Python开发"}
        pm = MagicMock()
        job = _make_job()
        _ensure_job_description(pm, job)
        assert mock_adapter.get_job_detail.call_count == 2
        mock_sleep.assert_called_once()
        update_call_args = pm.update_job_data.call_args
        assert update_call_args[0][1]["jd_status"] == "ok"


@patch("boss_career_ops.agent.tools.time.sleep")
@patch("boss_career_ops.agent.tools.get_active_adapter")
class TestRetryMechanism:
    def test_retries_up_to_max_attempts_on_exception(self, mock_get_adapter, mock_sleep):
        mock_adapter = MagicMock()
        mock_adapter.get_job_detail.side_effect = Exception("网络错误")
        mock_get_adapter.return_value = mock_adapter
        pm = MagicMock()
        job = _make_job()
        _ensure_job_description(pm, job)
        assert mock_adapter.get_job_detail.call_count == _JD_MAX_RETRIES
        pm.update_job_data.assert_called_once_with("job1", {"jd_status": "fetch_failed"})

    def test_exponential_backoff_delays(self, mock_get_adapter, mock_sleep):
        mock_adapter = MagicMock()
        mock_adapter.get_job_detail.side_effect = Exception("网络错误")
        mock_get_adapter.return_value = mock_adapter
        pm = MagicMock()
        job = _make_job()
        _ensure_job_description(pm, job)
        assert mock_sleep.call_count == _JD_MAX_RETRIES - 1
        sleep_calls = [c[0][0] for c in mock_sleep.call_args_list]
        for i, delay in enumerate(sleep_calls):
            expected_base = _JD_RETRY_BASE_DELAY * (2 ** i)
            assert expected_base <= delay <= expected_base + 1
