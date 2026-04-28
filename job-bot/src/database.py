import json
import sqlite3
from contextlib import contextmanager
from typing import Optional

from .config import DB_PATH


SCHEMA = """
CREATE TABLE IF NOT EXISTS cv_profile (
    id INTEGER PRIMARY KEY,
    raw_text TEXT NOT NULL,
    parsed_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    company TEXT,
    location TEXT,
    description TEXT,
    url TEXT UNIQUE NOT NULL,
    source TEXT NOT NULL,
    score INTEGER,
    score_reasoning TEXT,
    status TEXT DEFAULT 'new',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY,
    job_id INTEGER REFERENCES jobs(id),
    cover_letter TEXT,
    status TEXT DEFAULT 'pending',
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def save_cv_profile(raw_text: str, parsed_json_str: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO cv_profile (raw_text, parsed_json) VALUES (?, ?)",
            (raw_text, parsed_json_str),
        )
        return cur.lastrowid


def get_cv_profile() -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, raw_text, parsed_json, created_at "
            "FROM cv_profile ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "raw_text": row["raw_text"],
            "parsed_json": row["parsed_json"],
            "parsed": json.loads(row["parsed_json"]),
            "created_at": row["created_at"],
        }


def save_job(
    title: str,
    company: Optional[str],
    location: Optional[str],
    description: Optional[str],
    url: str,
    source: str,
) -> Optional[int]:
    with get_conn() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO jobs (title, company, location, description, url, source) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (title, company, location, description, url, source),
            )
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return None


def update_job_score(job_id: int, score: int, reasoning: str, status: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE jobs SET score = ?, score_reasoning = ?, status = ? WHERE id = ?",
            (score, reasoning, status, job_id),
        )


def _row_to_job(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "company": row["company"],
        "location": row["location"],
        "description": row["description"],
        "url": row["url"],
        "source": row["source"],
        "score": row["score"],
        "score_reasoning": row["score_reasoning"],
        "status": row["status"],
        "created_at": row["created_at"],
    }


def get_unscored_jobs() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE score IS NULL ORDER BY created_at DESC"
        ).fetchall()
        return [_row_to_job(r) for r in rows]


def get_jobs_by_status(status: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE status = ? "
            "ORDER BY (score IS NULL), score DESC, created_at DESC",
            (status,),
        ).fetchall()
        return [_row_to_job(r) for r in rows]


def get_all_jobs() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM jobs ORDER BY (score IS NULL), score DESC, created_at DESC"
        ).fetchall()
        return [_row_to_job(r) for r in rows]


def get_stats() -> dict:
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) AS c FROM jobs").fetchone()["c"]
        rows = conn.execute(
            "SELECT status, COUNT(*) AS c FROM jobs GROUP BY status"
        ).fetchall()
        by_source = conn.execute(
            "SELECT source, COUNT(*) AS c FROM jobs GROUP BY source"
        ).fetchall()
        cv_count = conn.execute("SELECT COUNT(*) AS c FROM cv_profile").fetchone()["c"]
        return {
            "total_jobs": total,
            "by_status": {r["status"]: r["c"] for r in rows},
            "by_source": {r["source"]: r["c"] for r in by_source},
            "cv_profiles": cv_count,
        }
