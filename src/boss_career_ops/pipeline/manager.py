import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator, Union

from boss_career_ops.config.settings import BCO_HOME
from boss_career_ops.config.singleton import SingletonMeta
from boss_career_ops.pipeline.stages import Stage
from boss_career_ops.display.logger import get_logger
from boss_career_ops.platform.models import Job

logger = get_logger(__name__)

DB_PATH = BCO_HOME / "pipeline.db"

_PIPELINE_COLS = [
    "job_id", "job_name", "company_name", "salary_desc",
    "stage", "score", "grade", "security_id", "status",
    "data", "created_at", "updated_at",
]

STATUS_ACTIVE = "active"
STATUS_DISMISSED = "dismissed"

_AI_RESULT_COLS = [
    "id", "job_id", "task_type", "result", "source", "created_at",
]

_DB_LOCK_RETRIES = 3
_DB_LOCK_DELAY = 0.05


class PipelineManager(metaclass=SingletonMeta):

    def __init__(self, db_path: str | Path | None = None):
        self._db_path = Path(db_path) if db_path else DB_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._schema_initialized = False
        self._schema_lock = threading.Lock()

    @property
    def _conn(self) -> sqlite3.Connection | None:
        return getattr(self._local, 'conn', None)

    @_conn.setter
    def _conn(self, value: sqlite3.Connection | None):
        self._local.conn = value

    @property
    def _ref_count(self) -> int:
        return getattr(self._local, 'ref_count', 0)

    @_ref_count.setter
    def _ref_count(self, value: int):
        self._local.ref_count = value

    @property
    def _batch_mode(self) -> bool:
        return getattr(self._local, 'batch_mode', False)

    @_batch_mode.setter
    def _batch_mode(self, value: bool):
        self._local.batch_mode = value

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def _db_execute(self, sql: str, params: Any = None):
        for attempt in range(_DB_LOCK_RETRIES):
            try:
                if params is not None:
                    return self._conn.execute(sql, params)
                return self._conn.execute(sql)
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() and attempt < _DB_LOCK_RETRIES - 1:
                    time.sleep(_DB_LOCK_DELAY * (2 ** attempt))
                    continue
                raise

    def _db_executemany(self, sql: str, params_list: list):
        for attempt in range(_DB_LOCK_RETRIES):
            try:
                return self._conn.executemany(sql, params_list)
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() and attempt < _DB_LOCK_RETRIES - 1:
                    time.sleep(_DB_LOCK_DELAY * (2 ** attempt))
                    continue
                raise

    def _db_commit(self):
        for attempt in range(_DB_LOCK_RETRIES):
            try:
                self._conn.commit()
                return
            except sqlite3.OperationalError as e:
                if "locked" in str(e).lower() and attempt < _DB_LOCK_RETRIES - 1:
                    time.sleep(_DB_LOCK_DELAY * (2 ** attempt))
                    continue
                raise

    def open(self):
        self._ref_count += 1
        if self._conn is not None:
            return
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.execute("PRAGMA busy_timeout=30000")
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    def _init_schema(self):
        with self._schema_lock:
            if self._schema_initialized:
                return
            conn = self._conn
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pipeline (
                    job_id TEXT PRIMARY KEY,
                    job_name TEXT DEFAULT '',
                    company_name TEXT DEFAULT '',
                    salary_desc TEXT DEFAULT '',
                    stage TEXT NOT NULL DEFAULT '发现',
                    score REAL DEFAULT 0.0,
                    grade TEXT DEFAULT '',
                    security_id TEXT DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'active',
                    data TEXT DEFAULT '{}',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            conn.commit()
            try:
                conn.execute("ALTER TABLE pipeline ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
                conn.commit()
            except sqlite3.OperationalError:
                pass
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ai_results (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id     TEXT NOT NULL,
                    task_type  TEXT NOT NULL,
                    result     TEXT NOT NULL,
                    source     TEXT DEFAULT 'agent',
                    created_at REAL NOT NULL,
                    UNIQUE(job_id, task_type)
                )
            """)
            conn.commit()
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_stage ON pipeline(stage)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_updated ON pipeline(updated_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_status ON pipeline(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_results_job_task ON ai_results(job_id, task_type)")
            conn.commit()
            self._schema_initialized = True

    def close(self):
        self._ref_count -= 1
        if self._ref_count > 0 or self._conn is None:
            return
        self._conn.close()
        self._conn = None

    @contextmanager
    def batch_commit(self) -> Generator[None, None, None]:
        self._batch_mode = True
        try:
            yield
            self._db_commit()
        finally:
            self._batch_mode = False

    def upsert_job(self, job_or_id: Union[Job, str], job_name: str = "", company_name: str = "", salary_desc: str = "", security_id: str = "", data: dict | None = None):
        if isinstance(job_or_id, Job):
            job = job_or_id
            job_id = job.job_id
            job_name = job.job_name
            company_name = job.company_name
            salary_desc = job.salary_desc
            security_id = job.security_id
            if data is None:
                data = job.raw_data or {}
        else:
            job_id = job_or_id
        if not self._conn:
            raise RuntimeError("PipelineManager 未打开")
        now = time.time()
        self._db_execute(
            """INSERT INTO pipeline (job_id, job_name, company_name, salary_desc, stage, security_id, status, data, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(job_id) DO UPDATE SET
                   data = json_patch(pipeline.data, excluded.data),
                   updated_at = excluded.updated_at""",
            (job_id, job_name, company_name, salary_desc, Stage.DISCOVERED.value, security_id, STATUS_ACTIVE, json.dumps(data or {}, ensure_ascii=False), now, now),
        )
        if not self._batch_mode:
            self._db_commit()

    def batch_add_jobs(self, jobs: list[Union[Job, dict]]):
        if not self._conn:
            raise RuntimeError("PipelineManager 未打开")
        now = time.time()
        dismissed_ids = set()
        cursor = self._db_execute("SELECT job_id FROM pipeline WHERE status = ?", (STATUS_DISMISSED,))
        for row in cursor.fetchall():
            dismissed_ids.add(row[0])
        rows = []
        for j in jobs:
            job = Job.normalize(j)
            if job.job_id in dismissed_ids:
                continue
            rows.append((
                job.job_id,
                job.job_name,
                job.company_name,
                job.salary_desc,
                Stage.DISCOVERED.value,
                job.security_id,
                STATUS_ACTIVE,
                json.dumps({}, ensure_ascii=False),
                now,
                now,
            ))
        if rows:
            self._db_executemany(
                "INSERT OR IGNORE INTO pipeline (job_id, job_name, company_name, salary_desc, stage, security_id, status, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                rows,
            )
        if not self._batch_mode:
            self._db_commit()

    def update_job_data(self, job_id: str, data_updates: dict):
        if not self._conn:
            raise RuntimeError("PipelineManager 未打开")
        cursor = self._db_execute("SELECT data FROM pipeline WHERE job_id = ?", (job_id,))
        row = cursor.fetchone()
        if not row:
            return
        current_data = json.loads(row[0]) if row[0] else {}
        current_data.update(data_updates)
        self._db_execute(
            "UPDATE pipeline SET data = ?, updated_at = ? WHERE job_id = ?",
            (json.dumps(current_data, ensure_ascii=False), time.time(), job_id),
        )
        if not self._batch_mode:
            self._db_commit()

    def update_stage(self, job_id: str, stage: Stage):
        if not self._conn:
            raise RuntimeError("PipelineManager 未打开")
        self._db_execute(
            "UPDATE pipeline SET stage = ?, updated_at = ? WHERE job_id = ?",
            (stage.value, time.time(), job_id),
        )
        if not self._batch_mode:
            self._db_commit()

    def update_score(self, job_id: str, score: float, grade: str):
        if not self._conn:
            raise RuntimeError("PipelineManager 未打开")
        self._db_execute(
            "UPDATE pipeline SET score = ?, grade = ?, updated_at = ? WHERE job_id = ?",
            (score, grade, time.time(), job_id),
        )
        if not self._batch_mode:
            self._db_commit()

    def get_job(self, job_id: str) -> dict | None:
        if not self._conn:
            raise RuntimeError("PipelineManager 未打开")
        cursor = self._db_execute("SELECT * FROM pipeline WHERE job_id = ?", (job_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return dict(zip(_PIPELINE_COLS, row))

    def list_jobs(self, stage: str | None = None, status: str | None = STATUS_ACTIVE) -> list[dict]:
        if not self._conn:
            raise RuntimeError("PipelineManager 未打开")
        conditions = []
        params = []
        if stage:
            conditions.append("stage = ?")
            params.append(stage)
        if status:
            conditions.append("status = ?")
            params.append(status)
        where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
        cursor = self._db_execute(f"SELECT * FROM pipeline{where} ORDER BY updated_at DESC", params)
        return [dict(zip(_PIPELINE_COLS, row)) for row in cursor.fetchall()]

    def get_stale_jobs(self, days: int = 3) -> list[dict]:
        if not self._conn:
            raise RuntimeError("PipelineManager 未打开")
        cutoff = time.time() - days * 86400
        cursor = self._db_execute("SELECT * FROM pipeline WHERE status = ? AND updated_at < ? AND stage != 'offer' ORDER BY updated_at ASC", (STATUS_ACTIVE, cutoff))
        return [dict(zip(_PIPELINE_COLS, row)) for row in cursor.fetchall()]

    def get_daily_summary(self) -> dict:
        if not self._conn:
            raise RuntimeError("PipelineManager 未打开")
        now = time.time()
        today_start = now - (now % 86400)
        cursor = self._db_execute("SELECT COUNT(*) FROM pipeline WHERE created_at >= ?", (today_start,))
        new_count = cursor.fetchone()[0]
        cursor = self._db_execute("SELECT stage, COUNT(*) FROM pipeline GROUP BY stage")
        by_stage = {row[0]: row[1] for row in cursor.fetchall()}
        cursor = self._db_execute("SELECT COUNT(*) FROM pipeline WHERE updated_at < ? AND stage != 'offer'", (now - 3 * 86400,))
        stale_count = cursor.fetchone()[0]
        return {
            "new_today": new_count,
            "by_stage": by_stage,
            "stale_count": stale_count,
            "total": sum(by_stage.values()),
        }

    def save_ai_result(self, job_id: str, task_type: str, result: str, source: str = "agent"):
        if not self._conn:
            raise RuntimeError("PipelineManager 未打开")
        now = time.time()
        self._db_execute(
            """INSERT INTO ai_results (job_id, task_type, result, source, created_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(job_id, task_type) DO UPDATE SET
                   result = excluded.result,
                   source = excluded.source,
                   created_at = excluded.created_at""",
            (job_id, task_type, result, source, now),
        )
        if not self._batch_mode:
            self._db_commit()

    def get_ai_result(self, job_id: str, task_type: str) -> dict | None:
        if not self._conn:
            raise RuntimeError("PipelineManager 未打开")
        cursor = self._db_execute(
            "SELECT id, job_id, task_type, result, source, created_at FROM ai_results WHERE job_id = ? AND task_type = ?",
            (job_id, task_type),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return dict(zip(_AI_RESULT_COLS, row))

    def get_ai_results(self, job_id: str) -> list[dict]:
        if not self._conn:
            raise RuntimeError("PipelineManager 未打开")
        cursor = self._db_execute(
            "SELECT id, job_id, task_type, result, source, created_at FROM ai_results WHERE job_id = ? ORDER BY created_at DESC",
            (job_id,),
        )
        return [dict(zip(_AI_RESULT_COLS, row)) for row in cursor.fetchall()]

    def dismiss_job(self, job_id: str) -> bool:
        if not self._conn:
            raise RuntimeError("PipelineManager 未打开")
        cursor = self._db_execute(
            "UPDATE pipeline SET status = ?, updated_at = ? WHERE job_id = ? AND status = ?",
            (STATUS_DISMISSED, time.time(), job_id, STATUS_ACTIVE),
        )
        if not self._batch_mode:
            self._db_commit()
        return cursor.rowcount > 0

    def restore_job(self, job_id: str) -> bool:
        if not self._conn:
            raise RuntimeError("PipelineManager 未打开")
        cursor = self._db_execute(
            "UPDATE pipeline SET status = ?, updated_at = ? WHERE job_id = ? AND status = ?",
            (STATUS_ACTIVE, time.time(), job_id, STATUS_DISMISSED),
        )
        if not self._batch_mode:
            self._db_commit()
        return cursor.rowcount > 0

    def batch_dismiss(self, job_ids: list[str]) -> int:
        if not self._conn:
            raise RuntimeError("PipelineManager 未打开")
        if not job_ids:
            return 0
        now = time.time()
        placeholders = ",".join("?" * len(job_ids))
        cursor = self._db_execute(
            f"UPDATE pipeline SET status = ?, updated_at = ? WHERE job_id IN ({placeholders}) AND status = ?",
            [STATUS_DISMISSED, now] + job_ids + [STATUS_ACTIVE],
        )
        if not self._batch_mode:
            self._db_commit()
        return cursor.rowcount

    def batch_dismiss_by_score(self, max_score: float) -> int:
        if not self._conn:
            raise RuntimeError("PipelineManager 未打开")
        cursor = self._db_execute(
            "UPDATE pipeline SET status = ?, updated_at = ? WHERE score <= ? AND status = ?",
            (STATUS_DISMISSED, time.time(), max_score, STATUS_ACTIVE),
        )
        if not self._batch_mode:
            self._db_commit()
        return cursor.rowcount

    def batch_dismiss_by_grade(self, grades: list[str]) -> int:
        if not self._conn:
            raise RuntimeError("PipelineManager 未打开")
        if not grades:
            return 0
        placeholders = ",".join("?" * len(grades))
        cursor = self._db_execute(
            f"UPDATE pipeline SET status = ?, updated_at = ? WHERE grade IN ({placeholders}) AND status = ?",
            [STATUS_DISMISSED, time.time()] + grades + [STATUS_ACTIVE],
        )
        if not self._batch_mode:
            self._db_commit()
        return cursor.rowcount

    def batch_restore(self, job_ids: list[str]) -> int:
        if not self._conn:
            raise RuntimeError("PipelineManager 未打开")
        if not job_ids:
            return 0
        now = time.time()
        placeholders = ",".join("?" * len(job_ids))
        cursor = self._db_execute(
            f"UPDATE pipeline SET status = ?, updated_at = ? WHERE job_id IN ({placeholders}) AND status = ?",
            [STATUS_ACTIVE, now] + job_ids + [STATUS_DISMISSED],
        )
        if not self._batch_mode:
            self._db_commit()
        return cursor.rowcount

    def get_unevaluated(self, limit: int = 50) -> list[dict]:
        if not self._conn:
            raise RuntimeError("PipelineManager 未打开")
        cursor = self._db_execute(
            "SELECT * FROM pipeline WHERE status = ? AND stage = ? ORDER BY created_at DESC LIMIT ?",
            (STATUS_ACTIVE, Stage.DISCOVERED.value, limit),
        )
        return [dict(zip(_PIPELINE_COLS, row)) for row in cursor.fetchall()]

    def is_dismissed(self, job_id: str) -> bool:
        if not self._conn:
            raise RuntimeError("PipelineManager 未打开")
        cursor = self._db_execute("SELECT status FROM pipeline WHERE job_id = ?", (job_id,))
        row = cursor.fetchone()
        return row is not None and row[0] == STATUS_DISMISSED
