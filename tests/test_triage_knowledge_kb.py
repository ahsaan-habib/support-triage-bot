import functools

import pytest

from conftest import triage_json
from support import kb, knowledge, session, triage


@pytest.mark.parametrize("msg,why", [
    ("I want my money back for last month", "refund or chargeback"),
    ("I'll take legal action if this isn't fixed", "legal / data rights"),
    ("please delete my account", "account deletion or cancellation"),
    ("I think someone else logged in to my workspace", "possible security incident"),
])
def test_hard_rules_beat_the_model(msg, why, llm):
    fake = llm()
    t = triage.classify(msg)
    assert t.route == "escalate" and t.reason == f"hard rule: {why}" and fake.calls == []


def test_model_triage_valid_invalid_angry(llm):
    fake = llm(triage_json("knowledge"), "garbage", triage_json("knowledge", "angry"))
    assert triage.classify("how do I export my data?").route == "knowledge"
    assert fake.calls[0]["fmt"]["properties"]["route"]["enum"] == ["knowledge", "account", "escalate"]
    assert triage.classify("??").reason == "triage output invalid"
    angry = triage.classify("THIS IS THE THIRD TIME")
    assert angry.route == "escalate" and angry.reason.startswith("angry customer")


# min_score is tuned for bge-small; the fake bag-of-words embedder scores lower
FAKE_MIN = 0.3


def test_index_and_search_help_centre(indexed):
    assert indexed >= 15
    hits = kb.search("annual plans refunded within 14 days of purchase", min_score=FAKE_MIN)
    assert hits and hits[0].cite == "billing.md › Refund policy"
    assert kb.search("qwertyuiop zxcvbnm", min_score=FAKE_MIN) == []


def test_knowledge_answer_needs_a_citation(indexed, llm, monkeypatch):
    monkeypatch.setattr(kb, "search", functools.partial(kb.search, min_score=FAKE_MIN))
    q = "are annual plans refunded within 14 days of purchase?"
    llm("Annual plans can be refunded in full within 14 days [1].")
    a = knowledge.answer(q)
    assert a.covered and a.citations == ["billing.md › Refund policy"]
    llm("Sure, refunds are always available.")
    assert not knowledge.answer(q).covered
    llm("NOT_COVERED")
    assert not knowledge.answer(q).covered
    assert not knowledge.answer("qwertyuiop zxcvbnm").covered      # nothing retrieved, no model call


def test_session_tokens():
    tok = session.issue("cus_001")
    assert session.verify(tok) == "cus_001"
    assert session.verify(tok.replace("cus_001", "cus_002")) is None
    assert session.verify("nodot") is None and session.verify("") is None
