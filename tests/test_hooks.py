import asyncio
from boss_career_ops.hooks.manager import HookManager, HookAction, HookResult


class TestHookAction:
    def test_values(self):
        assert HookAction.CONTINUE.value == "continue"
        assert HookAction.VETO.value == "veto"
        assert HookAction.MODIFY.value == "modify"


class TestHookResult:
    def test_default(self):
        r = HookResult()
        assert r.action == HookAction.CONTINUE
        assert r.modified_data is None
        assert r.reason == ""

    def test_custom(self):
        r = HookResult(action=HookAction.VETO, reason="test")
        assert r.action == HookAction.VETO
        assert r.reason == "test"


class TestHookManager:
    def test_register_and_list(self):
        hm = HookManager()
        def cb(data): return HookResult()
        hm.register("greet_before", cb)
        assert hm.has_hooks("greet_before")
        hooks = hm.list_hooks()
        assert "greet_before" in hooks
        assert hooks["greet_before"] == 1

    def test_unregister(self):
        hm = HookManager()
        def cb(data): return HookResult()
        hm.register("greet_before", cb)
        hm.unregister("greet_before", cb)
        assert not hm.has_hooks("greet_before")

    def test_clear(self):
        hm = HookManager()
        def cb(data): return HookResult()
        hm.register("hook1", cb)
        hm.register("hook2", cb)
        hm.clear()
        assert not hm.has_hooks("hook1")
        assert not hm.has_hooks("hook2")

    def test_execute_before_continue(self):
        hm = HookManager()
        def cb(data): return HookResult(action=HookAction.CONTINUE)
        hm.register("test_hook", cb)
        result = asyncio.run(hm.execute_before("test_hook", {"key": "val"}))
        assert result.action == HookAction.CONTINUE

    def test_execute_before_veto(self):
        hm = HookManager()
        def cb(data): return HookResult(action=HookAction.VETO, reason="blocked")
        hm.register("test_hook", cb)
        result = asyncio.run(hm.execute_before("test_hook"))
        assert result.action == HookAction.VETO
        assert result.reason == "blocked"

    def test_execute_before_modify(self):
        hm = HookManager()
        def cb(data):
            return HookResult(action=HookAction.MODIFY, modified_data={"new": "data"})
        hm.register("test_hook", cb)
        result = asyncio.run(hm.execute_before("test_hook"))
        assert result.modified_data == {"new": "data"}

    def test_execute_before_no_hooks(self):
        hm = HookManager()
        result = asyncio.run(hm.execute_before("nonexistent"))
        assert result.action == HookAction.CONTINUE

    def test_execute_after(self):
        hm = HookManager()
        called = []
        def cb(data):
            called.append(data)
        hm.register("test_after", cb)
        asyncio.run(hm.execute_after("test_after", {"result": "ok"}))
        assert len(called) == 1

    def test_execute_before_exception_handled(self):
        hm = HookManager()
        def bad_cb(data):
            raise ValueError("boom")
        hm.register("test_hook", bad_cb)
        result = asyncio.run(hm.execute_before("test_hook"))
        assert result.action == HookAction.CONTINUE

    def test_has_hooks_false(self):
        hm = HookManager()
        assert not hm.has_hooks("nonexistent")
