from pathlib import Path
from unittest.mock import MagicMock

import yaml

from boss_career_ops.boss.api.endpoints import Endpoints
from boss_career_ops.platform.adapter import PlatformAdapter
from boss_career_ops.platform.adapters.boss.adapter import BossAdapter


YAML_PATH = Path(__file__).parent.parent / "src" / "boss_career_ops" / "boss" / "api" / "boss.yaml"


class TestJobCardYaml:
    def test_job_card_in_yaml(self):
        with open(YAML_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "job_card" in data["endpoints"]
        ep = data["endpoints"]["job_card"]
        assert ep["path"] == "/wapi/zpgeek/job/card.json"
        assert ep["method"] == "GET"

    def test_job_card_loaded_by_endpoints(self):
        eps = Endpoints()
        ep = eps.get("job_card")
        assert ep is not None
        assert ep.path == "/wapi/zpgeek/job/card.json"
        assert ep.method == "GET"


class TestBossClientGetJobCard:
    def test_calls_correct_endpoint_with_params(self):
        from boss_career_ops.boss.api.client import BossClient

        client = BossClient.__new__(BossClient)
        captured = {}

        def mock_get(endpoint_name, params=None):
            captured["endpoint"] = endpoint_name
            captured["params"] = params
            return {"code": 0, "zpData": {}}

        client.get = mock_get
        client.get_job_card("abc123", lid="xyz")
        assert captured["endpoint"] == "job_card"
        assert captured["params"] == {"securityId": "abc123", "lid": "xyz"}

    def test_default_lid_empty(self):
        from boss_career_ops.boss.api.client import BossClient

        client = BossClient.__new__(BossClient)
        captured = {}

        def mock_get(endpoint_name, params=None):
            captured["params"] = params
            return {"code": 0, "zpData": {}}

        client.get = mock_get
        client.get_job_card("abc123")
        assert captured["params"]["lid"] == ""


class TestBossAdapterGetJobCard:
    def _make_adapter(self, mock_get_job_card):
        adapter = BossAdapter.__new__(BossAdapter)
        adapter._client = MagicMock()
        adapter._client.get_job_card = mock_get_job_card
        adapter._mapper = MagicMock()
        adapter._mapper.map_job = lambda j: j
        return adapter

    def test_parses_zpdata_jobcard(self):
        job_card_data = {"encryptJobId": "abc", "jobName": "测试职位"}

        def mock_get_job_card(security_id, lid=""):
            return {"code": 0, "zpData": {"jobCard": job_card_data}}

        adapter = self._make_adapter(mock_get_job_card)
        result = adapter.get_job_card("abc")
        assert result is not None
        assert result["encryptJobId"] == "abc"
        assert result["securityId"] == "abc"

    def test_returns_none_when_jobcard_empty(self):
        def mock_get_job_card(security_id, lid=""):
            return {"code": 0, "zpData": {"jobCard": {}}}

        adapter = self._make_adapter(mock_get_job_card)
        result = adapter.get_job_card("abc")
        assert result is None

    def test_returns_none_when_code_not_zero(self):
        def mock_get_job_card(security_id, lid=""):
            return {"code": 1, "message": "失败"}

        adapter = self._make_adapter(mock_get_job_card)
        result = adapter.get_job_card("abc")
        assert result is None

    def test_returns_none_when_risk_blocked(self):
        def mock_get_job_card(security_id, lid=""):
            return {"code": 0, "_risk_blocked": True}

        adapter = self._make_adapter(mock_get_job_card)
        result = adapter.get_job_card("abc")
        assert result is None

    def test_adds_security_id_to_jobcard(self):
        job_card_data = {"encryptJobId": "xyz", "jobName": "开发"}

        def mock_get_job_card(security_id, lid=""):
            return {"code": 0, "zpData": {"jobCard": job_card_data}}

        adapter = self._make_adapter(mock_get_job_card)
        result = adapter.get_job_card("xyz")
        assert result is not None
        assert result["securityId"] == "xyz"


class TestPlatformAdapterGetJobCard:
    def test_raises_not_implemented(self):
        class StubAdapter(PlatformAdapter):
            def search(self, params): return []
            def get_job_detail(self, security_id): return None
            def greet(self, security_id, job_id): pass
            def apply(self, security_id, job_id): pass
            def get_chat_list(self): return []
            def get_chat_messages(self, security_id): return []
            def exchange_contact(self, security_id, contact_type): pass
            def mark_contact(self, security_id, tag): pass
            def get_recommendations(self, params=None): return []
            def upload_resume(self, pdf_path, display_name): pass
            def login(self, **kwargs): pass
            def check_auth_status(self): pass
            def build_search_params(self, **kwargs): return {}
            def get_city_code(self, city): return ""
            def filter_by_welfare(self, jobs, welfare_keywords): return jobs

        adapter = StubAdapter()
        try:
            adapter.get_job_card("abc")
            assert False, "应抛出 NotImplementedError"
        except NotImplementedError as e:
            assert "StubAdapter" in str(e)
            assert "get_job_card" in str(e)
