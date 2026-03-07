from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app.config import settings


def connect(db_path: str | None = None) -> sqlite3.Connection:
    path = db_path or settings.db_path
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection):
    try:
        yield
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def init_db(conn: sqlite3.Connection) -> None:
    with transaction(conn):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL,
                source_path TEXT NOT NULL,
                source_ref TEXT NOT NULL,
                subject TEXT NOT NULL,
                sender TEXT NOT NULL,
                date TEXT NOT NULL,
                body TEXT NOT NULL,
                body_preview TEXT NOT NULL,
                body_hash TEXT NOT NULL UNIQUE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS embeddings (
                email_id INTEGER PRIMARY KEY,
                dim INTEGER NOT NULL,
                vector_json TEXT NOT NULL,
                FOREIGN KEY(email_id) REFERENCES emails(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mailbox_state (
                source_path TEXT PRIMARY KEY,
                source_type TEXT NOT NULL,
                processed_offset INTEGER NOT NULL DEFAULT 0,
                processed_emails INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ingest_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT NOT NULL,
                source_path TEXT NOT NULL,
                source_type TEXT NOT NULL,
                started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                ended_at TEXT,
                processed_emails INTEGER NOT NULL DEFAULT 0,
                total_emails_estimate INTEGER NOT NULL DEFAULT 0,
                processed_bytes INTEGER NOT NULL DEFAULT 0,
                total_bytes INTEGER NOT NULL DEFAULT 0,
                throughput_eps REAL NOT NULL DEFAULT 0,
                eta_seconds REAL NOT NULL DEFAULT 0,
                message TEXT NOT NULL DEFAULT ''
            )
            """
        )


def get_mailbox_state(conn: sqlite3.Connection, source_path: str, source_type: str) -> dict:
    row = conn.execute(
        "SELECT * FROM mailbox_state WHERE source_path = ?", (source_path,)
    ).fetchone()
    if row:
        return dict(row)
    with transaction(conn):
        conn.execute(
            "INSERT INTO mailbox_state(source_path, source_type, processed_offset, processed_emails) VALUES(?,?,0,0)",
            (source_path, source_type),
        )
    return {
        "source_path": source_path,
        "source_type": source_type,
        "processed_offset": 0,
        "processed_emails": 0,
    }


def update_mailbox_state(
    conn: sqlite3.Connection,
    source_path: str,
    processed_offset: int,
    processed_emails: int,
) -> None:
    with transaction(conn):
        conn.execute(
            """
            UPDATE mailbox_state
            SET processed_offset = ?, processed_emails = ?, updated_at = CURRENT_TIMESTAMP
            WHERE source_path = ?
            """,
            (processed_offset, processed_emails, source_path),
        )


def insert_email(
    conn: sqlite3.Connection,
    source_type: str,
    source_path: str,
    source_ref: str,
    subject: str,
    sender: str,
    date: str,
    body: str,
    body_preview: str,
    body_hash: str,
) -> int | None:
    try:
        with transaction(conn):
            cur = conn.execute(
                """
                INSERT INTO emails(source_type, source_path, source_ref, subject, sender, date, body, body_preview, body_hash)
                VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    source_type,
                    source_path,
                    source_ref,
                    subject,
                    sender,
                    date,
                    body,
                    body_preview,
                    body_hash,
                ),
            )
        return int(cur.lastrowid)
    except sqlite3.IntegrityError:
        return None


def upsert_embedding(conn: sqlite3.Connection, email_id: int, vector: list[float]) -> None:
    payload = json.dumps(vector)
    with transaction(conn):
        conn.execute(
            """
            INSERT INTO embeddings(email_id, dim, vector_json)
            VALUES(?,?,?)
            ON CONFLICT(email_id) DO UPDATE SET dim=excluded.dim, vector_json=excluded.vector_json
            """,
            (email_id, len(vector), payload),
        )


def list_embeddings(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT e.id AS email_id, e.source_ref, e.subject, e.sender, e.date, e.body, e.body_preview, em.vector_json
        FROM emails e JOIN embeddings em ON e.id = em.email_id
        """
    ).fetchall()
    return [dict(r) for r in rows]


def create_ingest_job(conn: sqlite3.Connection, source_path: str, source_type: str) -> int:
    with transaction(conn):
        cur = conn.execute(
            "INSERT INTO ingest_jobs(status, source_path, source_type, message) VALUES('running',?,?, 'started')",
            (source_path, source_type),
        )
    return int(cur.lastrowid)


def update_ingest_job(conn: sqlite3.Connection, job_id: int, **kwargs) -> None:
    if not kwargs:
        return
    cols = []
    vals = []
    for k, v in kwargs.items():
        cols.append(f"{k} = ?")
        vals.append(v)
    vals.append(job_id)
    with transaction(conn):
        conn.execute(
            f"UPDATE ingest_jobs SET {', '.join(cols)} WHERE id = ?",
            vals,
        )


def finish_ingest_job(conn: sqlite3.Connection, job_id: int, status: str, message: str) -> None:
    with transaction(conn):
        conn.execute(
            """
            UPDATE ingest_jobs
            SET status = ?, message = ?, ended_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (status, message, job_id),
        )


def get_latest_ingest_job(conn: sqlite3.Connection) -> dict | None:
    row = conn.execute("SELECT * FROM ingest_jobs ORDER BY id DESC LIMIT 1").fetchone()
    return dict(row) if row else None
