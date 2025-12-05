"""Triage: decide where a message goes. It never answers.

  knowledge  -> cited answer from the help centre
  account    -> scoped tools over this customer's own data
  escalate   -> a person, with context

Hard rules run before the model. Anything about money leaving the customer,
legal threats or deleting data goes to a person no matter how the model
would have classified it — those are cheap to recognise and expensive to get
wrong.
"""
from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, ValidationError

from . import llm

HARD_ESCALATE = [
    (r"\b(refund|charge ?back|dispute[d]? (the )?charge|money back)\b", "refund or chargeback"),
    (r"\b(lawyer|solicitor|legal action|sue|court|gdpr request|data subject)\b", "legal / data rights"),
    (r"\b(delete|close|cancel) (my|our|the) (account|workspace)\b", "account deletion or cancellation"),
    (r"\b(hacked|compromised|unauthori[sz]ed|someone (else )?logged)\b", "possible security incident"),
]


class Triage(BaseModel):
    route: Literal["knowledge", "account", "escalate"]
    intent: str
    sentiment: Literal["calm", "frustrated", "angry"]
    reason: str


SYSTEM = """Classify a customer support message for Flowdesk, a scheduling and
invoicing SaaS. Do not answer it.

route:
  knowledge — how something works, settings, policies, how-to
  account   — about THIS customer's own subscription, invoices, plan, payment status
  escalate  — complaints, anything the customer wants a human for, anything unclear
intent: a few words, e.g. "reset 2fa", "invoice copy", "plan price"
sentiment: calm | frustrated | angry
reason: one short sentence

Reply as JSON with keys route, intent, sentiment, reason."""


def classify(message: str, history: list[dict] | None = None) -> Triage:
    for pattern, why in HARD_ESCALATE:
        if re.search(pattern, message, re.I):
            return Triage(route="escalate", intent=why, sentiment="calm", reason=f"hard rule: {why}")
    msg = llm.chat([{"role": "system", "content": SYSTEM}, *(history or [])[-4:],
                    {"role": "user", "content": message}], fmt=Triage.model_json_schema())
    try:
        t = Triage.model_validate_json(msg["content"])
    except (ValidationError, json.JSONDecodeError):
        return Triage(route="escalate", intent="unclassified", sentiment="calm",
                      reason="triage output invalid")
    if t.sentiment == "angry":
        # an angry customer gets a person, not a better-worded paragraph
        return t.model_copy(update={"route": "escalate", "reason": f"angry customer: {t.reason}"})
    return t
