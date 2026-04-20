from boss_career_ops.cache.store import CacheStore


class TestCacheStore:
    def test_context_manager(self, tmp_dir):
        db = tmp_dir / "test_cache.db"
        with CacheStore(db) as store:
            assert store._conn is not None
        assert store._conn is None

    def test_set_and_get(self, tmp_dir):
        db = tmp_dir / "test_cache.db"
        with CacheStore(db) as store:
            store.set("key1", "value1", ttl=3600)
            result = store.get("key1")
            assert result == "value1"

    def test_get_nonexistent_key(self, tmp_dir):
        db = tmp_dir / "test_cache.db"
        with CacheStore(db) as store:
            result = store.get("missing")
            assert result is None

    def test_set_and_get_json(self, tmp_dir):
        db = tmp_dir / "test_cache.db"
        with CacheStore(db) as store:
            store.set("job1", {"name": "Golang", "salary": "20-40K"}, ttl=3600)
            result = store.get("job1")
            assert result["name"] == "Golang"
            assert result["salary"] == "20-40K"

    def test_delete(self, tmp_dir):
        db = tmp_dir / "test_cache.db"
        with CacheStore(db) as store:
            store.set("key1", "val1", ttl=3600)
            store.delete("key1")
            assert store.get("key1") is None

    def test_clear(self, tmp_dir):
        db = tmp_dir / "test_cache.db"
        with CacheStore(db) as store:
            store.set("k1", "v1", ttl=3600)
            store.set("k2", "v2", ttl=3600)
            store.clear()
            assert store.get("k1") is None
            assert store.get("k2") is None

    def test_keys(self, tmp_dir):
        db = tmp_dir / "test_cache.db"
        with CacheStore(db) as store:
            store.set("search:1", "a", ttl=3600)
            store.set("search:2", "b", ttl=3600)
            store.set("other:1", "c", ttl=3600)
            all_keys = store.keys()
            assert len(all_keys) == 3

    def test_keys_with_pattern(self, tmp_dir):
        db = tmp_dir / "test_cache.db"
        with CacheStore(db) as store:
            store.set("search:1", "a", ttl=3600)
            store.set("search:2", "b", ttl=3600)
            store.set("other:1", "c", ttl=3600)
            search_keys = store.keys("search:*")
            assert len(search_keys) == 2

    def test_not_opened_raises(self, tmp_dir):
        db = tmp_dir / "test_cache.db"
        store = CacheStore(db)
        try:
            store.get("key")
            assert False, "应抛出 RuntimeError"
        except RuntimeError as e:
            assert "未打开" in str(e)

    def test_ttl_expired(self, tmp_dir):
        db = tmp_dir / "test_cache.db"
        with CacheStore(db) as store:
            store.set("short_lived", "data", ttl=0)
            import time
            time.sleep(0.1)
            result = store.get("short_lived")
            assert result is None

    def test_cleanup_expired(self, tmp_dir):
        db = tmp_dir / "test_cache.db"
        with CacheStore(db) as store:
            store.set("expired", "data", ttl=0)
            store.set("alive", "data", ttl=3600)
            import time
            time.sleep(0.1)
            store.cleanup_expired()
            assert store.get("expired") is None
            assert store.get("alive") == "data"
