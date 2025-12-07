"""Account questions, answered from this customer's own data.

The customer's identity comes from the authenticated session and is bound in
code. It is never a tool parameter, so no prompt — however clever — can make
the model look up someone else's account.
"""
from __future__ import annotations

import json
from functools import partial
from pathlib import Path

from . import llm

DATA = Path(__file__).resolve().parents[1] / "data" / "accounts.json"


def _account(customer_id: str) -> dict:
    # stands in for your billing API, called with the session's customer id
    return json.loads(DATA.read_text())[customer_id]


def get_subscription(customer_id: str) -> dict:
    return _account(customer_id)["subscription"]


def list_invoices(customer_id: str, limit: int = 5) -> list[dict]:
    return _account(customer_id)["invoices"][:limit]


def get_invoice(customer_id: str, invoice_id: str) -> dict:
    for inv in _account(customer_id)["invoices"]:
        if inv["id"] == invoice_id:
            return inv
    return {"error": "no invoice with that id on this account"}


# schemas the model sees: no customer_id anywhere
TOOLS = [
    {"type": "function", "function": {
        "name": "get_subscription",
        "description": "The current customer's plan, billing period, seats, status and renewal date.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "list_invoices",
        "description": "The current customer's most recent invoices (id, date, amount, status).",
        "parameters": {"type": "object", "properties": {
            "limit": {"type": "integer", "description": "how many, default 5"}}}}},
    {"type": "function", "function": {
        "name": "get_invoice",
        "description": "One of the current customer's invoices by id, e.g. INV-2025-1103.",
        "parameters": {"type": "object", "properties": {
            "invoice_id": {"type": "string"}}, "required": ["invoice_id"]}}},
]

SYSTEM = """You are Flowdesk's support assistant answering a question about the
customer's own account. Use the tools to look things up. State only facts the
tools returned; if they don't answer it, say you'll pass it to the team.
You cannot change anything — no refunds, plan changes or cancellations.
Two or three sentences."""


def answer(customer_id: str, question: str, max_steps: int = 3) -> tuple[str, list[dict]]:
    bound = {
        "get_subscription": partial(get_subscription, customer_id),
        "list_invoices": partial(list_invoices, customer_id),
        "get_invoice": partial(get_invoice, customer_id),
    }
    facts: list[dict] = []
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]
    for _ in range(max_steps):
        msg = llm.chat(messages, tools=TOOLS)
        messages.append(msg)
        calls = msg.get("tool_calls") or []
        if not calls:
            return msg["content"].strip(), facts
        for call in calls:
            name, args = call["function"]["name"], call["function"].get("arguments") or {}
            args.pop("customer_id", None)          # belt and braces
            fn = bound.get(name)
            try:
                result = fn(**args) if fn else {"error": f"unknown tool {name}"}
            except TypeError as e:
                result = {"error": f"bad arguments: {e}"}
            facts.append({"tool": name, "args": args, "result": result})
            messages.append({"role": "tool", "tool_name": name, "content": json.dumps(result)})
    return "", facts   # ran out of steps: caller escalates
