# support-triage-bot

Blueprint 1 from *Designing AI Automation for Your Business*: intelligent
customer support. Local model (`qwen3:4b-instruct` via Ollama), local embeddings,
everything open source.

```
customer message
      │
   TRIAGE  ── hard rules first (refunds, chargebacks, legal, deletion, security) ──▶ human
      │      then the model: route + intent + sentiment (angry ──▶ human)
      ├── knowledge ─▶ help-centre RAG ─▶ cited answer   │ not covered ─▶ human
      ├── account   ─▶ tools bound to the session customer ─▶ answer from tool facts
      └── escalate  ─▶ ticket with transcript + everything gathered so far
```

The triage step never answers. Its whole job is routing, so the expensive and
risky paths only run when they should.

## Design decisions

- **Start narrow.** `SUPPORT_FAQ_ONLY=1` (default) answers only from the help
  centre and escalates everything else, account questions included. Turn
  account tools on once deflection and satisfaction justify it.
- **No invented policy.** Knowledge answers must cite help articles; no
  citation or `NOT_COVERED` → human. A bot that confidently invents a refund
  policy costs more than it saves.
- **Identity is enforced in code.** The customer comes from an HMAC-signed
  session token issued by your app. Account tools are bound to that customer
  with `functools.partial`; the model's tool schemas have no customer id
  parameter, so no prompt can widen the scope. The bot is read-only: no
  refunds, plan changes or cancellations.
- **Money, law and deletion always go to a person**, by regex before the
  model — cheap to recognise, expensive to misroute. So do angry customers.
- **Handoff carries context.** Tickets store the transcript, the triage
  result, the docs that were tried and any account facts fetched, so nobody
  asks the customer to repeat themselves.

## Metrics

`GET /agent/metrics` → conversations, deflection rate (no turn escalated),
escalation rate, not-covered refusals (counted as correct behaviour, not
failures), and CSAT from 👍/👎 on bot answers.

## Run it

```bash
ollama pull qwen3:4b-instruct   # not plain qwen3:4b: that tag is now a thinking-only build
make install && source .venv/bin/activate
make index                 # help_docs/ -> chroma
make serve                 # widget at http://localhost:8020
make token C=cus_001       # paste into the widget
```

`help_docs/` and `data/accounts.json` are invented sample data for a fictional
product. Replace them with your help centre and point `support/account.py` at
your real billing API.
