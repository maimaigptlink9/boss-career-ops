import csv
import json
from pathlib import Path

from boss_career_ops.boss.api.client import BossClient
from boss_career_ops.boss.search_filters import build_search_params
from boss_career_ops.config.settings import EXPORTS_DIR
from boss_career_ops.display.error_codes import ErrorCode
from boss_career_ops.display.output import output_json, output_error
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)


def _sanitize_path(output: str) -> Path:
    p = Path(output)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError("导出路径不安全：不允许绝对路径或路径遍历")
    return p


def _sanitize_csv_value(value: str) -> str:
    if value.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + value
    return value


def run_export(keyword: str, city: str, output: str, count: int, fmt: str):
    client = BossClient()
    params = build_search_params(keyword, city, page_size=min(count, 50))
    try:
        resp = client.get("search", params=params)
        if resp.get("code") != 0:
            output_error(command="export", message="搜索失败", code=ErrorCode.SEARCH_ERROR)
            return
        jobs = resp.get("zpData", {}).get("jobList", [])[:count]
        if output:
            try:
                safe_path = _sanitize_path(output)
            except ValueError as e:
                output_error(command="export", message=str(e), code="PATH_ERROR")
                return
        else:
            safe_path = Path(f"export_{keyword}.{fmt}")
        output_dir = EXPORTS_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
        full_path = output_dir / safe_path
        if fmt == "csv":
            _export_csv(jobs, full_path)
        elif fmt == "json":
            _export_json(jobs, full_path)
        elif fmt == "html":
            _export_html(jobs, full_path)
        elif fmt == "md":
            _export_md(jobs, full_path)
        output_json(
            command="export",
            data={"path": str(full_path), "format": fmt, "count": len(jobs)},
            hints={"next_actions": ["bco evaluate --from-search"]},
        )
    except Exception as e:
        output_error(command="export", message=str(e), code="EXPORT_ERROR")


def _export_csv(jobs: list, path: Path):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["职位名", "公司", "薪资", "城市", "经验", "学历"])
        for job in jobs:
            writer.writerow([
                _sanitize_csv_value(job.get("jobName", "")),
                _sanitize_csv_value(job.get("brandName", "")),
                _sanitize_csv_value(job.get("salaryDesc", "")),
                _sanitize_csv_value(job.get("cityName", "")),
                _sanitize_csv_value(job.get("jobExperience", "")),
                _sanitize_csv_value(job.get("jobDegree", "")),
            ])


def _export_json(jobs: list, path: Path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)


def _export_html(jobs: list, path: Path):
    rows = ""
    for job in jobs:
        rows += f"<tr><td>{job.get('jobName','')}</td><td>{job.get('brandName','')}</td><td>{job.get('salaryDesc','')}</td><td>{job.get('cityName','')}</td></tr>\n"
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>职位导出</title>
<style>table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ddd;padding:8px;text-align:left}}th{{background:#f5f5f5}}</style>
</head><body><h1>职位列表</h1><table><tr><th>职位</th><th>公司</th><th>薪资</th><th>城市</th></tr>{rows}</table></body></html>"""
    path.write_text(html, encoding="utf-8")


def _export_md(jobs: list, path: Path):
    lines = ["# 职位列表\n"]
    for job in jobs:
        lines.append(f"- **{job.get('jobName','')}** @ {job.get('brandName','')} | {job.get('salaryDesc','')} | {job.get('cityName','')}")
    path.write_text("\n".join(lines), encoding="utf-8")
