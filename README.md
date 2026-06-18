# CPNP - Crawl Policy Negotiation Protocol for automated web craewlers

A working prototype of a protocol that lets web crawlers and servers **negotiate**
and **cryptographically enforce** data-access agreements before crawling begins —
a verifiable, auditable replacement for the advisory-only robots.txt.

> Bernard Kipkirui Cheress · Department of ICT, JKUAT · Msc Research Prototype

---

## Start here

| I want to... | Read this | Or run this |
|--------------|-----------|-------------|
| Understand & test everything | **TESTING_GUIDE.md** | — |
| Run the live demo dashboard | USER_GUIDE.md | `uvicorn app.server:app --port 8000` then open `/dashboard` |
| Reproduce all measured numbers | HOW_TO_PRODUCE_REAL_NUMBERS.md | `python3 produce_results.py` |
| Demo the negotiation round bound | HOW_TO_DEMO_NEGOTIATION.md | `python3 CPNP_negotiation_demo.py` |
| Run the real-website audit | audit/RUNBOOK.md | `python3 audit/robots_audit.py` |
| Host it online for free | TESTING_GUIDE.md section 4 | push to GitHub + Render |

---

## 30-second start

```bash
pip install -r requirements.txt
python3 produce_results.py                       # all measured results
uvicorn app.server:app --reload --port 8000      # live server
# open http://localhost:8000/dashboard
```

---

## What's in here

```
cpnp/
├── app/                      The protocol implementation
│   ├── identity/             Ed25519 keys, DIDs, Verifiable Credentials
│   ├── enforcement/          JWT tokens, middleware, audit log, test website
│   ├── negotiation.py        Bilateral negotiation engine
│   ├── server.py             FastAPI server (all endpoints)
│   └── dashboard.py          Live monitoring dashboard
├── benchmarks/               The five evaluation experiments
├── audit/                    The 50-website robots.txt audit
├── results/                  Measured output data (CSV + JSON)
├── produce_results.py        Run ALL experiments in one command
├── CPNP_negotiation_demo.py  Standalone round-bound demo (no deps)
├── TESTING_GUIDE.md          <- complete testing documentation
├── USER_GUIDE.md       Live demo walk-through script
├── Dockerfile, render.yaml   Deployment configs
└── requirements.txt
```

---

## The three layers

1. **Identity** — every crawler holds an Ed25519 keypair; its identity is a
   W3C DID derived from its public key. A trusted authority issues Verifiable
   Credentials. Identity cannot be forged.

2. **Negotiation** — crawler and server bargain over crawl rate, URL scope, and
   purpose using a bounded alternating-offers protocol. Converges in ~2–3 rounds.

3. **Enforcement** — agreement produces an EdDSA-signed JWT. The server verifies
   it on every request and blocks violations with HTTP 451. Every decision is
   logged to an audit trail.

---

## Headline measured results

| Metric | Measured | Method |
|--------|----------|--------|
| Handshake latency | ~0.6 ms mean | 1,000 timed iterations |
| Adversarial detection | 100% (0 false positives) | 1,400 trials, 14 attack types |
| Negotiation convergence | ~2-3 rounds, 95% within 3 | 5,000 scenarios |
| Throughput | ~1,600 handshakes/s/core | saturation test |
| Policy expressiveness | CPNP 14/14 vs robots.txt 1 native | 14-dimension comparison |

Reproduce them all: `python3 produce_results.py`

---

## License & citation

Research prototype for academic evaluation. If referencing this work, cite the
associated thesis/manuscript by Bernard Kipkirui Cheress, JKUAT.
