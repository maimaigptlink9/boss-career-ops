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
def login():
    """登录 BOSS 直聘（4 级降级）"""
    from boss_career_ops.commands.login import run_login
    run_login()


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
def search(keyword, city, welfare, page, limit, pages):
    """搜索职位 + 福利筛选"""
    from boss_career_ops.commands.search import run_search
    run_search(keyword, city, welfare, page, limit, pages)


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
def auto_action():
    """阈值驱动自动执行"""
    from boss_career_ops.commands.auto_action import run_auto_action
    run_auto_action()


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
def apply(security_id, job_id):
    """投递简历"""
    from boss_career_ops.commands.apply import run_apply
    run_apply(security_id, job_id)


@cli.command()
@click.argument("job_id")
@click.option("--format", "fmt", default="md", type=click.Choice(["md", "pdf"]), help="输出格式")
def resume(job_id, fmt):
    """生成定制简历（MD/PDF）"""
    from boss_career_ops.commands.resume import run_resume
    run_resume(job_id, fmt)


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
@click.argument("security_id")
@click.option("--type", "contact_type", required=True, type=click.Choice(["phone", "wechat"]), help="联系方式类型")
def exchange(security_id, contact_type):
    """交换联系方式"""
    from boss_career_ops.commands.exchange import run_exchange
    run_exchange(security_id, contact_type)


@cli.command()
def pipeline():
    """求职流水线"""
    from boss_career_ops.commands.pipeline import run_pipeline
    run_pipeline()


@cli.command()
def follow_up():
    """跟进提醒"""
    from boss_career_ops.commands.follow_up import run_follow_up
    run_follow_up()


@cli.command()
def digest():
    """每日摘要"""
    from boss_career_ops.commands.digest import run_digest
    run_digest()


@cli.group()
def watch():
    """增量监控"""
    pass


@watch.command("add")
@click.argument("name")
@click.argument("keyword")
@click.option("--city", default="", help="城市筛选")
@click.option("--welfare", default="", help="福利筛选")
def watch_add(name, keyword, city, welfare):
    """添加监控"""
    from boss_career_ops.commands.watch import run_watch_add
    run_watch_add(name, keyword, city, welfare)


@watch.command("list")
def watch_list():
    """列出监控"""
    from boss_career_ops.commands.watch import run_watch_list
    run_watch_list()


@watch.command("remove")
@click.argument("name")
def watch_remove(name):
    """移除监控"""
    from boss_career_ops.commands.watch import run_watch_remove
    run_watch_remove(name)


@watch.command("run")
@click.argument("name")
def watch_run(name):
    """执行监控"""
    from boss_career_ops.commands.watch import run_watch_run
    run_watch_run(name)


@cli.command()
def shortlist():
    """精选列表"""
    from boss_career_ops.commands.shortlist import run_shortlist
    run_shortlist()


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


@cli.command()
@click.argument("job_id")
def negotiate(job_id):
    """薪资谈判辅助"""
    from boss_career_ops.commands.negotiate import run_negotiate
    run_negotiate(job_id)


@cli.command()
def dashboard():
    """启动 TUI Dashboard"""
    from boss_career_ops.commands.dashboard import run_dashboard
    run_dashboard()


@cli.command("ai-config")
@click.option("--api-key", default=None, help="API Key")
@click.option("--base-url", default=None, help="API Base URL（OpenAI 兼容）")
@click.option("--model", default=None, help="模型名称")
@click.option("--provider", default=None, help="Provider 类型（openai_compat）")
@click.option("--max-tokens", default=None, type=int, help="最大 token 数")
@click.option("--temperature", default=None, type=float, help="温度参数")
@click.option("--show", "show_config", is_flag=True, help="显示当前配置")
def ai_config(api_key, base_url, model, provider, max_tokens, temperature, show_config):
    """AI 配置管理"""
    from boss_career_ops.commands.ai_config import run_ai_config
    run_ai_config(api_key, base_url, model, provider, max_tokens, temperature, show_config)
