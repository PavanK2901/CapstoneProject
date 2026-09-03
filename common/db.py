"""SQLite-backed audit trail for decisions, notifications, and full application records."""
import json
import os
import sqlite3
from contextlib import contextmanager

from common.config import DATA_DIR

DB_PATH = os.path.join(DATA_DIR, "audit.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
    case_id TEXT PRIMARY KEY,
    classification TEXT,
    risk_score INTEGER,
    confidence_level INTEGER,
    key_factors_json TEXT,
    explanation TEXT,
    timestamp TEXT
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT,
    notification_type TEXT,
    recipient TEXT,
    subject TEXT,
    message TEXT,
    timestamp TEXT,
    status TEXT
);

CREATE TABLE IF NOT EXISTS applications (
    case_id TEXT PRIMARY KEY,
    applicant_id TEXT,
    response_json TEXT,
    timestamp TEXT
);
"""


@contextmanager
def get_conn():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(_SCHEMA)


def save_decision(case_id: str, classification: str, risk_score: int, confidence_level: int,
                   key_factors: list, explanation: str, timestamp: str):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO decisions (case_id, classification, risk_score, confidence_level,
                                       key_factors_json, explanation, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(case_id) DO UPDATE SET
                   classification=excluded.classification,
                   risk_score=excluded.risk_score,
                   confidence_level=excluded.confidence_level,
                   key_factors_json=excluded.key_factors_json,
                   explanation=excluded.explanation,
                   timestamp=excluded.timestamp""",
            (case_id, classification, risk_score, confidence_level,
             json.dumps(key_factors), explanation, timestamp)
        )


def get_decision(case_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM decisions WHERE case_id = ?", (case_id,)).fetchone()
        if row is None:
            return None
        record = dict(row)
        record["key_factors"] = json.loads(record.pop("key_factors_json"))
        return record


def get_all_decisions() -> list:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM decisions ORDER BY timestamp DESC").fetchall()
        records = []
        for row in rows:
            record = dict(row)
            record["key_factors"] = json.loads(record.pop("key_factors_json"))
            records.append(record)
        return records


def save_notification(case_id: str, notification_type: str, recipient: str, subject: str,
                       message: str, timestamp: str, status: str) -> int:
    with get_conn() as conn:
        cursor = conn.execute(
            """INSERT INTO notifications (case_id, notification_type, recipient, subject,
                                           message, timestamp, status)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (case_id, notification_type, recipient, subject, message, timestamp, status)
        )
        return cursor.lastrowid


def get_notifications(case_id: str | None = None) -> list:
    with get_conn() as conn:
        if case_id:
            rows = conn.execute(
                "SELECT * FROM notifications WHERE case_id = ? ORDER BY id", (case_id,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM notifications ORDER BY id").fetchall()
        return [dict(row) for row in rows]


def save_application_record(case_id: str, applicant_id: str, response: dict, timestamp: str):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO applications (case_id, applicant_id, response_json, timestamp)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(case_id) DO UPDATE SET
                   applicant_id=excluded.applicant_id,
                   response_json=excluded.response_json,
                   timestamp=excluded.timestamp""",
            (case_id, applicant_id, json.dumps(response), timestamp)
        )


def get_application_record(case_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT response_json FROM applications WHERE case_id = ?", (case_id,)
        ).fetchone()
        if row is None:
            return None
        return json.loads(row["response_json"])
