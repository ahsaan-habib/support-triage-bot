"""Triage and a cited answer from a real local model. Opt-in:

    RUN_OLLAMA=1 pytest tests/test_smoke_ollama.py -s
"""
import functools
import os

import pytest

from support import kb, knowledge, triage

pytestmark = pytest.mark.skipif(os.environ.get("RUN_OLLAMA") != "1", reason="set RUN_OLLAMA=1 to run")


def test_triage_routes_a_howto_to_knowledge():
    t = triage.classify("How do I connect my Google calendar?")
    print("\n", t)
    assert t.route == "knowledge"


def test_cited_answer_or_honest_refusal(indexed, monkeypatch):
    # the tests index with a bag-of-words stand-in for bge-small, which scores lower
    monkeypatch.setattr(kb, "search", functools.partial(kb.search, min_score=0.3))
    a = knowledge.answer("Are annual plans refunded within 14 days of purchase?")
    print("\n", a)
    assert a.covered and a.citations == ["billing.md › Refund policy"] and "14 days" in a.text
    off = knowledge.answer("Do you offer a discount for veterinary clinics in Peru?")
    print(" off-topic:", off)
    assert not off.covered
