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
    def test_execute_before_continue(self):
        hm = HookManager()
        hm._hooks["test_hook"] = [lambda data: HookResult(action=HookAction.CONTINUE)]
        result = asyncio.run(hm.execute_before("test_hook", {"key": "val"}))
        assert result.action == HookAction.CONTINUE

    def test_execute_before_veto(self):
        hm = HookManager()
        hm._hooks["test_hook"] = [lambda data: HookResult(action=HookAction.VETO, reason="blocked")]
        result = asyncio.run(hm.execute_before("test_hook"))
        assert result.action == HookAction.VETO
        assert result.reason == "blocked"

    def test_execute_before_modify(self):
        hm = HookManager()
        def cb(data):
            return HookResult(action=HookAction.MODIFY, modified_data={"new": "data"})
        hm._hooks["test_hook"] = [cb]
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
        hm._hooks["test_after"] = [cb]
        asyncio.run(hm.execute_after("test_after", {"result": "ok"}))
        assert len(called) == 1

    def test_execute_before_exception_handled(self):
        hm = HookManager()
        def bad_cb(data):
            raise ValueError("boom")
        hm._hooks["test_hook"] = [bad_cb]
        result = asyncio.run(hm.execute_before("test_hook"))
        assert result.action == HookAction.CONTINUE
