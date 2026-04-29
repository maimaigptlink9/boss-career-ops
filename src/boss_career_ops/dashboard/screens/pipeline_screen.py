from textual.message import Message
from textual.widgets import Static, DataTable, Input, Select, Button
from textual.containers import VerticalScroll, Horizontal

from boss_career_ops.pipeline.manager import PipelineManager, STATUS_ACTIVE, STATUS_DISMISSED
from boss_career_ops.pipeline.stages import Stage


class PipelineScreen(VerticalScroll):
    class JobSelected(Message):
        def __init__(self, job_id: str, security_id: str, job_name: str, company_name: str):
            super().__init__()
            self.job_id = job_id
            self.security_id = security_id
            self.job_name = job_name
            self.company_name = company_name

    class JobDismissed(Message):
        def __init__(self, job_id: str):
            super().__init__()
            self.job_id = job_id

    class JobRestored(Message):
        def __init__(self, job_id: str):
            super().__init__()
            self.job_id = job_id

    def __init__(self):
        super().__init__()
        self._all_rows: list[dict] = []

    def compose(self):
        yield Static("# 求职流水线", id="title")
        with Horizontal():
            yield Input(placeholder="搜索职位/公司...", id="filter_input")
            yield Select(
                [("全部", ""), ("发现", "发现"), ("评估", "评估"),
                 ("投递", "投递"), ("沟通", "沟通"), ("面试", "面试"), ("offer", "offer")],
                id="stage_filter",
                value="",
            )
            yield Select(
                [("活跃", "active"), ("已排除", "dismissed"), ("全部", "all")],
                id="status_filter",
                value="active",
            )
        with Horizontal(classes="pipeline-actions"):
            yield Button("排除选中 [D]", id="btn_dismiss", variant="warning")
            yield Button("恢复选中 [R]", id="btn_restore", variant="success")
            yield Button("刷新", id="btn_refresh", variant="primary")
        table = DataTable(id="pipeline_table")
        table.add_columns("职位", "公司", "薪资", "阶段", "评分", "等级", "状态")
        self._load_data(table, status=STATUS_ACTIVE)
        yield table

    def _load_data(self, table: DataTable, status: str | None = STATUS_ACTIVE):
        table.clear()
        self._all_rows = []
        try:
            pm = PipelineManager()
            with pm:
                jobs = pm.list_jobs(status=status)
                self._all_rows = jobs
                for job in jobs:
                    job_status = job.get("status", STATUS_ACTIVE)
                    status_label = "已排除" if job_status == STATUS_DISMISSED else ""
                    table.add_row(
                        job.get("job_name", ""),
                        job.get("company_name", ""),
                        job.get("salary_desc", ""),
                        job.get("stage", ""),
                        str(round(job.get("score", 0), 1)),
                        job.get("grade", ""),
                        status_label,
                        key=job.get("job_id", ""),
                    )
        except Exception:
            table.add_row("—", "—", "—", "—", "—", "—", "—")

    def _get_selected_job_id(self) -> str | None:
        table = self.query_one("#pipeline_table", DataTable)
        try:
            cursor = table.cursor_row
            row_key = table.get_row_at(cursor).key
            return str(row_key.value) if row_key.value else None
        except Exception:
            return None

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

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn_dismiss":
            self._action_dismiss_selected()
        elif btn_id == "btn_restore":
            self._action_restore_selected()
        elif btn_id == "btn_refresh":
            self._refresh()

    def key_d(self) -> None:
        self._action_dismiss_selected()

    def key_r(self) -> None:
        self._action_restore_selected()

    def _action_dismiss_selected(self) -> None:
        job_id = self._get_selected_job_id()
        if not job_id:
            return
        try:
            pm = PipelineManager()
            with pm:
                pm.dismiss_job(job_id)
            self.post_message(self.JobDismissed(job_id=job_id))
            self._refresh()
        except Exception:
            pass

    def _action_restore_selected(self) -> None:
        job_id = self._get_selected_job_id()
        if not job_id:
            return
        try:
            pm = PipelineManager()
            with pm:
                pm.restore_job(job_id)
            self.post_message(self.JobRestored(job_id=job_id))
            self._refresh()
        except Exception:
            pass

    def on_input_changed(self, event: Input.Changed) -> None:
        self._apply_filters()

    def on_select_changed(self, event: Select.Changed) -> None:
        select_id = event.select.id
        if select_id == "status_filter":
            self._refresh()
        else:
            self._apply_filters()

    def _refresh(self) -> None:
        try:
            status_val = self.query_one("#status_filter", Select).value
            if status_val == "all":
                status = None
            elif status_val == "dismissed":
                status = STATUS_DISMISSED
            else:
                status = STATUS_ACTIVE
            table = self.query_one("#pipeline_table", DataTable)
            self._load_data(table, status=status)
        except Exception:
            pass

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
            job_status = job.get("status", STATUS_ACTIVE)
            status_label = "已排除" if job_status == STATUS_DISMISSED else ""
            table.add_row(
                job.get("job_name", ""),
                job.get("company_name", ""),
                job.get("salary_desc", ""),
                stage,
                str(round(job.get("score", 0), 1)),
                job.get("grade", ""),
                status_label,
                key=job.get("job_id", ""),
            )
