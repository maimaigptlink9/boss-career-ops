import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from boss_career_ops.config.settings import BCO_HOME
from boss_career_ops.config.singleton import SingletonMeta
from boss_career_ops.pipeline.stages import Stage, next_stage
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)

DB_PATH = BCO_HOME / "pipeline.db"


class PipelineManager(metaclass=SingletonMeta):

    def __init__(self, db_path: str | Path | None = None):
        self._db_path = Path(db_path) if db_path else DB_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._ref_count = 0

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def open(self):
        self._ref_count += 1
        if self._conn is not None:
            return
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS pipeline (
                job_id TEXT PRIMARY KEY,
                job_name TEXT DEFAULT '',
                company_name TEXT DEFAULT '',
                salary_desc TEXT DEFAULT '',
                stage TEXT NOT NULL DEFAULT '发现',
                score REAL DEFAULT 0.0,
                grade TEXT DEFAULT '',
                security_id TEXT DEFAULT '',
                data TEXT DEFAULT '{}',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        self._conn.commit()

    def close(self):
        self._ref_count -= 1
        if self._ref_count > 0 or self._conn is None:
            return
        self._conn.close()
        self._conn = None

    def add_job(self, job_id: str, job_name: str = "", company_name: str = "", salary_desc: str = "", security_id: str = "", data: dict | None = None):
        if not self._conn:
            raise RuntimeError("PipelineManager 未打开")
        now = time.time()
        self._conn.execute(
            "INSERT OR IGNORE INTO pipeline (job_id, job_name, company_name, salary_desc, stage, security_id, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (job_id, job_name, company_name, salary_desc, Stage.DISCOVERED.value, security_id, json.dumps(data or {}, ensure_ascii=False), now, now),
        )
        self._conn.commit()

    def upsert_job(self, job_id: str, job_name: str = "", company_name: str = "", salary_desc: str = "", security_id: str = "", data: dict | None = None):
        if not self._conn:
            raise RuntimeError("PipelineManager 未打开")
        now = time.time()
        self._conn.execute(
            """INSERT INTO pipeline (job_id, job_name, company_name, salary_desc, stage, security_id, data, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(job_id) DO UPDATE SET
                   data = json_patch(pipeline.data, excluded.data),
                   updated_at = excluded.updated_at""",
            (job_id, job_name, company_name, salary_desc, Stage.DISCOVERED.value, security_id, json.dumps(data or {}, ensure_ascii=False), now, now),
        )
        self._conn.commit()

    def batch_add_jobs(self, jobs: list[dict]):
        if not self._conn:
            raise RuntimeError("PipelineManager 未打开")
        now = time.time()
        rows = []
        for j in jobs:
            rows.append((
                j.get("encryptJobId", ""),
                j.get("jobName", ""),
                j.get("brandName", ""),
                j.get("salaryDesc", ""),
                Stage.DISCOVERED.value,
                j.get("securityId", ""),
                json.dumps({}, ensure_ascii=False),
                now,
                now,
            ))
        self._conn.executemany(
            "INSERT OR IGNORE INTO pipeline (job_id, job_name, company_name, salary_desc, stage, security_id, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        self._conn.commit()

    def update_job_data(self, job_id: str, data_updates: dict):
        if not self._conn:
            raise RuntimeError("PipelineManager 未打开")
        cursor = self._conn.execute("SELECT data FROM pipeline WHERE job_id = ?", (job_id,))
        row = cursor.fetchone()
        if not row:
            return
        current_data = json.loads(row[0]) if row[0] else {}
        current_data.update(data_updates)
        self._conn.execute(
            "UPDATE pipeline SET data = ?, updated_at = ? WHERE job_id = ?",
            (json.dumps(current_data, ensure_ascii=False), time.time(), job_id),
        )
        self._conn.commit()

    def update_stage(self, job_id: str, stage: Stage):
        if not self._conn:
            raise RuntimeError("PipelineManager 未打开")
        self._conn.execute(
            "UPDATE pipeline SET stage = ?, updated_at = ? WHERE job_id = ?",
            (stage.value, time.time(), job_id),
        )
        self._conn.commit()

    def update_score(self, job_id: str, score: float, grade: str):
        if not self._conn:
            raise RuntimeError("PipelineManager 未打开")
        self._conn.execute(
            "UPDATE pipeline SET score = ?, grade = ?, updated_at = ? WHERE job_id = ?",
            (score, grade, time.time(), job_id),
        )
        self._conn.commit()

    def advance_stage(self, job_id: str) -> Stage | None:
        if not self._conn:
            raise RuntimeError("PipelineManager 未打开")
        cursor = self._conn.execute("SELECT stage FROM pipeline WHERE job_id = ?", (job_id,))
        row = cursor.fetchone()
        if not row:
            return None
        current = Stage(row[0])
        nxt = next_stage(current)
        if nxt:
            self.update_stage(job_id, nxt)
            return nxt
        return None

    def get_job(self, job_id: str) -> dict | None:
        if not self._conn:
            raise RuntimeError("PipelineManager 未打开")
        cursor = self._conn.execute("SELECT * FROM pipeline WHERE job_id = ?", (job_id,))
        row = cursor.fetchone()
        if not row:
            return None
        cols = ["job_id", "job_name", "company_name", "salary_desc", "stage", "score", "grade", "security_id", "data", "created_at", "updated_at"]
        return dict(zip(cols, row))

    def list_jobs(self, stage: str | None = None) -> list[dict]:
        if not self._conn:
            raise RuntimeError("PipelineManager 未打开")
        if stage:
            cursor = self._conn.execute("SELECT * FROM pipeline WHERE stage = ? ORDER BY updated_at DESC", (stage,))
        else:
            cursor = self._conn.execute("SELECT * FROM pipeline ORDER BY updated_at DESC")
        cols = ["job_id", "job_name", "company_name", "salary_desc", "stage", "score", "grade", "security_id", "data", "created_at", "updated_at"]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def get_stale_jobs(self, days: int = 3) -> list[dict]:
        if not self._conn:
            raise RuntimeError("PipelineManager 未打开")
        cutoff = time.time() - days * 86400
        cursor = self._conn.execute("SELECT * FROM pipeline WHERE updated_at < ? AND stage != 'offer' ORDER BY updated_at ASC", (cutoff,))
        cols = ["job_id", "job_name", "company_name", "salary_desc", "stage", "score", "grade", "security_id", "data", "created_at", "updated_at"]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def get_daily_summary(self) -> dict:
        if not self._conn:
            raise RuntimeError("PipelineManager 未打开")
        now = time.time()
        today_start = now - (now % 86400)
        cursor = self._conn.execute("SELECT COUNT(*) FROM pipeline WHERE created_at >= ?", (today_start,))
        new_count = cursor.fetchone()[0]
        cursor = self._conn.execute("SELECT stage, COUNT(*) FROM pipeline GROUP BY stage")
        by_stage = {row[0]: row[1] for row in cursor.fetchall()}
        cursor = self._conn.execute("SELECT COUNT(*) FROM pipeline WHERE updated_at < ? AND stage != 'offer'", (now - 3 * 86400,))
        stale_count = cursor.fetchone()[0]
        return {
            "new_today": new_count,
            "by_stage": by_stage,
            "stale_count": stale_count,
            "total": sum(by_stage.values()),
        }
