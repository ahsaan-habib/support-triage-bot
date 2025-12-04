"""Conversation orchestration.

v1 is deliberately narrow: answer from the FAQ with citations, escalate
everything else. Earn trust and measure before adding anything that can act.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import handoff, knowledge

ESCALATE_MSG = ("I'm not able to answer that one reliably, so I'm passing you to "
                "a member of the support team. They'll reply here.")


@dataclass
class Reply:
    text: str
    route: str                      # knowledge | escalated
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
    ans = knowledge.answer(message, conv.history[:-1])
    if ans.covered:
        reply = Reply(ans.text, "knowledge", ans.citations)
    else:
        ticket = handoff.open_ticket(conv.customer_id, "not covered by help docs", conv.history,
                                     {"question": message})
        reply = Reply(ESCALATE_MSG, "escalated", ticket_id=ticket)
    conv.add("assistant", reply.text)
    return reply
