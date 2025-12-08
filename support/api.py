"""uvicorn support.api:app --port 8020"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import handoff, session
from .bot import Conversation, handle

app = FastAPI(title="support-triage-bot")
conversations: dict[str, Conversation] = {}
AGENT_TOKEN = os.environ.get("SUPPORT_AGENT_TOKEN", "dev-agent-token")
STATIC = Path(__file__).parent / "static"


def customer(authorization: str = Header(...)) -> str:
    cid = session.verify(authorization.removeprefix("Bearer ").strip())
    if not cid:
        raise HTTPException(401, "invalid session")
    return cid


def agent(authorization: str = Header(...)) -> None:
    if authorization.removeprefix("Bearer ").strip() != AGENT_TOKEN:
        raise HTTPException(401)


class ChatIn(BaseModel):
    message: str
    conversation_id: str | None = None


@app.post("/chat")
def chat(body: ChatIn, customer_id: str = Depends(customer)) -> dict:
    cid = body.conversation_id or uuid.uuid4().hex
    conv = conversations.get(cid)
    if conv is None or conv.customer_id != customer_id:
        conv = conversations[cid] = Conversation(customer_id)
    reply = handle(conv, body.message)
    return {"conversation_id": cid, "reply": reply.text, "route": reply.route,
            "citations": reply.citations, "ticket_id": reply.ticket_id}


@app.get("/agent/tickets", dependencies=[Depends(agent)])
def tickets(status: str = "open") -> list[dict]:
    return handoff.queue(status)


@app.post("/agent/tickets/{ticket_id}/close", dependencies=[Depends(agent)])
def close_ticket(ticket_id: int) -> dict:
    handoff.close(ticket_id)
    return {"ok": True}


@app.get("/")
def widget() -> FileResponse:
    return FileResponse(STATIC / "widget.html")
