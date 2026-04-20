from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Header, Footer, TabbedContent, TabPane

from boss_career_ops.dashboard.screens.pipeline_screen import PipelineScreen
from boss_career_ops.dashboard.screens.analytics_screen import AnalyticsScreen
from boss_career_ops.dashboard.screens.detail_screen import DetailScreen


class BossCareerOpsApp(App):
    TITLE = "Boss-Career-Ops Dashboard"
    CSS = """
    Screen {
        layout: vertical;
    }
    """

    BINDINGS = [
        ("q", "quit", "退出"),
        ("1", "show_pipeline", "流水线"),
        ("2", "show_analytics", "数据分析"),
        ("3", "show_detail", "职位详情"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("流水线", id="pipeline"):
                yield PipelineScreen()
            with TabPane("数据分析", id="analytics"):
                yield AnalyticsScreen()
            with TabPane("职位详情", id="detail"):
                yield DetailScreen()
        yield Footer()

    def action_show_pipeline(self):
        self.query_one(TabbedContent).active = "pipeline"

    def action_show_analytics(self):
        self.query_one(TabbedContent).active = "analytics"

    def action_show_detail(self):
        self.query_one(TabbedContent).active = "detail"

    def on_pipeline_screen_job_selected(self, message: PipelineScreen.JobSelected) -> None:
        detail = self.query_one(DetailScreen)
        detail.show_job(message.job_id, message.security_id)
        self.query_one(TabbedContent).active = "detail"
