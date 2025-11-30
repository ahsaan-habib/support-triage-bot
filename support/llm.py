from __future__ import annotations

import httpx

from . import config


def chat(messages: list[dict], fmt: str | dict | None = None, tools: list[dict] | None = None,
         temperature: float = 0.0) -> dict:
    body = {"model": config.MODEL, "messages": messages, "stream": False, "think": False,
            "options": {"temperature": temperature}}
    if fmt is not None:
        body["format"] = fmt
    if tools:
        body["tools"] = tools
    r = httpx.post(f"{config.OLLAMA_URL}/api/chat", json=body, timeout=120)
    r.raise_for_status()
    return r.json()["message"]
