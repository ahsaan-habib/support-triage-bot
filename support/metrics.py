"""Measure from day one: deflection, escalation, refusal, satisfaction.

A refusal ("the docs don't cover this" -> human) is a success, not a failure:
it's the bot declining to invent a policy. It's tracked separately so it can't
hide inside "escalations".
"""
from __future__ import annotations

import time

from .handoff import db

SCHEMA = """
CREATE TABLE IF NOT EXISTS turns (
    id              INTEGER PRIMARY KEY,
    ts              REAL NOT NULL,
    conversation_id TEXT NOT NULL,
    route           TEXT NOT NULL,     -- knowledge | account | escalated
    reason          TEXT,
    feedback        INTEGER            -- 1 thumbs up, 0 thumbs down, NULL none
);
"""


def _conn():
    conn = db()
    conn.executescript(SCHEMA)
    return conn


def record(conversation_id: str, route: str, reason: str = "") -> int:
    conn = _conn()
    cur = conn.execute("INSERT INTO turns (ts, conversation_id, route, reason) VALUES (?,?,?,?)",
                       (time.time(), conversation_id, route, reason))
    conn.commit()
    return cur.lastrowid


def feedback(turn_id: int, helpful: bool) -> None:
    conn = _conn()
    conn.execute("UPDATE turns SET feedback = ? WHERE id = ?", (int(helpful), turn_id))
    conn.commit()


def summary(days: float = 7) -> dict:
    rows = _conn().execute("SELECT * FROM turns WHERE ts >= ?", (time.time() - days * 86400,)).fetchall()
    convs: dict[str, list] = {}
    for r in rows:
        convs.setdefault(r["conversation_id"], []).append(r)
    n = len(convs)
    escalated = [c for c in convs.values() if any(t["route"] == "escalated" for t in c)]
    not_covered = [t for t in rows if t["route"] == "escalated" and (t["reason"] or "").startswith("no help article")]
    rated = [t for t in rows if t["feedback"] is not None]
    return {
        "conversations": n,
        # resolved without a person: no turn in the conversation escalated
        "deflection_rate": round(1 - len(escalated) / n, 3) if n else None,
        "escalation_rate": round(len(escalated) / n, 3) if n else None,
        "not_covered_refusals": len(not_covered),
        "csat": round(sum(t["feedback"] for t in rated) / len(rated), 3) if rated else None,
        "rated_turns": len(rated),
    }
