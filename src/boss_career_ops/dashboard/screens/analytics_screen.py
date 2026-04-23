from textual.widgets import Static, DataTable
from textual.containers import VerticalScroll

from boss_career_ops.pipeline.manager import PipelineManager


class AnalyticsScreen(VerticalScroll):
    def compose(self):
        yield Static("# 数据分析", id="title")
        try:
            pm = PipelineManager()
            with pm:
                summary = pm.get_daily_summary()
        except Exception:
            summary = {"new_today": 0, "by_stage": {}, "stale_count": 0, "total": 0}
        yield Static(f"今日新增: {summary.get('new_today', 0)}")
        yield Static(f"总计: {summary.get('total', 0)}")
        yield Static(f"待跟进: {summary.get('stale_count', 0)}")
        table = DataTable()
        table.add_columns("阶段", "数量")
        for stage, count in summary.get("by_stage", {}).items():
            table.add_row(stage, str(count))
        yield table
