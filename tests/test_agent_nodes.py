import json
from unittest.mock import AsyncMock, MagicMock, patch
from string import Template

import pytest

from boss_career_ops.agent.nodes.orchestrator import run as orchestrator_run, _keyword_intent
from boss_career_ops.agent.nodes.search import run as search_run
from boss_career_ops.agent.nodes.evaluate import run as evaluate_run
from boss_career_ops.agent.nodes.resume import run as resume_run
from boss_career_ops.agent.nodes.apply import run as apply_run
from boss_career_ops.agent.nodes.gap_analysis import run as gap_analysis_run, _simple_gap_analysis
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


def _patch_orchestrator_prompts():
    return patch(
        "boss_career_ops.agent.nodes.orchestrator.ORCHESTRATOR_SYSTEM",
        "你是一个路由器",
    )


def _patch_search_prompts():
    return patch.multiple(
        "boss_career_ops.agent.nodes.search",
        SEARCH_STRATEGY_SYSTEM="生成搜索关键词",
        SEARCH_STRATEGY_USER="用户搜索意图：{query}",
    )


def _patch_resume_prompts():
    return patch(
        "boss_career_ops.agent.nodes.resume.RESUME_SYSTEM",
        "润色简历",
    )


def _patch_apply_prompts():
    return patch(
        "boss_career_ops.agent.nodes.apply.APPLY_SYSTEM",
        "生成打招呼语",
    )


def _patch_gap_prompts():
    return patch(
        "boss_career_ops.agent.nodes.gap_analysis.GAP_ANALYSIS_SYSTEM",
        "分析技能差距",
    )


class TestOrchestratorNode:
    @pytest.mark.asyncio
    async def test_happy_path_llm_routes_to_search(self):
        mock_llm = _make_mock_llm(json.dumps({
            "intent": "search",
            "params": {},
            "next_action": "search",
        }))
        with _patch_orchestrator_prompts(), \
             patch("boss_career_ops.agent.nodes.orchestrator.get_llm", return_value=mock_llm), \
             patch("boss_career_ops.agent.nodes.orchestrator.is_llm_available", return_value=True):
            result = await orchestrator_run(_base_state(
                messages=[{"role": "user", "content": "搜索Python职位"}],
            ))
            assert result["intent"] == "search"
            assert result["next_action"] == "search"
            assert any("LLM路由" in str(m) for m in result.get("messages", []))

    @pytest.mark.asyncio
    async def test_boundary_empty_messages_returns_error(self):
        with patch("boss_career_ops.agent.nodes.orchestrator.is_llm_available", return_value=False):
            result = await orchestrator_run(_base_state(messages=[]))
            assert result["intent"] == "search"
            assert "无用户输入" in result.get("errors", [])

    @pytest.mark.asyncio
    async def test_fallback_keyword_routing_when_no_llm(self):
        with patch("boss_career_ops.agent.nodes.orchestrator.get_llm", return_value=None), \
             patch("boss_career_ops.agent.nodes.orchestrator.is_llm_available", return_value=False):
            result = await orchestrator_run(_base_state(
                messages=[{"role": "user", "content": "评估一下这个职位"}],
            ))
            assert result["intent"] == "evaluate"
            assert any("关键词路由" in str(m) for m in result.get("messages", []))

    @pytest.mark.asyncio
    async def test_fallback_when_llm_raises_exception(self):
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(side_effect=Exception("API超时"))
        with _patch_orchestrator_prompts(), \
             patch("boss_career_ops.agent.nodes.orchestrator.get_llm", return_value=mock_llm), \
             patch("boss_career_ops.agent.nodes.orchestrator.is_llm_available", return_value=True):
            result = await orchestrator_run(_base_state(
                messages=[{"role": "user", "content": "帮我投递职位"}],
            ))
            assert result["intent"] == "apply"

    @pytest.mark.asyncio
    async def test_fallback_when_llm_returns_invalid_json(self):
        mock_llm = _make_mock_llm("这不是JSON")
        with _patch_orchestrator_prompts(), \
             patch("boss_career_ops.agent.nodes.orchestrator.get_llm", return_value=mock_llm), \
             patch("boss_career_ops.agent.nodes.orchestrator.is_llm_available", return_value=True):
            result = await orchestrator_run(_base_state(
                messages=[{"role": "user", "content": "搜索Go职位"}],
            ))
            assert result["intent"] == "search"

    @pytest.mark.asyncio
    async def test_llm_extracts_job_ids_from_params(self):
        mock_llm = _make_mock_llm(json.dumps({
            "intent": "evaluate",
            "params": {"job_ids": ["j1", "j2"], "current_job_id": "j1"},
            "next_action": "evaluate",
        }))
        with _patch_orchestrator_prompts(), \
             patch("boss_career_ops.agent.nodes.orchestrator.get_llm", return_value=mock_llm), \
             patch("boss_career_ops.agent.nodes.orchestrator.is_llm_available", return_value=True):
            result = await orchestrator_run(_base_state(
                messages=[{"role": "user", "content": "评估这些职位"}],
            ))
            assert result["job_ids"] == ["j1", "j2"]
            assert result["current_job_id"] == "j1"


class TestKeywordIntent:
    def test_search_keywords(self):
        for kw in ["搜索", "找", "搜"]:
            intent, _ = _keyword_intent(f"帮我{kw}Python职位")
            assert intent == "search", f"关键词'{kw}'应路由到search"

    def test_evaluate_keywords(self):
        for kw in ["评估", "匹配", "评分"]:
            intent, _ = _keyword_intent(f"帮我{kw}这个职位")
            assert intent == "evaluate", f"关键词'{kw}'应路由到evaluate"

    def test_resume_keywords(self):
        for kw in ["简历", "改简历"]:
            intent, _ = _keyword_intent(f"帮我生成{kw}")
            assert intent == "resume", f"关键词'{kw}'应路由到resume"

    def test_apply_keywords(self):
        for kw in ["投递", "打招呼", "应聘"]:
            intent, _ = _keyword_intent(f"帮我{kw}这个职位")
            assert intent == "apply", f"关键词'{kw}'应路由到apply"

    def test_gap_analysis_keywords(self):
        for kw in ["技能差距", "技能分析"]:
            intent, _ = _keyword_intent(f"分析{kw}")
            assert intent == "gap_analysis", f"关键词'{kw}'应路由到gap_analysis"

    def test_no_match_defaults_to_search(self):
        intent, _ = _keyword_intent("今天天气怎么样")
        assert intent == "search"


class TestSearchNode:
    @pytest.mark.asyncio
    async def test_happy_path_returns_search_results(self):
        mock_results = [
            {"job_id": "j1", "job_name": "Python开发", "company_name": "公司A", "city": "深圳", "salary": "20K-40K", "skills": ["Python"], "security_id": "sec1"},
            {"job_id": "j2", "job_name": "Go开发", "company_name": "公司B", "city": "北京", "salary": "25K-50K", "skills": ["Go"], "security_id": "sec2"},
        ]
        with patch("boss_career_ops.agent.nodes.search.search_jobs", return_value=mock_results), \
             patch("boss_career_ops.agent.nodes.search.is_llm_available", return_value=False):
            result = await search_run(_base_state(
                messages=[{"role": "user", "content": "Python"}],
            ))
            assert "j1" in result["job_ids"]
            assert "j2" in result["job_ids"]
            assert result["job_details"]["j1"]["job_name"] == "Python开发"

    @pytest.mark.asyncio
    async def test_boundary_empty_keyword_returns_error(self):
        with patch("boss_career_ops.agent.nodes.search.is_llm_available", return_value=False):
            result = await search_run(_base_state(messages=[]))
            assert result["job_ids"] == []
            assert "搜索关键词为空" in result.get("errors", [])

    @pytest.mark.asyncio
    async def test_empty_search_results(self):
        with patch("boss_career_ops.agent.nodes.search.search_jobs", return_value=[]), \
             patch("boss_career_ops.agent.nodes.search.is_llm_available", return_value=False):
            result = await search_run(_base_state(
                messages=[{"role": "user", "content": "Rust"}],
            ))
            assert result["job_ids"] == []
            assert result["job_details"] == {}

    @pytest.mark.asyncio
    async def test_llm_strategy_expands_keywords(self):
        from langchain_core.messages import HumanMessage
        mock_llm = _make_mock_llm(json.dumps({"keywords": ["Python", "FastAPI", "Django"]}))
        call_log = []

        def track_search(keyword, city=""):
            call_log.append(keyword)
            if keyword == "Python":
                return [{"job_id": "j1", "job_name": "Python开发", "company_name": "A", "city": "深圳", "salary": "20K", "skills": ["Python"], "security_id": "s1"}]
            return []

        with _patch_search_prompts(), \
             patch("boss_career_ops.agent.nodes.search.get_llm", return_value=mock_llm), \
             patch("boss_career_ops.agent.nodes.search.is_llm_available", return_value=True), \
             patch("boss_career_ops.agent.nodes.search.search_jobs", side_effect=track_search):
            result = await search_run(_base_state(
                messages=[HumanMessage(content="Python")],
            ))
            assert "Python" in call_log
            assert "FastAPI" in call_log

    @pytest.mark.asyncio
    async def test_deduplication_across_keywords(self):
        mock_llm = _make_mock_llm(json.dumps({"keywords": ["Python", "Python后端"]}))
        duplicate_job = {"job_id": "j1", "job_name": "Python开发", "company_name": "A", "city": "深圳", "salary": "20K", "skills": ["Python"], "security_id": "s1"}

        with _patch_search_prompts(), \
             patch("boss_career_ops.agent.nodes.search.get_llm", return_value=mock_llm), \
             patch("boss_career_ops.agent.nodes.search.is_llm_available", return_value=True), \
             patch("boss_career_ops.agent.nodes.search.search_jobs", return_value=[duplicate_job]):
            result = await search_run(_base_state(
                messages=[{"role": "user", "content": "Python"}],
            ))
            assert result["job_ids"].count("j1") == 1

    @pytest.mark.asyncio
    async def test_llm_parse_failure_falls_back_to_single_keyword(self):
        mock_llm = _make_mock_llm("invalid json")
        with _patch_search_prompts(), \
             patch("boss_career_ops.agent.nodes.search.get_llm", return_value=mock_llm), \
             patch("boss_career_ops.agent.nodes.search.is_llm_available", return_value=True), \
             patch("boss_career_ops.agent.nodes.search.search_jobs", return_value=[
                 {"job_id": "j1", "job_name": "Python", "company_name": "A", "city": "深圳", "salary": "20K", "skills": [], "security_id": "s1"},
             ]):
            result = await search_run(_base_state(
                messages=[{"role": "user", "content": "Python"}],
            ))
            assert "j1" in result["job_ids"]


class TestEvaluateNode:
    @pytest.mark.asyncio
    async def test_happy_path_llm_evaluation(self):
        mock_llm = _make_mock_llm(json.dumps({
            "scores": {"匹配度": {"score": 4, "reason": "技能匹配"}},
            "total_score": 4.0,
            "grade": "B",
            "analysis": "匹配度较高",
        }))
        job_detail = {"job_id": "j1", "job_name": "Python开发", "company_name": "公司A"}
        with patch("boss_career_ops.agent.nodes.evaluate.get_llm", return_value=mock_llm), \
             patch("boss_career_ops.agent.nodes.evaluate.is_llm_available", return_value=True), \
             patch("boss_career_ops.agent.nodes.evaluate.get_job_detail", return_value=job_detail), \
             patch("boss_career_ops.agent.nodes.evaluate.get_profile", return_value={"name": "测试", "skills": ["Python"]}), \
             patch("boss_career_ops.agent.nodes.evaluate.write_evaluation") as mock_write:
            result = await evaluate_run(_base_state(
                job_ids=["j1"],
                job_details={"j1": job_detail},
            ))
            assert "j1" in result["evaluation_results"]
            assert result["evaluation_results"]["j1"]["grade"] == "B"
            mock_write.assert_called_once()

    @pytest.mark.asyncio
    async def test_boundary_no_job_ids_returns_error(self):
        with patch("boss_career_ops.agent.nodes.evaluate.is_llm_available", return_value=False):
            result = await evaluate_run(_base_state(job_ids=[]))
            assert result["evaluation_results"] == {}
            assert "无待评估职位" in result.get("errors", [])

    @pytest.mark.asyncio
    async def test_fallback_to_rule_engine_when_llm_unavailable(self):
        job_detail = {"job_id": "j1", "job_name": "Python开发", "company_name": "公司A"}
        mock_engine = MagicMock()
        mock_engine.evaluate.return_value = {
            "total_score": 3.0,
            "grade": "C",
            "recommendation": "一般匹配",
            "scores": {},
        }
        with patch("boss_career_ops.agent.nodes.evaluate.get_llm", return_value=None), \
             patch("boss_career_ops.agent.nodes.evaluate.is_llm_available", return_value=False), \
             patch("boss_career_ops.agent.nodes.evaluate.get_job_detail", return_value=job_detail), \
             patch("boss_career_ops.agent.nodes.evaluate.get_profile", return_value={"name": "测试", "skills": ["Python"]}), \
             patch("boss_career_ops.agent.nodes.evaluate.write_evaluation"), \
             patch("boss_career_ops.agent.nodes.evaluate.EvaluationEngine", return_value=mock_engine):
            result = await evaluate_run(_base_state(
                job_ids=["j1"],
                job_details={"j1": job_detail},
            ))
            assert "j1" in result["evaluation_results"]
            assert result["evaluation_results"]["j1"]["grade"] == "C"

    @pytest.mark.asyncio
    async def test_fallback_to_rule_engine_when_llm_raises(self):
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(side_effect=Exception("API错误"))
        job_detail = {"job_id": "j1", "job_name": "Python开发", "company_name": "公司A"}
        mock_engine = MagicMock()
        mock_engine.evaluate.return_value = {
            "total_score": 2.5,
            "grade": "C",
            "recommendation": "匹配度一般",
            "scores": {},
        }
        with patch("boss_career_ops.agent.nodes.evaluate.get_llm", return_value=mock_llm), \
             patch("boss_career_ops.agent.nodes.evaluate.is_llm_available", return_value=True), \
             patch("boss_career_ops.agent.nodes.evaluate.get_job_detail", return_value=job_detail), \
             patch("boss_career_ops.agent.nodes.evaluate.get_profile", return_value={"name": "测试", "skills": ["Python"]}), \
             patch("boss_career_ops.agent.nodes.evaluate.write_evaluation"), \
             patch("boss_career_ops.agent.nodes.evaluate.EvaluationEngine", return_value=mock_engine):
            result = await evaluate_run(_base_state(
                job_ids=["j1"],
                job_details={"j1": job_detail},
            ))
            assert "j1" in result["evaluation_results"]
            assert result["evaluation_results"]["j1"]["grade"] == "C"

    @pytest.mark.asyncio
    async def test_job_detail_fetch_failure_records_error(self):
        with patch("boss_career_ops.agent.nodes.evaluate.get_llm", return_value=None), \
             patch("boss_career_ops.agent.nodes.evaluate.is_llm_available", return_value=False), \
             patch("boss_career_ops.agent.nodes.evaluate.get_job_detail", return_value=None), \
             patch("boss_career_ops.agent.nodes.evaluate.get_profile", return_value={"name": "测试", "skills": ["Python"]}):
            result = await evaluate_run(_base_state(
                job_ids=["j_missing"],
                job_details={},
            ))
            assert any("j_missing" in e for e in result.get("errors", []))


class TestResumeNode:
    @pytest.mark.asyncio
    async def test_happy_path_llm_rewrite(self):
        mock_llm = _make_mock_llm("# 润色后简历\n## 核心技能\n- Python\n- FastAPI")
        job_detail = {"job_id": "j1", "job_name": "Python开发", "company_name": "公司A"}
        with _patch_resume_prompts(), \
             patch("boss_career_ops.agent.nodes.resume.get_llm", return_value=mock_llm), \
             patch("boss_career_ops.agent.nodes.resume.is_llm_available", return_value=True), \
             patch("boss_career_ops.agent.nodes.resume.get_job_detail", return_value=job_detail), \
             patch("boss_career_ops.agent.nodes.resume.get_cv", return_value="# 原始简历"), \
             patch("boss_career_ops.agent.nodes.resume.write_resume") as mock_write, \
             patch("boss_career_ops.agent.nodes.resume.RagRetriever", create=True):
            result = await resume_run(_base_state(
                current_job_id="j1",
                job_details={"j1": job_detail},
            ))
            assert "j1" in result["resume_versions"]
            assert "润色后简历" in result["resume_versions"]["j1"]
            mock_write.assert_called_once()

    @pytest.mark.asyncio
    async def test_boundary_no_target_job_returns_error(self):
        with patch("boss_career_ops.agent.nodes.resume.is_llm_available", return_value=False):
            result = await resume_run(_base_state(
                current_job_id="",
                job_ids=[],
            ))
            assert "无目标职位" in result.get("errors", [])

    @pytest.mark.asyncio
    async def test_boundary_empty_cv_returns_error(self):
        job_detail = {"job_id": "j1", "job_name": "Python开发"}
        with patch("boss_career_ops.agent.nodes.resume.is_llm_available", return_value=False), \
             patch("boss_career_ops.agent.nodes.resume.get_job_detail", return_value=job_detail), \
             patch("boss_career_ops.agent.nodes.resume.get_cv", return_value=""):
            result = await resume_run(_base_state(
                current_job_id="j1",
                job_details={"j1": job_detail},
            ))
            assert "简历内容为空" in result.get("errors", [])

    @pytest.mark.asyncio
    async def test_fallback_to_template_generator(self):
        job_detail = {"job_id": "j1", "job_name": "Python开发", "company_name": "公司A"}
        mock_generator = MagicMock()
        mock_generator.generate.return_value = "# 模板简历\n基础内容"
        with patch("boss_career_ops.agent.nodes.resume.get_llm", return_value=None), \
             patch("boss_career_ops.agent.nodes.resume.is_llm_available", return_value=False), \
             patch("boss_career_ops.agent.nodes.resume.get_job_detail", return_value=job_detail), \
             patch("boss_career_ops.agent.nodes.resume.get_cv", return_value="# 原始简历"), \
             patch("boss_career_ops.agent.nodes.resume.write_resume"), \
             patch("boss_career_ops.resume.generator.ResumeGenerator", return_value=mock_generator):
            result = await resume_run(_base_state(
                current_job_id="j1",
                job_details={"j1": job_detail},
            ))
            assert "j1" in result["resume_versions"]
            assert "模板简历" in result["resume_versions"]["j1"]

    @pytest.mark.asyncio
    async def test_fallback_when_llm_raises(self):
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(side_effect=Exception("API超时"))
        job_detail = {"job_id": "j1", "job_name": "Python开发", "company_name": "公司A"}
        mock_generator = MagicMock()
        mock_generator.generate.return_value = "# 兜底简历"
        with _patch_resume_prompts(), \
             patch("boss_career_ops.agent.nodes.resume.get_llm", return_value=mock_llm), \
             patch("boss_career_ops.agent.nodes.resume.is_llm_available", return_value=True), \
             patch("boss_career_ops.agent.nodes.resume.get_job_detail", return_value=job_detail), \
             patch("boss_career_ops.agent.nodes.resume.get_cv", return_value="# 原始简历"), \
             patch("boss_career_ops.agent.nodes.resume.write_resume"), \
             patch("boss_career_ops.resume.generator.ResumeGenerator", return_value=mock_generator):
            result = await resume_run(_base_state(
                current_job_id="j1",
                job_details={"j1": job_detail},
            ))
            assert "j1" in result["resume_versions"]

    @pytest.mark.asyncio
    async def test_job_detail_not_found_returns_error(self):
        with patch("boss_career_ops.agent.nodes.resume.get_job_detail", return_value=None), \
             patch("boss_career_ops.agent.nodes.resume.is_llm_available", return_value=False):
            result = await resume_run(_base_state(
                current_job_id="j_missing",
                job_details={},
            ))
            assert any("j_missing" in e for e in result.get("errors", []))


class TestApplyNode:
    @pytest.mark.asyncio
    async def test_happy_path_greet_and_apply(self):
        job_detail = {
            "job_id": "j1", "job_name": "Python开发",
            "company_name": "公司A", "security_id": "sec1",
        }
        with patch("boss_career_ops.agent.nodes.apply.get_job_detail", return_value=job_detail), \
             patch("boss_career_ops.agent.nodes.apply.get_cv", return_value="# 简历"), \
             patch("boss_career_ops.agent.nodes.apply.greet_recruiter", return_value=Result.success(data={"message": "ok"})) as mock_greet, \
             patch("boss_career_ops.agent.nodes.apply.apply_job", return_value=Result.success(data={"message": "ok"})) as mock_apply, \
             patch("boss_career_ops.agent.nodes.apply.is_llm_available", return_value=False):
            result = await apply_run(_base_state(
                current_job_id="j1",
                job_details={"j1": job_detail},
            ))
            mock_greet.assert_called_once_with("sec1", "j1")
            mock_apply.assert_called_once_with("sec1", "j1")
            assert len(result.get("errors", [])) == 0

    @pytest.mark.asyncio
    async def test_boundary_no_target_job_returns_error(self):
        with patch("boss_career_ops.agent.nodes.apply.is_llm_available", return_value=False):
            result = await apply_run(_base_state(
                current_job_id="",
                job_ids=[],
            ))
            assert "无目标职位" in result.get("errors", [])

    @pytest.mark.asyncio
    async def test_boundary_missing_security_id_returns_error(self):
        job_detail = {"job_id": "j1", "job_name": "Python开发", "company_name": "公司A"}
        with patch("boss_career_ops.agent.nodes.apply.get_job_detail", return_value=job_detail), \
             patch("boss_career_ops.agent.nodes.apply.is_llm_available", return_value=False):
            result = await apply_run(_base_state(
                current_job_id="j1",
                job_details={"j1": job_detail},
            ))
            assert any("security_id" in e for e in result.get("errors", []))

    @pytest.mark.asyncio
    async def test_greet_failure_records_error(self):
        job_detail = {
            "job_id": "j1", "job_name": "Python开发",
            "company_name": "公司A", "security_id": "sec1",
        }
        with patch("boss_career_ops.agent.nodes.apply.get_job_detail", return_value=job_detail), \
             patch("boss_career_ops.agent.nodes.apply.get_cv", return_value="# 简历"), \
             patch("boss_career_ops.agent.nodes.apply.greet_recruiter", return_value=Result.failure(error="打招呼被拒", code="GREET_FAILED")), \
             patch("boss_career_ops.agent.nodes.apply.apply_job", return_value=Result.success(data={"message": "ok"})), \
             patch("boss_career_ops.agent.nodes.apply.is_llm_available", return_value=False):
            result = await apply_run(_base_state(
                current_job_id="j1",
                job_details={"j1": job_detail},
            ))
            assert any("打招呼失败" in e for e in result.get("errors", []))

    @pytest.mark.asyncio
    async def test_apply_failure_records_error(self):
        job_detail = {
            "job_id": "j1", "job_name": "Python开发",
            "company_name": "公司A", "security_id": "sec1",
        }
        with patch("boss_career_ops.agent.nodes.apply.get_job_detail", return_value=job_detail), \
             patch("boss_career_ops.agent.nodes.apply.get_cv", return_value="# 简历"), \
             patch("boss_career_ops.agent.nodes.apply.greet_recruiter", return_value=Result.success(data={"message": "ok"})), \
             patch("boss_career_ops.agent.nodes.apply.apply_job", return_value=Result.failure(error="投递失败", code="APPLY_FAILED")), \
             patch("boss_career_ops.agent.nodes.apply.is_llm_available", return_value=False):
            result = await apply_run(_base_state(
                current_job_id="j1",
                job_details={"j1": job_detail},
            ))
            assert any("投递失败" in e for e in result.get("errors", []))

    @pytest.mark.asyncio
    async def test_greet_exception_records_error(self):
        job_detail = {
            "job_id": "j1", "job_name": "Python开发",
            "company_name": "公司A", "security_id": "sec1",
        }
        with patch("boss_career_ops.agent.nodes.apply.get_job_detail", return_value=job_detail), \
             patch("boss_career_ops.agent.nodes.apply.get_cv", return_value="# 简历"), \
             patch("boss_career_ops.agent.nodes.apply.greet_recruiter", side_effect=Exception("网络错误")), \
             patch("boss_career_ops.agent.nodes.apply.apply_job", return_value=Result.success(data={"message": "ok"})), \
             patch("boss_career_ops.agent.nodes.apply.is_llm_available", return_value=False):
            result = await apply_run(_base_state(
                current_job_id="j1",
                job_details={"j1": job_detail},
            ))
            assert any("打招呼异常" in e for e in result.get("errors", []))

    @pytest.mark.asyncio
    async def test_llm_generates_greeting_message(self):
        mock_llm = _make_mock_llm("您好，我有5年Python经验，期待交流！")
        job_detail = {
            "job_id": "j1", "job_name": "Python开发",
            "company_name": "公司A", "security_id": "sec1",
        }
        with _patch_apply_prompts(), \
             patch("boss_career_ops.agent.nodes.apply.get_llm", return_value=mock_llm), \
             patch("boss_career_ops.agent.nodes.apply.is_llm_available", return_value=True), \
             patch("boss_career_ops.agent.nodes.apply.get_job_detail", return_value=job_detail), \
             patch("boss_career_ops.agent.nodes.apply.get_cv", return_value="# 简历\n5年Python经验"), \
             patch("boss_career_ops.agent.nodes.apply.greet_recruiter", return_value=Result.success(data={"message": "ok"})), \
             patch("boss_career_ops.agent.nodes.apply.apply_job", return_value=Result.success(data={"message": "ok"})):
            result = await apply_run(_base_state(
                current_job_id="j1",
                job_details={"j1": job_detail},
            ))
            mock_llm.ainvoke.assert_called_once()


class TestGapAnalysisNode:
    @pytest.mark.asyncio
    async def test_happy_path_llm_analysis(self):
        mock_llm = _make_mock_llm(json.dumps({
            "missing_skills": [
                {"skill": "Kubernetes", "priority": "high", "suggestion": "学习K8s"},
            ],
            "overall_assessment": "需补充云原生技能",
        }))
        with _patch_gap_prompts(), \
             patch("boss_career_ops.agent.nodes.gap_analysis.get_llm", return_value=mock_llm), \
             patch("boss_career_ops.agent.nodes.gap_analysis.is_llm_available", return_value=True), \
             patch("boss_career_ops.agent.nodes.gap_analysis.get_profile", return_value={"name": "测试", "skills": ["Python", "Go"]}), \
             patch("boss_career_ops.agent.nodes.gap_analysis.list_pipeline_jobs", return_value=[{"job_id": "j1"}]), \
             patch("boss_career_ops.pipeline.manager.PipelineManager") as mock_pm_cls:
            mock_pm = MagicMock()
            mock_pm.__enter__ = MagicMock(return_value=mock_pm)
            mock_pm.__exit__ = MagicMock(return_value=False)
            mock_pm_cls.return_value = mock_pm

            result = await gap_analysis_run(_base_state())
            assert "missing_skills" in result["skill_gaps"]
            assert result["skill_gaps"]["missing_skills"][0]["skill"] == "Kubernetes"

    @pytest.mark.asyncio
    async def test_boundary_no_skills_returns_error(self):
        with patch("boss_career_ops.agent.nodes.gap_analysis.is_llm_available", return_value=False), \
             patch("boss_career_ops.agent.nodes.gap_analysis.get_profile", return_value={"name": "测试", "skills": []}), \
             patch("boss_career_ops.agent.nodes.gap_analysis.list_pipeline_jobs", return_value=[{"job_id": "j1"}]):
            result = await gap_analysis_run(_base_state())
            assert result["skill_gaps"] == {}
            assert any("技能" in e for e in result.get("errors", []))

    @pytest.mark.asyncio
    async def test_boundary_no_pipeline_jobs_returns_error(self):
        with patch("boss_career_ops.agent.nodes.gap_analysis.is_llm_available", return_value=False), \
             patch("boss_career_ops.agent.nodes.gap_analysis.get_profile", return_value={"name": "测试", "skills": ["Python"]}), \
             patch("boss_career_ops.agent.nodes.gap_analysis.list_pipeline_jobs", return_value=[]):
            result = await gap_analysis_run(_base_state())
            assert result["skill_gaps"] == {}
            assert any("Pipeline" in e or "职位" in e for e in result.get("errors", []))

    @pytest.mark.asyncio
    async def test_fallback_simple_comparison_when_no_llm(self):
        with patch("boss_career_ops.agent.nodes.gap_analysis.get_llm", return_value=None), \
             patch("boss_career_ops.agent.nodes.gap_analysis.is_llm_available", return_value=False), \
             patch("boss_career_ops.agent.nodes.gap_analysis.get_profile", return_value={"name": "测试", "skills": ["Python", "Go"]}), \
             patch("boss_career_ops.agent.nodes.gap_analysis.list_pipeline_jobs", return_value=[{"job_id": "j1", "job_name": "Rust开发"}]), \
             patch("boss_career_ops.pipeline.manager.PipelineManager") as mock_pm_cls:
            mock_pm = MagicMock()
            mock_pm.__enter__ = MagicMock(return_value=mock_pm)
            mock_pm.__exit__ = MagicMock(return_value=False)
            mock_pm_cls.return_value = mock_pm

            result = await gap_analysis_run(_base_state())
            assert "missing_skills" in result["skill_gaps"]
            assert "overall_assessment" in result["skill_gaps"]

    @pytest.mark.asyncio
    async def test_fallback_when_llm_raises(self):
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(side_effect=Exception("API超时"))
        with _patch_gap_prompts(), \
             patch("boss_career_ops.agent.nodes.gap_analysis.get_llm", return_value=mock_llm), \
             patch("boss_career_ops.agent.nodes.gap_analysis.is_llm_available", return_value=True), \
             patch("boss_career_ops.agent.nodes.gap_analysis.get_profile", return_value={"name": "测试", "skills": ["Python"]}), \
             patch("boss_career_ops.agent.nodes.gap_analysis.list_pipeline_jobs", return_value=[{"job_id": "j1"}]), \
             patch("boss_career_ops.pipeline.manager.PipelineManager") as mock_pm_cls:
            mock_pm = MagicMock()
            mock_pm.__enter__ = MagicMock(return_value=mock_pm)
            mock_pm.__exit__ = MagicMock(return_value=False)
            mock_pm_cls.return_value = mock_pm

            result = await gap_analysis_run(_base_state())
            assert "skill_gaps" in result

    @pytest.mark.asyncio
    async def test_fallback_when_llm_returns_invalid_json(self):
        mock_llm = _make_mock_llm("not json at all")
        with _patch_gap_prompts(), \
             patch("boss_career_ops.agent.nodes.gap_analysis.get_llm", return_value=mock_llm), \
             patch("boss_career_ops.agent.nodes.gap_analysis.is_llm_available", return_value=True), \
             patch("boss_career_ops.agent.nodes.gap_analysis.get_profile", return_value={"name": "测试", "skills": ["Python"]}), \
             patch("boss_career_ops.agent.nodes.gap_analysis.list_pipeline_jobs", return_value=[{"job_id": "j1"}]), \
             patch("boss_career_ops.pipeline.manager.PipelineManager") as mock_pm_cls:
            mock_pm = MagicMock()
            mock_pm.__enter__ = MagicMock(return_value=mock_pm)
            mock_pm.__exit__ = MagicMock(return_value=False)
            mock_pm_cls.return_value = mock_pm

            result = await gap_analysis_run(_base_state())
            assert "skill_gaps" in result
            assert "missing_skills" in result["skill_gaps"]


class TestSimpleGapAnalysis:
    def test_finds_missing_skills(self):
        skills = ["Python", "Go"]
        jds = ['{"skills": ["Rust", "Python"]}']
        result = _simple_gap_analysis(skills, jds)
        assert len(result["missing_skills"]) > 0
        missing_names = [m["skill"] for m in result["missing_skills"]]
        assert "Go" in missing_names

    def test_no_missing_when_all_present(self):
        skills = ["Python"]
        jds = ['{"skills": ["Python", "Go"]}']
        result = _simple_gap_analysis(skills, jds)
        assert result["missing_skills"] == []

    def test_empty_inputs(self):
        result = _simple_gap_analysis([], [])
        assert result["missing_skills"] == []


class TestActionNodeNextActionReset:
    @pytest.mark.asyncio
    async def test_search_resets_next_action(self):
        with patch("boss_career_ops.agent.nodes.search.search_jobs", return_value=[
            {"job_id": "j1", "job_name": "Python", "company_name": "A", "city": "深圳", "salary": "20K", "skills": [], "security_id": "s1"},
        ]), \
             patch("boss_career_ops.agent.nodes.search.is_llm_available", return_value=False):
            result = await search_run(_base_state(
                messages=[{"role": "user", "content": "Python"}],
                next_action="search",
            ))
            assert result.get("next_action") == "", f"search节点应重置next_action, 实际: {result.get('next_action')}"

    @pytest.mark.asyncio
    async def test_evaluate_resets_next_action(self):
        job_detail = {"job_id": "j1", "job_name": "Python开发"}
        with patch("boss_career_ops.agent.nodes.evaluate.is_llm_available", return_value=False), \
             patch("boss_career_ops.agent.nodes.evaluate.get_job_detail", return_value=job_detail), \
             patch("boss_career_ops.agent.nodes.evaluate.get_profile", return_value={"name": "测试", "skills": ["Python"]}), \
             patch("boss_career_ops.agent.nodes.evaluate.EvaluationEngine", return_value=MagicMock(evaluate=MagicMock(return_value={"total_score": 3, "grade": "C", "recommendation": "一般", "scores": {}}))):
            result = await evaluate_run(_base_state(
                job_ids=["j1"],
                job_details={"j1": job_detail},
                next_action="evaluate",
            ))
            assert result.get("next_action") == "", f"evaluate节点应重置next_action, 实际: {result.get('next_action')}"

    @pytest.mark.asyncio
    async def test_resume_resets_next_action(self):
        job_detail = {"job_id": "j1", "job_name": "Python开发", "company_name": "公司A"}
        mock_generator = MagicMock()
        mock_generator.generate.return_value = "# 简历"
        with patch("boss_career_ops.agent.nodes.resume.is_llm_available", return_value=False), \
             patch("boss_career_ops.agent.nodes.resume.get_job_detail", return_value=job_detail), \
             patch("boss_career_ops.agent.nodes.resume.get_cv", return_value="# 原始简历"), \
             patch("boss_career_ops.resume.generator.ResumeGenerator", return_value=mock_generator):
            result = await resume_run(_base_state(
                current_job_id="j1",
                job_details={"j1": job_detail},
                next_action="resume",
            ))
            assert result.get("next_action") == "", f"resume节点应重置next_action, 实际: {result.get('next_action')}"

    @pytest.mark.asyncio
    async def test_apply_resets_next_action(self):
        job_detail = {"job_id": "j1", "job_name": "Python开发", "company_name": "公司A", "security_id": "sec1"}
        with patch("boss_career_ops.agent.nodes.apply.is_llm_available", return_value=False), \
             patch("boss_career_ops.agent.nodes.apply.get_job_detail", return_value=job_detail), \
             patch("boss_career_ops.agent.nodes.apply.get_cv", return_value="# 简历"), \
             patch("boss_career_ops.agent.nodes.apply.greet_recruiter", return_value=Result.success(data={"message": "ok"})), \
             patch("boss_career_ops.agent.nodes.apply.apply_job", return_value=Result.success(data={"message": "ok"})):
            result = await apply_run(_base_state(
                current_job_id="j1",
                job_details={"j1": job_detail},
                next_action="apply",
            ))
            assert result.get("next_action") == "", f"apply节点应重置next_action, 实际: {result.get('next_action')}"

    @pytest.mark.asyncio
    async def test_gap_analysis_resets_next_action(self):
        with patch("boss_career_ops.agent.nodes.gap_analysis.is_llm_available", return_value=False), \
             patch("boss_career_ops.agent.nodes.gap_analysis.get_profile", return_value={"name": "测试", "skills": ["Python"]}), \
             patch("boss_career_ops.agent.nodes.gap_analysis.list_pipeline_jobs", return_value=[{"job_id": "j1"}]), \
             patch("boss_career_ops.pipeline.manager.PipelineManager") as mock_pm_cls:
            mock_pm = MagicMock()
            mock_pm.__enter__ = MagicMock(return_value=mock_pm)
            mock_pm.__exit__ = MagicMock(return_value=False)
            mock_pm_cls.return_value = mock_pm
            result = await gap_analysis_run(_base_state(
                next_action="gap_analysis",
            ))
            assert result.get("next_action") == "", f"gap_analysis节点应重置next_action, 实际: {result.get('next_action')}"
