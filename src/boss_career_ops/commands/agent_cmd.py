import asyncio
from boss_career_ops.display.logger import get_logger
from rich.console import Console

logger = get_logger(__name__)
console = Console()

def run_agent(query: str, interactive: bool = False):
    """AI Agent 对话式求职助手"""
    from boss_career_ops.agent.graph import build_career_agent
    from boss_career_ops.agent.state import AgentState

    graph = build_career_agent()

    if interactive:
        console.print("[bold cyan]BCO Agent 交互模式（输入 quit 退出）[/bold cyan]")
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
        while True:
            try:
                user_input = input("你: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if user_input.lower() in ("quit", "exit", "q"):
                break
            if not user_input:
                continue
            state["messages"] = [{"role": "user", "content": user_input}]
            try:
                result = asyncio.run(_run_graph(graph, state))
                _print_result(result)
                state.update(result)
            except Exception as e:
                logger.warning("Agent 执行失败: %s", e)
                console.print(f"[red]执行失败: {e}[/red]")
    else:
        if not query:
            console.print("[red]请提供查询内容，或使用 --interactive 进入交互模式[/red]")
            return
        state = {
            "messages": [{"role": "user", "content": query}],
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
        try:
            result = asyncio.run(_run_graph(graph, state))
            _print_result(result)
        except Exception as e:
            logger.warning("Agent 执行失败: %s", e)
            console.print(f"[red]执行失败: {e}[/red]")

async def _run_graph(graph, state: dict) -> dict:
    return await graph.ainvoke(state)

def _print_result(result: dict):
    """打印 Agent 执行结果"""
    if result.get("evaluation_results"):
        for job_id, ev in result["evaluation_results"].items():
            console.print(f"\n[bold]职位 {job_id} 评估结果:[/bold]")
            console.print(f"  评分: {ev.get('score', 'N/A')} | 等级: {ev.get('grade', 'N/A')}")
            if ev.get("analysis"):
                console.print(f"  分析: {ev['analysis']}")
    if result.get("resume_versions"):
        for job_id, resume in result["resume_versions"].items():
            console.print(f"\n[bold]职位 {job_id} 简历已生成[/bold]")
    if result.get("skill_gaps"):
        gaps = result["skill_gaps"]
        console.print(f"\n[bold]技能差距分析:[/bold]")
        if isinstance(gaps, dict) and gaps.get("missing_skills"):
            for skill in gaps["missing_skills"]:
                console.print(f"  - {skill.get('skill', '')} (优先级: {skill.get('priority', '')})")
    if result.get("errors"):
        for err in result["errors"]:
            console.print(f"[red]错误: {err}[/red]")
    if result.get("next_action"):
        console.print(f"\n[dim]建议下一步: {result['next_action']}[/dim]")
