import sys

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import click

from boss_career_ops import __version__


@click.group()
@click.version_option(version=__version__, prog_name="bco")
def cli():
    """BOSS直聘 AI 求职全流程系统"""


@cli.command()
def doctor():
    """环境诊断"""
    from boss_career_ops.commands.doctor import run_doctor
    run_doctor()


@cli.command()
def setup():
    """初始化配置（首次使用）"""
    from boss_career_ops.commands.setup import run_setup
    run_setup()


@cli.command()
@click.option("--profile", default="", help="Chrome 配置文件名（如 Default、Profile 2），默认自动选择")
def login(profile):
    """登录 BOSS 直聘（3 级降级）"""
    from boss_career_ops.commands.login import run_login
    run_login(profile=profile)


@cli.command()
def status():
    """检查登录态"""
    from boss_career_ops.commands.status import run_status
    run_status()


@cli.command()
@click.argument("keyword")
@click.option("--city", default="", help="城市筛选")
@click.option("--welfare", default="", help="福利筛选（逗号分隔）")
@click.option("--page", default=1, type=int, help="起始页码")
@click.option("--limit", default=15, type=int, help="每页数量")
@click.option("--pages", default=1, type=int, help="连续获取页数（受 search_max_pages 限制）")
@click.option("-o", "--output", default="", help="输出到文件（绕过管道编码问题）")
def search(keyword, city, welfare, page, limit, pages, output):
    """搜索职位 + 福利筛选"""
    from boss_career_ops.commands.search import run_search
    run_search(keyword, city, welfare, page, limit, pages, output=output or None)


@cli.command()
def recommend():
    """个性化推荐"""
    from boss_career_ops.commands.recommend import run_recommend
    run_recommend()


@cli.command()
@click.argument("target", required=False)
@click.option("--from-search", is_flag=True, help="对上次搜索结果批量评估")
def evaluate(target, from_search):
    """5 维评估（单个/批量）"""
    from boss_career_ops.commands.evaluate import run_evaluate
    run_evaluate(target, from_search)


@cli.command()
@click.argument("security_id")
@click.argument("job_id")
def greet(security_id, job_id):
    """打招呼"""
    from boss_career_ops.commands.greet import run_greet
    run_greet(security_id, job_id)


@cli.command()
@click.argument("keyword")
@click.option("--city", default="", help="城市筛选")
def batch_greet(keyword, city):
    """批量打招呼"""
    from boss_career_ops.commands.greet import run_batch_greet
    run_batch_greet(keyword, city)


@cli.command()
@click.argument("security_id")
@click.argument("job_id")
@click.option("--resume", "resume_job_id", default="", help="投递前先上传简历（指定 job_id 生成并上传）")
def apply(security_id, job_id, resume_job_id):
    """投递简历（浏览器通道）"""
    from boss_career_ops.commands.apply import run_apply
    run_apply(security_id, job_id, resume_job_id)


@cli.command()
@click.argument("job_id")
@click.option("--format", "fmt", default="md", type=click.Choice(["md", "pdf"]), help="输出格式")
@click.option("--upload", is_flag=True, help="上传简历到 BOSS 直聘平台（需 --format pdf）")
def resume(job_id, fmt, upload):
    """生成定制简历（MD/PDF）"""
    from boss_career_ops.commands.resume import run_resume
    run_resume(job_id, fmt, upload)


@cli.command()
@click.option("--export", "export_fmt", default="", type=click.Choice(["csv", "json", "html", "md"]), help="导出格式")
def chat(export_fmt):
    """聊天管理 + 导出"""
    from boss_career_ops.commands.chat import run_chat
    run_chat(export_fmt)


@cli.command()
@click.argument("security_id")
def chatmsg(security_id):
    """聊天消息历史"""
    from boss_career_ops.commands.chatmsg import run_chatmsg
    run_chatmsg(security_id)


@cli.command()
@click.argument("security_id")
def chat_summary(security_id):
    """聊天摘要"""
    from boss_career_ops.commands.chatmsg import run_chat_summary
    run_chat_summary(security_id)


@cli.command()
@click.argument("security_id")
@click.option("--tag", required=True, help="标签名称")
def mark(security_id, tag):
    """联系人标签"""
    from boss_career_ops.commands.mark import run_mark
    run_mark(security_id, tag)


@cli.command()
def pipeline():
    """求职流水线"""
    from boss_career_ops.commands.pipeline import run_pipeline
    run_pipeline()


@cli.command()
@click.argument("keyword")
@click.option("--city", default="", help="城市筛选")
@click.option("-o", "--output", default="", help="输出文件路径")
@click.option("--count", default=50, type=int, help="导出数量")
@click.option("--format", "fmt", default="csv", type=click.Choice(["csv", "json", "html", "md"]), help="导出格式")
def export(keyword, city, output, count, fmt):
    """多格式导出"""
    from boss_career_ops.commands.export import run_export
    run_export(keyword, city, output, count, fmt)


@cli.command()
@click.argument("job_id")
def interview(job_id):
    """面试准备"""
    from boss_career_ops.commands.interview import run_interview
    run_interview(job_id)


@cli.command("agent-evaluate")
@click.argument("job_id", required=False)
@click.option("--stage", default=None, help="按阶段筛选职位")
@click.option("--limit", default=10, type=int, help="最多输出多少个职位")
def agent_evaluate(job_id, stage, limit):
    """输出职位数据供 Agent 评估"""
    from boss_career_ops.commands.agent_evaluate import run_agent_evaluate
    run_agent_evaluate(job_id, stage=stage, limit=limit)


@cli.command("agent-save")
@click.argument("subcommand", type=click.Choice(["evaluate", "resume", "chat-summary", "interview-prep"]))
@click.option("--job-id", default="", help="职位 ID")
@click.option("--security-id", default="", help="联系人安全 ID（chat-summary 使用）")
@click.option("--score", default=0.0, type=float, help="评估分数（evaluate 使用）")
@click.option("--grade", default="", help="评估等级（evaluate 使用）")
@click.option("--analysis", default="", help="评估分析（evaluate 使用）")
@click.option("--scores-detail", default=None, help="5 维度评分详情 JSON（evaluate 使用）")
@click.option("--content", default="", help="简历 Markdown 内容（resume 使用）")
@click.option("--data", default="", help="JSON 数据（chat-summary/interview-prep 使用）")
def agent_save(subcommand, job_id, security_id, score, grade, analysis, scores_detail, content, data):
    """保存 Agent AI 结果到数据库"""
    from boss_career_ops.commands.agent_save import (
        run_agent_save_evaluate,
        run_agent_save_resume,
        run_agent_save_chat_summary,
        run_agent_save_interview_prep,
    )
    if subcommand == "evaluate":
        run_agent_save_evaluate(job_id, score, grade, analysis, scores_detail=scores_detail)
    elif subcommand == "resume":
        run_agent_save_resume(job_id, content)
    elif subcommand == "chat-summary":
        run_agent_save_chat_summary(security_id, data)
    elif subcommand == "interview-prep":
        run_agent_save_interview_prep(job_id, data)


@cli.command("rag-index")
@click.option("--reindex", is_flag=True, help="全量重建索引")
def rag_index(reindex):
    """构建/更新 RAG 知识库索引"""
    from boss_career_ops.commands.rag import run_rag_index
    run_rag_index(reindex=reindex)


@cli.command("rag-search")
@click.argument("query")
@click.option("--collection", default="jd", type=click.Choice(["jd", "resume", "interview"]), help="搜索的集合")
@click.option("--top-k", default=10, type=int, help="返回结果数量")
def rag_search(query, collection, top_k):
    """RAG 语义搜索"""
    from boss_career_ops.commands.rag import run_rag_search
    run_rag_search(query, collection, top_k)


@cli.command("agent")
@click.argument("query", nargs=-1)
@click.option("--interactive", is_flag=True, help="交互模式")
def agent_cmd(query, interactive):
    """AI Agent 对话式求职助手"""
    from boss_career_ops.commands.agent_cmd import run_agent
    run_agent(" ".join(query), interactive=interactive)


@cli.command("mcp-server")
def mcp_server():
    """启动 MCP Server（供 Claude Desktop 等客户端调用）"""
    from boss_career_ops.commands.mcp_server import run_mcp_server
    run_mcp_server()


@cli.command()
def dashboard():
    """启动 TUI Dashboard"""
    from boss_career_ops.commands.dashboard import run_dashboard
    run_dashboard()


@cli.group()
def bridge():
    """Bridge Daemon 管理"""


@bridge.command("status")
def bridge_status():
    """查看 Bridge Daemon 状态"""
    from boss_career_ops.commands.bridge import run_bridge_status
    run_bridge_status()


@bridge.command("test")
def bridge_test():
    """Bridge 连通性诊断"""
    from boss_career_ops.commands.bridge import run_bridge_test
    run_bridge_test()


@cli.command("skill-update")
@click.option("--check", "check_only", is_flag=True, help="仅检查远程版本，不输出内容")
def skill_update(check_only):
    """检查并获取最新 skill.md"""
    from boss_career_ops.commands.skill_update import run_skill_update
    run_skill_update(check_only=check_only)
