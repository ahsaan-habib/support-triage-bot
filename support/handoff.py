"""Human handoff. The person picking it up gets the transcript and everything
the bot already gathered, so the customer never has to repeat themselves."""
from __future__ import annotations

import json
import sqlite3
import time

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    id          INTEGER PRIMARY KEY,
    created     REAL NOT NULL,
    customer_id TEXT NOT NULL,
    reason      TEXT NOT NULL,
    priority    TEXT NOT NULL DEFAULT 'normal',
    transcript  TEXT NOT NULL,       -- json list of {role, content}
    context     TEXT NOT NULL,       -- json: triage result, docs tried, account facts
    status      TEXT NOT NULL DEFAULT 'open'
);
"""


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def open_ticket(customer_id: str, reason: str, transcript: list[dict], context: dict,
                priority: str = "normal") -> int:
    conn = db()
    cur = conn.execute(
        "INSERT INTO tickets (created, customer_id, reason, priority, transcript, context) VALUES (?,?,?,?,?,?)",
        (time.time(), customer_id, reason, priority, json.dumps(transcript), json.dumps(context, default=str)))
    conn.commit()
    return cur.lastrowid


def queue(status: str = "open") -> list[dict]:
    rows = db().execute(
        "SELECT * FROM tickets WHERE status = ? ORDER BY priority = 'urgent' DESC, created", (status,)).fetchall()
    return [{**dict(r), "transcript": json.loads(r["transcript"]), "context": json.loads(r["context"])} for r in rows]


def close(ticket_id: int) -> None:
    conn = db()
    conn.execute("UPDATE tickets SET status = 'closed' WHERE id = ?", (ticket_id,))
    conn.commit()
