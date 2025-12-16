from fastapi.testclient import TestClient

from conftest import triage_json
from support import account, api, bot, config, handoff, metrics, session


def tool_call(name, **args):
    return {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": name, "arguments": args}}]}


def test_account_tools_are_bound_to_the_session_customer(llm):
    fake = llm(tool_call("list_invoices", customer_id="cus_001", limit=1), "Your last invoice failed.")
    text, facts = account.answer("cus_002", "what's my last invoice?")
    assert text == "Your last invoice failed."
    assert facts == [{"tool": "list_invoices", "args": {"limit": 1},
                      "result": [{"id": "INV-2025-0921", "date": "2025-09-21", "amount_eur": 3920.0,
                                  "status": "payment_failed"}]}]
    assert all("customer_id" not in str(t["function"]["parameters"]) for t in fake.calls[0]["tools"])


def test_account_errors_become_observations(llm):
    llm(tool_call("get_invoice", invoice="x"), tool_call("drop_tables"), tool_call("get_subscription"))
    text, facts = account.answer("cus_001", "q", max_steps=3)
    assert text == "" and "bad arguments" in facts[0]["result"]["error"]
    assert facts[1]["result"] == {"error": "unknown tool drop_tables"}
    assert facts[2]["result"]["plan"] == "Pro"


def test_signed_in_customer_without_billing_data_is_not_a_500(llm):
    llm(tool_call("get_subscription"), "I'll pass this to the team.")
    text, facts = account.answer("cus_999", "what's my plan?")
    assert "error" in facts[0]["result"] and text


def test_handle_routes_and_escalates_with_context(indexed, llm, monkeypatch):
    conv = bot.Conversation("cus_001", id="conv1")
    llm(triage_json("knowledge"), "You can export everything as CSV from Settings [1].")
    # knowledge answer depends on what the fake index returns; only check the route machinery
    r = bot.handle(conv, "how do I export my data?")
    assert r.route in ("knowledge", "escalated") and r.turn_id
    monkeypatch.setattr(config, "FAQ_ONLY", True)
    llm(triage_json("account"))
    r = bot.handle(conv, "what plan am I on?")
    assert r.route == "escalated" and r.ticket_id
    t = handoff.queue()[-1]
    assert t["context"]["account"] == "account tools disabled (FAQ-only mode)"
    assert t["transcript"][0]["content"] == "how do I export my data?"
    r = bot.handle(conv, "refund me now")             # hard rule, no model call
    assert r.route == "escalated" and handoff.queue()[0]["reason"] == "hard rule: refund or chargeback"
    s = metrics.summary()
    assert s["conversations"] == 1 and s["escalation_rate"] == 1.0


def test_api_auth_chat_feedback_agent(llm, monkeypatch):
    c = TestClient(api.app)
    assert c.post("/chat", json={"message": "hi"}).status_code == 422          # no header
    assert c.post("/chat", json={"message": "hi"}, headers={"Authorization": "Bearer cus_001.bad"}).status_code == 401
    auth = {"Authorization": f"Bearer {session.issue('cus_001')}"}
    r = c.post("/chat", json={"message": "please cancel my account"}, headers=auth).json()
    assert r["route"] == "escalated" and r["ticket_id"]
    assert c.post("/feedback", json={"turn_id": r["turn_id"], "helpful": True}, headers=auth).json() == {"ok": True}
    assert c.get("/agent/tickets").status_code == 422
    agent = {"Authorization": f"Bearer {api.AGENT_TOKEN}"}
    assert c.get("/agent/tickets", headers=auth).status_code == 401
    assert len(c.get("/agent/tickets", headers=agent).json()) == 1
    assert c.post(f"/agent/tickets/{r['ticket_id']}/close", headers=agent).json() == {"ok": True}
    assert c.get("/agent/tickets", headers=agent).json() == []
    assert c.get("/agent/metrics", headers=agent).json()["csat"] == 1.0
    assert "session token" in c.get("/").text
