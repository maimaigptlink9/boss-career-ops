from textual.message import Message
from textual.widgets import Static, DataTable, Input, Select
from textual.containers import VerticalScroll, Horizontal

from boss_career_ops.pipeline.manager import PipelineManager
from boss_career_ops.pipeline.stages import Stage


class PipelineScreen(VerticalScroll):
    class JobSelected(Message):
        def __init__(self, job_id: str, security_id: str, job_name: str, company_name: str):
            super().__init__()
            self.job_id = job_id
            self.security_id = security_id
            self.job_name = job_name
            self.company_name = company_name

    def __init__(self):
        super().__init__()
        self._all_rows: list[dict] = []

    def compose(self):
        yield Static("# 求职流水线", id="title")
        with Horizontal():
            yield Input(placeholder="搜索职位/公司...", id="filter_input")
            yield Select(
                [("全部", ""), ("发现", "discovered"), ("评估", "evaluated"),
                 ("投递", "applied"), ("沟通", "chatting"), ("面试", "interview"), ("offer", "offer")],
                id="stage_filter",
                value="",
            )
        table = DataTable(id="pipeline_table")
        table.add_columns("职位", "公司", "薪资", "阶段", "评分", "等级")
        try:
            pm = PipelineManager()
            with pm:
                jobs = pm.list_jobs()
                self._all_rows = jobs
                for job in jobs:
                    table.add_row(
                        job.get("job_name", ""),
                        job.get("company_name", ""),
                        job.get("salary_desc", ""),
                        job.get("stage", ""),
                        str(job.get("score", 0)),
                        job.get("grade", ""),
                        key=job.get("job_id", ""),
                    )
        except Exception:
            table.add_row("—", "—", "—", "—", "—", "—")
        yield table

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        row_key = str(event.row_key.value) if event.row_key.value else ""
        for job in self._all_rows:
            if str(job.get("job_id", "")) == row_key:
                self.post_message(self.JobSelected(
                    job_id=job.get("job_id", ""),
                    security_id=job.get("security_id", ""),
                    job_name=job.get("job_name", ""),
                    company_name=job.get("company_name", ""),
                ))
                return

    def on_input_changed(self, event: Input.Changed) -> None:
        self._apply_filters()

    def on_select_changed(self, event: Select.Changed) -> None:
        self._apply_filters()

    def _apply_filters(self) -> None:
        try:
            filter_text = self.query_one("#filter_input", Input).value.lower()
            stage_filter = self.query_one("#stage_filter", Select).value
        except Exception:
            return
        table = self.query_one("#pipeline_table", DataTable)
        table.clear()
        for job in self._all_rows:
            name = job.get("job_name", "").lower()
            company = job.get("company_name", "").lower()
            stage = job.get("stage", "")
            if filter_text and filter_text not in name and filter_text not in company:
                continue
            if stage_filter and stage != stage_filter:
                continue
            table.add_row(
                job.get("job_name", ""),
                job.get("company_name", ""),
                job.get("salary_desc", ""),
                stage,
                str(job.get("score", 0)),
                job.get("grade", ""),
                key=job.get("job_id", ""),
            )
