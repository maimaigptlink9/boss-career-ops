import json
import operator
from contextlib import contextmanager
from importlib import import_module
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langgraph.graph import END

from boss_career_ops.agent.graph import (
    build_career_agent,
    route_after_resume,
    route_after_action,
    NODE_NAMES,
)
from boss_career_ops.agent.state import AgentState
from boss_career_ops.agent.conditions import route_by_intent
from boss_career_ops.errors import Result


def _make_mock_llm(response_content: str):
    llm = AsyncMock()
    response = MagicMock()
    response.content = response_content
    llm.ainvoke = AsyncMock(return_value=response)
    return llm


def _base_state(**overrides):
    state = {
        "messages": [],
        "intent": "",
        "job_ids": [],
        "current_job_id": "",
        "job_details": {},
        "evaluation_results": {},
        "resume_versions": {},
        "skill_gaps": {},
        "rag_context": "",
        "errors": [],
        "next_action": "",
    }
    state.update(overrides)
    return state


_NODE_MODULES = [
    "boss_career_ops.agent.nodes.orchestrator",
    "boss_career_ops.agent.nodes.search",
    "boss_career_ops.agent.nodes.evaluate",
    "boss_career_ops.agent.nodes.resume",
    "boss_career_ops.agent.nodes.apply",
    "boss_career_ops.agent.nodes.gap_analysis",
]


def _has_attr(mod_name: str, attr: str) -> bool:
    mod = import_module(mod_name)
    return hasattr(mod, attr)


@contextmanager
def _patch_llm(mock_llm=None, available=False):
    patches = []
    for mod in _NODE_MODULES:
        if _has_attr(mod, "is_llm_available"):
            p = patch(f"{mod}.is_llm_available", return_value=available)
            p.start()
            patches.append(p)
        if _has_attr(mod, "get_llm"):
            p = patch(f"{mod}.get_llm", return_value=mock_llm)
            p.start()
            patches.append(p)
    try:
        yield
    finally:
        for p in reversed(patches):
            p.stop()


@contextmanager
def _patch_tools(**tool_overrides):
    patches = []
    for tool_name, val in tool_overrides.items():
        for mod in _NODE_MODULES:
            if not _has_attr(mod, tool_name):
                continue
            if callable(val) and not isinstance(val, type):
                p = patch(f"{mod}.{tool_name}", side_effect=val)
            else:
                p = patch(f"{mod}.{tool_name}", return_value=val)
            p.start()
            patches.append(p)
    try:
        yield
    finally:
        for p in reversed(patches):
            p.stop()


_SYSTEM_PROMPTS = {
    "ORCHESTRATOR_SYSTEM": "你是一个路由器",
    "SEARCH_STRATEGY_SYSTEM": "生成搜索关键词",
    "SEARCH_STRATEGY_USER": "用户搜索意图：{query}",
    "EVALUATE_SYSTEM": None,
    "RESUME_SYSTEM": "润色简历",
    "APPLY_SYSTEM": "生成打招呼语",
    "GAP_ANALYSIS_SYSTEM": "分析技能差距",
}


@contextmanager
def _patch_system_prompts():
    patches = []
    for prompt_name, replacement in _SYSTEM_PROMPTS.items():
        if replacement is None:
            continue
        for mod in _NODE_MODULES:
            if _has_attr(mod, prompt_name):
                p = patch(f"{mod}.{prompt_name}", replacement)
                p.start()
                patches.append(p)
    try:
        yield
    finally:
        for p in reversed(patches):
            p.stop()


class TestRouteByIntent:
    def test_search_intent(self):
        assert route_by_intent({"intent": "search"}) == "search"

    def test_evaluate_intent(self):
        assert route_by_intent({"intent": "evaluate"}) == "evaluate"

    def test_resume_intent(self):
        assert route_by_intent({"intent": "resume"}) == "resume"

    def test_apply_intent(self):
        assert route_by_intent({"intent": "apply"}) == "apply"

    def test_gap_analysis_intent(self):
        assert route_by_intent({"intent": "gap_analysis"}) == "gap_analysis"

    def test_resume_apply_routes_to_resume(self):
        assert route_by_intent({"intent": "resume+apply"}) == "resume"

    def test_unknown_intent_defaults_to_search(self):
        assert route_by_intent({"intent": "unknown"}) == "search"

    def test_empty_intent_defaults_to_search(self):
        assert route_by_intent({"intent": ""}) == "search"


class TestRouteAfterResume:
    def test_resume_apply_intent_routes_to_apply(self):
        state = {"intent": "resume+apply", "next_action": ""}
        assert route_after_resume(state) == "apply"

    def test_resume_intent_without_apply_goes_to_end(self):
        state = {"intent": "resume", "next_action": ""}
        assert route_after_resume(state) == END

    def test_resume_with_next_action_routes_to_next(self):
        state = {"intent": "resume", "next_action": "evaluate"}
        assert route_after_resume(state) == "evaluate"

    def test_resume_apply_intent_with_next_action_prefers_apply(self):
        state = {"intent": "resume+apply", "next_action": "evaluate"}
        assert route_after_resume(state) == "apply"


class TestRouteAfterAction:
    def test_no_next_action_goes_to_end(self):
        state = {"next_action": ""}
        assert route_after_action(state) == END

    def test_next_action_routes_to_node(self):
        for name in NODE_NAMES:
            state = {"next_action": name}
            assert route_after_action(state) == name

    def test_invalid_next_action_goes_to_end(self):
        state = {"next_action": "nonexistent"}
        assert route_after_action(state) == END


class TestGraphCompilesAndExecutes:
    @pytest.mark.asyncio
    async def test_graph_compiles_successfully(self):
        with _patch_llm(available=False):
            app = build_career_agent()
            assert app is not None

    @pytest.mark.asyncio
    async def test_graph_executes_search_via_keyword_routing(self):
        mock_llm = _make_mock_llm(json.dumps({
            "intent": "search",
            "params": {},
            "next_action": "search",
        }))
        mock_results = [
            {"job_id": "j1", "job_name": "Python开发", "company_name": "公司A", "city": "深圳", "salary": "20K-40K", "skills": ["Python"], "security_id": "sec1"},
        ]
        with _patch_system_prompts(), \
             _patch_llm(mock_llm, available=True), \
             _patch_tools(search_jobs=mock_results):
            app = build_career_agent()
            result = await app.ainvoke(_base_state(
                messages=[{"role": "user", "content": "搜索Python职位"}],
            ))
            assert "j1" in result.get("job_ids", [])
            assert result["job_details"]["j1"]["job_name"] == "Python开发"

    @pytest.mark.asyncio
    async def test_graph_executes_keyword_fallback_when_no_llm(self):
        mock_results = [
            {"job_id": "j2", "job_name": "Go开发", "company_name": "公司B", "city": "北京", "salary": "25K-50K", "skills": ["Go"], "security_id": "sec2"},
        ]
        with _patch_llm(available=False), \
             _patch_tools(search_jobs=mock_results):
            app = build_career_agent()
            result = await app.ainvoke(_base_state(
                messages=[{"role": "user", "content": "搜索Go职位"}],
            ))
            assert "j2" in result.get("job_ids", [])


class TestResumeApplyChain:
    @pytest.mark.asyncio
    async def test_resume_apply_intent_executes_both_nodes(self):
        mock_llm = _make_mock_llm(json.dumps({
            "intent": "resume+apply",
            "params": {"current_job_id": "j1"},
            "next_action": "resume",
        }))
        job_detail = {
            "job_id": "j1", "job_name": "Python开发", "company_name": "公司A",
            "security_id": "sec1", "city": "深圳", "salary": "20K-40K",
        }

        call_log = []

        def track_write_resume(job_id, content):
            call_log.append(("write_resume", job_id))

        def track_greet(security_id, job_id):
            call_log.append(("greet", job_id))
            return Result.success(data={"message": "ok"})

        def track_apply(security_id, job_id):
            call_log.append(("apply", job_id))
            return Result.success(data={"message": "ok"})

        with _patch_system_prompts(), \
             _patch_llm(mock_llm, available=True), \
             _patch_tools(
                 get_job_detail=job_detail,
                 get_cv="# 简历\nPython工程师5年经验",
                 write_resume=track_write_resume,
                 greet_recruiter=track_greet,
                 apply_job=track_apply,
             ):
            app = build_career_agent()
            result = await app.ainvoke(_base_state(
                messages=[{"role": "user", "content": "帮我改简历并投递"}],
                intent="resume+apply",
                job_ids=["j1"],
                current_job_id="j1",
            ))
            resume_calls = [c for c in call_log if c[0] == "write_resume"]
            apply_calls = [c for c in call_log if c[0] == "apply"]
            assert len(resume_calls) >= 1, f"期望至少1次write_resume, 实际: {call_log}"
            assert len(apply_calls) >= 1, f"期望至少1次apply, 实际: {call_log}"
            resume_idx = call_log.index(resume_calls[0])
            apply_idx = call_log.index(apply_calls[0])
            assert resume_idx < apply_idx, f"简历应在投递前: resume@{resume_idx}, apply@{apply_idx}"


class TestMultiStepOrchestration:
    @pytest.mark.asyncio
    async def test_search_to_evaluate_via_next_action(self):
        mock_llm_responses = iter([
            MagicMock(content=json.dumps({
                "intent": "search",
                "params": {},
                "next_action": "search",
            })),
            MagicMock(content='{"keywords": ["Python"]}'),
            MagicMock(content=json.dumps({
                "scores": {"匹配度": {"score": 4, "reason": "技能匹配"}},
                "total_score": 4.0,
                "grade": "B",
                "analysis": "匹配度较高",
            })),
        ])
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(side_effect=lambda msgs: next(mock_llm_responses))

        search_results = [
            {"job_id": "j1", "job_name": "Python开发", "company_name": "公司A", "city": "深圳", "salary": "20K-40K", "skills": ["Python"], "security_id": "sec1"},
        ]
        job_detail = {"job_id": "j1", "job_name": "Python开发", "company_name": "公司A", "city": "深圳", "salary": "20K-40K", "skills": ["Python"]}

        with _patch_system_prompts(), \
             _patch_llm(mock_llm, available=True), \
             _patch_tools(search_jobs=search_results, get_job_detail=job_detail):
            app = build_career_agent()
            result = await app.ainvoke(_base_state(
                messages=[{"role": "user", "content": "搜索Python职位"}],
                intent="search",
                next_action="search",
            ))
            assert "j1" in result.get("job_ids", [])


class TestErrorsReducer:
    def test_errors_field_has_add_reducer(self):
        hints = AgentState.__annotations__
        errors_type = hints.get("errors")
        assert errors_type is not None
        assert hasattr(errors_type, "__metadata__")
        assert errors_type.__metadata__[0] is operator.add

    @pytest.mark.asyncio
    async def test_errors_accumulate_across_nodes(self):
        with _patch_llm(available=False), \
             _patch_tools(search_jobs=[], get_profile={"name": "测试", "skills": []}, get_cv=""):
            app = build_career_agent()
            result = await app.ainvoke(_base_state(
                messages=[{"role": "user", "content": "搜索Python职位"}],
                intent="search",
                next_action="search",
            ))
            assert isinstance(result.get("errors", []), list)
