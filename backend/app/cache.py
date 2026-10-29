"""SQLite answer cache. Repeated questions replay instantly and don't spend LLM quota.

The file lives in the container and is rebuilt on each deploy, which is fine for a cache.
"""

import hashlib
import json
import re
import sqlite3
import time
from pathlib import Path


def normalize(question: str) -> str:
    return re.sub(r"\s+", " ", question.lower()).strip(" ?.!")


class AnswerCache:
    def __init__(self, path: Path, ttl_s: int):
        self.path, self.ttl_s = path, ttl_s
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._db() as db:
            db.execute("CREATE TABLE IF NOT EXISTS answers (key TEXT PRIMARY KEY, events TEXT, created REAL)")

    def _db(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=5)

    @staticmethod
    def key(question: str) -> str:
        return hashlib.sha256(normalize(question).encode()).hexdigest()

    def get(self, question: str) -> list[dict] | None:
        with self._db() as db:
            row = db.execute("SELECT events, created FROM answers WHERE key = ?", (self.key(question),)).fetchone()
        if not row or time.time() - row[1] > self.ttl_s:
            return None
        return json.loads(row[0])

    def put(self, question: str, events: list[dict]) -> None:
        with self._db() as db:
            db.execute(
                "INSERT OR REPLACE INTO answers (key, events, created) VALUES (?, ?, ?)",
                (self.key(question), json.dumps(events), time.time()),
            )
