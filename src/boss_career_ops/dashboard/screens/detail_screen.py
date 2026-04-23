from textual.widgets import Static, Markdown
from textual.containers import VerticalScroll

from boss_career_ops.pipeline.manager import PipelineManager


class DetailScreen(VerticalScroll):
    def __init__(self):
        super().__init__()
        self._current_job_id: str = ""

    def compose(self):
        yield Static("# 职位详情", id="title")
        yield Static("选择流水线中的职位查看详情", id="detail_placeholder")

    def show_job(self, job_id: str, security_id: str = "") -> None:
        self._current_job_id = job_id
        for child in self.query(Static).results():
            if child.id != "title":
                child.remove()
        for child in self.query(Markdown).results():
            child.remove()
        try:
            pm = PipelineManager()
            with pm:
                job = pm.get_job(job_id)
        except Exception:
            self.mount(Static(f"获取职位 {job_id} 详情失败"))
            return
        if not job:
            self.mount(Static(f"未找到职位: {job_id}"))
            return
        md_parts = [
            f"## {job.get('job_name', '未知职位')}",
            f"**公司**: {job.get('company_name', '')}",
            f"**薪资**: {job.get('salary_desc', '')}",
            f"**阶段**: {job.get('stage', '')}",
            f"**评分**: {job.get('score', 'N/A')} ({job.get('grade', 'N/A')})",
        ]
        if job.get("skills"):
            md_parts.append(f"**技能要求**: {job.get('skills', '')}")
        if job.get("city"):
            md_parts.append(f"**城市**: {job.get('city', '')}")
        if job.get("experience"):
            md_parts.append(f"**经验要求**: {job.get('experience', '')}")
        if job.get("education"):
            md_parts.append(f"**学历要求**: {job.get('education', '')}")
        if job.get("evaluate_report"):
            md_parts.append("\n### 评估报告")
            md_parts.append(job.get("evaluate_report", ""))
        md_content = "\n\n".join(md_parts)
        self.mount(Markdown(md_content))
