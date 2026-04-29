"""
验证 BossAdapter.search() 将搜索参数作为 URL query string 传递（而非 POST JSON body）

根因：BOSS 直聘 /wapi/zpgeek/search/joblist.json 接口通过 URL query 读取 query 等搜索参数，
若仅在 POST body 中传递这些参数，服务端会忽略关键词，返回不匹配的默认推荐结果。
"""

from unittest.mock import MagicMock, patch

import pytest

from boss_career_ops.platform.adapters.boss.adapter import BossAdapter


class TestSearchParamsAsUrlQuery:
    """验证 search 参数通过 params (URL query) 而非 json_data (POST body) 传递"""

    @patch("boss_career_ops.platform.adapters.boss.adapter.BossClient")
    def test_search_passes_params_not_json_data(self, mock_client_cls):
        """search() 必须将参数传给 client.post(params=...) 而非 json_data=..."""
        mock_client = MagicMock()
        mock_client.post.return_value = {"code": 0, "zpData": {"jobList": []}}
        mock_client_cls.return_value = mock_client

        with patch.object(BossAdapter, "__init__", lambda self, *a, **k: None):
            adapter = BossAdapter.__new__(BossAdapter)
            adapter._client = mock_client

        search_params = {
            "query": "agent开发",
            "page": 1,
            "pageSize": 15,
            "city": "101280100",
        }
        adapter.search(search_params)

        mock_client.post.assert_called_once()
        call_kwargs = mock_client.post.call_args.kwargs
        assert "params" in call_kwargs, "post() 必须接收 params 参数"
        assert call_kwargs["params"] is search_params, (
            "post() params 应为原始搜索参数字典，确保 query 在 URL query string 中"
        )
        assert call_kwargs.get("json_data") is None, (
            "post() 不应使用 json_data 传递搜索参数，否则 BOSS 服务端忽略 body 中的 query"
        )

    @patch("boss_career_ops.platform.adapters.boss.adapter.BossClient")
    def test_search_query_present_in_url_params(self, mock_client_cls):
        """query 关键词必须出现在 URL params 中以便 BOSS API 正确过滤"""
        mock_client = MagicMock()
        mock_client.post.return_value = {"code": 0, "zpData": {"jobList": []}}
        mock_client_cls.return_value = mock_client

        with patch.object(BossAdapter, "__init__", lambda self, *a, **k: None):
            adapter = BossAdapter.__new__(BossAdapter)
            adapter._client = mock_client

        adapter.search({"query": "Python开发", "page": 1, "pageSize": 15})

        call_kwargs = mock_client.post.call_args.kwargs
        assert call_kwargs["params"]["query"] == "Python开发", (
            "query 关键词必须在 params 中，否则 BOSS API 无法按关键词过滤"
        )

    def test_build_search_params_output_format(self):
        """build_search_params 输出的 query 字段能正确被 search() 传递到 URL"""
        from boss_career_ops.boss.search_filters import build_search_params

        params = build_search_params("AI agent开发", city="深圳")
        assert "query" in params
        assert params["query"] == "AI agent开发"
        assert "city" in params
