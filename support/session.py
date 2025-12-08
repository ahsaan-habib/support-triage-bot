"""Who is this customer? Decided by your app, not by the chat.

Your backend issues a signed token for the logged-in customer and the widget
sends it. The bot trusts nothing the customer types about who they are.
"""
from __future__ import annotations

import hashlib
import hmac
import os

SECRET = os.environ.get("SUPPORT_SECRET", "dev-only-change-me").encode()


def issue(customer_id: str) -> str:
    sig = hmac.new(SECRET, customer_id.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{customer_id}.{sig}"


def verify(token: str) -> str | None:
    customer_id, _, sig = token.rpartition(".")
    if not customer_id:
        return None
    expected = hmac.new(SECRET, customer_id.encode(), hashlib.sha256).hexdigest()[:32]
    return customer_id if hmac.compare_digest(sig, expected) else None


if __name__ == "__main__":
    import sys

    print(issue(sys.argv[1]))
