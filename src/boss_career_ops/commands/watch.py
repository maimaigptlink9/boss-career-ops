import json
import time
from pathlib import Path

from boss_career_ops.boss.api.client import BossClient
from boss_career_ops.boss.search_filters import build_search_params
from boss_career_ops.config.settings import WATCHES_DIR
from boss_career_ops.display.error_codes import ErrorCode
from boss_career_ops.display.output import output_json, output_error
from boss_career_ops.display.logger import get_logger
from boss_career_ops.pipeline.manager import PipelineManager

logger = get_logger(__name__)

WATCH_DIR = WATCHES_DIR


def _ensure_dir():
    WATCH_DIR.mkdir(parents=True, exist_ok=True)


def _watch_path(name: str) -> Path:
    return WATCH_DIR / f"{name}.json"


def run_watch_add(name: str, keyword: str, city: str, welfare: str):
    _ensure_dir()
    config = {
        "name": name,
        "keyword": keyword,
        "city": city,
        "welfare": welfare,
        "created_at": time.time(),
        "last_run": None,
        "seen_ids": [],
    }
    with open(_watch_path(name), "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    output_json(
        command="watch_add",
        data=config,
        hints={"next_actions": ["bco watch run " + name, "bco watch list"]},
    )


def run_watch_list():
    _ensure_dir()
    watches = []
    for f in WATCH_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            watches.append({"name": data.get("name", f.stem), "keyword": data.get("keyword", ""), "city": data.get("city", "")})
        except Exception:
            pass
    output_json(command="watch_list", data=watches)


def run_watch_remove(name: str):
    path = _watch_path(name)
    if path.exists():
        path.unlink()
        output_json(command="watch_remove", data={"name": name, "removed": True})
    else:
        output_error(command="watch_remove", message=f"监控不存在: {name}", code="NOT_FOUND")


def run_watch_run(name: str):
    path = _watch_path(name)
    if not path.exists():
        output_error(command="watch_run", message=f"监控不存在: {name}", code="NOT_FOUND")
        return
    config = json.loads(path.read_text(encoding="utf-8"))
    client = BossClient()
    params = build_search_params(config["keyword"], config.get("city", ""))
    try:
        resp = client.get("search", params=params)
        if resp.get("code") != 0:
            output_error(command="watch_run", message="搜索失败", code=ErrorCode.SEARCH_ERROR)
            return
        jobs = resp.get("zpData", {}).get("jobList", [])
        seen_ids = set(config.get("seen_ids", []))
        new_jobs = [j for j in jobs if j.get("encryptJobId", "") not in seen_ids]
        if new_jobs:
            try:
                pm = PipelineManager()
                with pm:
                    pm.batch_add_jobs(new_jobs)
                logger.info("已将 %d 条 Watch 新职位写入 Pipeline", len(new_jobs))
            except Exception as e:
                logger.warning("Watch 新职位写入 Pipeline 失败: %s", e)
        config["seen_ids"] = list(seen_ids | {j.get("encryptJobId", "") for j in jobs})
        config["last_run"] = time.time()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        output_json(
            command="watch_run",
            data={"new_jobs": len(new_jobs), "total": len(jobs), "details": new_jobs},
            hints={"next_actions": ["bco evaluate --from-search", "bco watch run " + name]},
        )
    except Exception as e:
        output_error(command="watch_run", message=str(e), code="WATCH_ERROR")
