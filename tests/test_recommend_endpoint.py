from unittest.mock import MagicMock, patch

import yaml

from boss_career_ops.boss.api.endpoints import Endpoints
from boss_career_ops.platform.adapters.boss.adapter import BossAdapter


YAML_PATH = Endpoints._instance_yaml_path if hasattr(Endpoints, "_instance_yaml_path") else None


class TestRecommendV2Endpoint:
    def test_recommend_v2_in_yaml(self):
        from pathlib import Path
        yaml_path = Path(__file__).parent.parent / "src" / "boss_career_ops" / "boss" / "api" / "boss.yaml"
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "recommend_v2" in data["endpoints"], "recommend_v2 端点不存在"
        ep = data["endpoints"]["recommend_v2"]
        assert ep["path"] == "/wapi/zprelation/interaction/geekGetJob"
        assert ep["method"] == "GET"

    def test_recommend_v2_loaded_by_endpoints(self):
        eps = Endpoints()
        ep = eps.get("recommend_v2")
        assert ep is not None, "Endpoints 未加载 recommend_v2"
        assert ep.path == "/wapi/zprelation/interaction/geekGetJob"
        assert ep.method == "GET"

    def test_recommend_original_preserved(self):
        eps = Endpoints()
        ep = eps.get("recommend")
        assert ep is not None, "原有 recommend 端点被删除"
        assert ep.path == "/wapi/zpgeek/recommend/job/list.json"


class TestGetRecommendationsParams:
    def _make_adapter(self, mock_get):
        adapter = BossAdapter.__new__(BossAdapter)
        adapter._client = MagicMock()
        adapter._client.get = mock_get
        adapter._mapper = MagicMock()
        adapter._mapper.map_job = lambda j: j
        return adapter

    def test_default_params_tag_and_is_active(self):
        captured = {}

        def mock_get(endpoint_name, params=None):
            captured["endpoint"] = endpoint_name
            captured["params"] = params
            return {"code": 0, "zpData": {"jobList": []}}

        adapter = self._make_adapter(mock_get)
        adapter.get_recommendations()
        assert captured["endpoint"] == "recommend_v2"
        assert captured["params"]["tag"] == "5"
        assert captured["params"]["isActive"] == "true"

    def test_custom_params_not_overridden(self):
        captured = {}

        def mock_get(endpoint_name, params=None):
            captured["params"] = params
            return {"code": 0, "zpData": {"jobList": []}}

        adapter = self._make_adapter(mock_get)
        adapter.get_recommendations(params={"tag": "3", "isActive": "false", "page": 2})
        assert captured["params"]["tag"] == "3"
        assert captured["params"]["isActive"] == "false"
        assert captured["params"]["page"] == 2

    def test_non_zero_code_returns_empty(self):
        adapter = self._make_adapter(lambda endpoint_name, params=None: {"code": 1, "message": "失败"})
        result = adapter.get_recommendations()
        assert result == []


class TestCardListFallback:
    def _make_adapter(self, mock_get):
        adapter = BossAdapter.__new__(BossAdapter)
        adapter._client = MagicMock()
        adapter._client.get = mock_get
        adapter._mapper = MagicMock()
        adapter._mapper.map_job = lambda j: j
        return adapter

    def test_job_list_takes_priority(self):
        job_data = [{"encryptJobId": "1"}, {"encryptJobId": "2"}]
        card_data = [{"encryptJobId": "3"}]

        def mock_get(endpoint_name, params=None):
            return {"code": 0, "zpData": {"jobList": job_data, "cardList": card_data}}

        adapter = self._make_adapter(mock_get)
        result = adapter.get_recommendations()
        assert result == job_data

    def test_card_list_fallback_when_job_list_empty(self):
        card_data = [{"encryptJobId": "3"}, {"encryptJobId": "4"}]

        def mock_get(endpoint_name, params=None):
            return {"code": 0, "zpData": {"jobList": [], "cardList": card_data}}

        adapter = self._make_adapter(mock_get)
        result = adapter.get_recommendations()
        assert result == card_data

    def test_both_empty_returns_empty(self):
        def mock_get(endpoint_name, params=None):
            return {"code": 0, "zpData": {"jobList": [], "cardList": []}}

        adapter = self._make_adapter(mock_get)
        result = adapter.get_recommendations()
        assert result == []

    def test_no_card_list_field_returns_empty(self):
        def mock_get(endpoint_name, params=None):
            return {"code": 0, "zpData": {"jobList": []}}

        adapter = self._make_adapter(mock_get)
        result = adapter.get_recommendations()
        assert result == []
