"""Conversation orchestration: triage, then one of three handlers.

Started deliberately narrow (FAQ answers + escalate). Account tools sit behind
SUPPORT_FAQ_ONLY=0 until deflection and satisfaction numbers justify them.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import account, config, handoff, knowledge, triage

ESCALATE_MSG = ("I'm not able to answer that one reliably, so I'm passing you to "
                "a member of the support team. They'll reply here.")


@dataclass
class Reply:
    text: str
    route: str                      # knowledge | account | escalated
    citations: list[str] = field(default_factory=list)
    ticket_id: int | None = None


@dataclass
class Conversation:
    customer_id: str
    history: list[dict] = field(default_factory=list)

    def add(self, role: str, text: str) -> None:
        self.history.append({"role": role, "content": text})


def handle(conv: Conversation, message: str) -> Reply:
    conv.add("user", message)
    t = triage.classify(message, conv.history[:-1])
    context = {"triage": t.model_dump()}

    reply = None
    if t.route == "knowledge":
        ans = knowledge.answer(message, conv.history[:-1])
        if ans.covered:
            reply = Reply(ans.text, "knowledge", ans.citations)
        else:
            context["docs"] = "no help article covers this"
    elif t.route == "account" and config.FAQ_ONLY:
        context["account"] = "account tools disabled (FAQ-only mode)"
    elif t.route == "account":
        text, facts = account.answer(conv.customer_id, message)
        context["account_facts"] = facts
        if text:
            reply = Reply(text, "account")
        else:
            context["account"] = "account lookup didn't resolve it"

    if reply is None:
        reason = t.reason if t.route == "escalate" else context.get("docs") or context.get("account", t.reason)
        priority = "urgent" if t.sentiment == "angry" or t.reason.startswith("hard rule") else "normal"
        ticket = handoff.open_ticket(conv.customer_id, reason, conv.history, context, priority)
        reply = Reply(ESCALATE_MSG, "escalated", ticket_id=ticket)
    conv.add("assistant", reply.text)
    return reply
