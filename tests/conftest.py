"""Offline by default: fake embedder, temp index and sqlite, and the model
replaced by a script of replies. test_smoke_ollama.py is opt-in."""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
_tmp = tempfile.mkdtemp(prefix="support-test-")
os.environ.setdefault("SUPPORT_INDEX_DIR", os.path.join(_tmp, "chroma"))
os.environ.setdefault("SUPPORT_DOCS_DIR", str(Path(__file__).resolve().parents[1] / "help_docs"))

import fake_st  # noqa: E402

fake_st.install()

import pytest  # noqa: E402

from support import config  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB", str(tmp_path / "support.db"))


@pytest.fixture(scope="session")
def indexed():
    from support import kb

    return kb.index()


class ScriptedLLM:
    """Replaces support.llm.chat. Each reply is a str (content) or a dict (message)."""

    def __init__(self, *replies):
        self.replies, self.calls = list(replies), []

    def __call__(self, messages, fmt=None, tools=None, temperature=0.0):
        self.calls.append({"messages": messages, "fmt": fmt, "tools": tools})
        r = self.replies.pop(0)
        return {"role": "assistant", "content": r} if isinstance(r, str) else r


def triage_json(route, sentiment="calm"):
    return json.dumps({"route": route, "intent": "x", "sentiment": sentiment, "reason": "because"})


@pytest.fixture
def llm(monkeypatch):
    def install(*replies):
        fake = ScriptedLLM(*replies)
        monkeypatch.setattr("support.llm.chat", fake)
        return fake
    return install
