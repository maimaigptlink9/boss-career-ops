from boss_career_ops.boss.api.endpoints import Endpoints, Endpoint


class TestEndpoints:
    def test_load_endpoints(self):
        eps = Endpoints()
        ep = eps.get("search")
        assert ep is not None

    def test_get_known_endpoint(self):
        eps = Endpoints()
        ep = eps.get("search")
        assert ep is not None
        assert ep.method == "GET"
        assert "search" in ep.path

    def test_get_unknown_endpoint(self):
        eps = Endpoints()
        assert eps.get("nonexistent") is None

    def test_url_construction(self):
        eps = Endpoints()
        url = eps.url("search")
        assert url.startswith("https://www.zhipin.com")
        assert "search" in url

    def test_url_unknown_raises(self):
        eps = Endpoints()
        try:
            eps.url("nonexistent")
            assert False, "应抛出 ValueError"
        except ValueError as e:
            assert "未知端点" in str(e)

    def test_endpoint_dataclass(self):
        ep = Endpoint(name="test", path="/test", method="POST", description="测试")
        assert ep.name == "test"
        assert ep.method == "POST"
