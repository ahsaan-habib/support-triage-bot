"""Knowledge questions: answer only from the help centre, cite every answer,
refuse when the docs don't cover it. A support bot that confidently invents a
refund policy costs more than it ever saves."""
from __future__ import annotations

from dataclasses import dataclass, field

from . import kb, llm

NOT_COVERED = "NOT_COVERED"

SYSTEM = f"""You are Flowdesk's support assistant. Answer the customer using ONLY
the numbered help articles. Cite the article numbers you used like [1].
Be brief and friendly: two to four sentences.
Never state a policy, price, limit or timeframe that is not written in the
articles. If the articles don't answer the question, reply exactly {NOT_COVERED}."""


@dataclass
class KnowledgeAnswer:
    text: str
    citations: list[str] = field(default_factory=list)
    covered: bool = True


def answer(question: str, history: list[dict] | None = None) -> KnowledgeAnswer:
    articles = kb.search(question)
    if not articles:
        return KnowledgeAnswer("", covered=False)
    context = "\n\n".join(f"[{i}] {a.cite}\n{a.text}" for i, a in enumerate(articles, 1))
    msg = llm.chat([{"role": "system", "content": SYSTEM}, *(history or [])[-4:],
                    {"role": "user", "content": f"Help articles:\n{context}\n\nCustomer: {question}"}])
    text = msg["content"].strip()
    if NOT_COVERED in text:
        return KnowledgeAnswer("", covered=False)
    used = [a.cite for i, a in enumerate(articles, 1) if f"[{i}]" in text]
    if not used:
        # an answer with no citation is an answer we can't stand behind
        return KnowledgeAnswer("", covered=False)
    return KnowledgeAnswer(text, used)
