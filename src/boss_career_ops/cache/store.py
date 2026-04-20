import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from boss_career_ops.config.settings import BCO_HOME
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)

DEFAULT_DB_PATH = BCO_HOME / "cache.db"


class CacheStore:
    def __init__(self, db_path: str | Path | None = None, default_ttl: int = 3600):
        self._db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._default_ttl = default_ttl

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def open(self):
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                created_at REAL NOT NULL,
                ttl INTEGER DEFAULT 3600
            )
        """)
        self._conn.commit()

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def get(self, key: str) -> Any | None:
        if not self._conn:
            raise RuntimeError("CacheStore 未打开，请使用 context manager")
        cursor = self._conn.execute(
            "SELECT value, created_at, ttl FROM cache WHERE key = ?", (key,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        value_json, created_at, ttl = row
        if time.time() - created_at > ttl:
            self._conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            self._conn.commit()
            return None
        try:
            return json.loads(value_json)
        except json.JSONDecodeError:
            return value_json

    def set(self, key: str, value: Any, ttl: int | None = None):
        if not self._conn:
            raise RuntimeError("CacheStore 未打开，请使用 context manager")
        effective_ttl = ttl if ttl is not None else self._default_ttl
        value_json = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
        self._conn.execute(
            "INSERT OR REPLACE INTO cache (key, value, created_at, ttl) VALUES (?, ?, ?, ?)",
            (key, value_json, time.time(), effective_ttl),
        )
        self._conn.commit()

    def delete(self, key: str):
        if not self._conn:
            raise RuntimeError("CacheStore 未打开，请使用 context manager")
        self._conn.execute("DELETE FROM cache WHERE key = ?", (key,))
        self._conn.commit()

    def clear(self):
        if not self._conn:
            raise RuntimeError("CacheStore 未打开，请使用 context manager")
        self._conn.execute("DELETE FROM cache")
        self._conn.commit()

    def cleanup_expired(self):
        if not self._conn:
            raise RuntimeError("CacheStore 未打开，请使用 context manager")
        cutoff = time.time()
        self._conn.execute(
            "DELETE FROM cache WHERE created_at + ttl < ?", (cutoff,)
        )
        self._conn.commit()

    def keys(self, pattern: str | None = None) -> list[str]:
        if not self._conn:
            raise RuntimeError("CacheStore 未打开，请使用 context manager")
        if pattern:
            sql_pattern = pattern.replace("*", "%").replace("?", "_")
            cursor = self._conn.execute(
                "SELECT key FROM cache WHERE key LIKE ?", (sql_pattern,)
            )
        else:
            cursor = self._conn.execute("SELECT key FROM cache")
        return [row[0] for row in cursor.fetchall()]
