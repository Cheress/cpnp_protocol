# CPNP — Complete Testing & Verification Guide

This document explains how to run, test, and verify **every** component of the
Crawl Policy Negotiation Protocol (CPNP) prototype. It is written so that anyone can reproduce every result.

---

## Table of contents

1. [What CPNP is](#1-what-cpnp-is)
2. [Quick start (5 minutes)](#2-quick-start)
3. [Running the live server + dashboard](#3-live-server)
4. [Hosting it online (free)](#4-hosting)
5. [Testing each layer](#5-testing-each-layer)
6. [Reproducing every measured result](#6-reproducing-results)
7. [The empirical website audit](#7-website-audit)
8. [What each number means](#8-interpreting-results)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. What CPNP is

CPNP is a proposed protocol that lets automated web crawlers and servers **negotiate** and
**cryptographically enforce** data-access agreements before crawling begins.
It replaces the advisory-only robots.txt with a signed, auditable handshake.

The prototype has three layers:
- **Identity** — Ed25519 keypairs, W3C DIDs, Verifiable Credentials
- **Negotiation** — bilateral rate/scope/purpose bargaining
- **Enforcement** — signed JWT tokens checked on every request, with audit logging

---

## 2. Quick start

You need **Python 3.11+**. Then:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run all measured experiments (no server needed) — ~30 seconds
python3 produce_results.py

# 3. Start the live server
uvicorn app.server:app --reload --port 8000

# 4. Open the dashboard
#    http://localhost:8000/dashboard
```

That's it. Everything below is detail on each piece.

---

## 3. Live server

### Start it
```bash
uvicorn app.server:app --host 0.0.0.0 --port 8000
```

### URLs to open

| URL | What it shows |
|-----|---------------|
| `http://localhost:8000/dashboard` | Live monitoring dashboard (the demo UI) |
| `http://localhost:8000/docs` | Interactive API explorer — try every endpoint |
| `http://localhost:8000/site/` | The test website CPNP protects |
| `http://localhost:8000/cpnp/policy` | The server's current policy (JSON) |
| `http://localhost:8000/audit/summary` | Compliance statistics |
| `http://localhost:8000/health` | Health check (returns `{"status":"ok"}`) |

### Demo the protocol from the dashboard
The dashboard has buttons that fire crawl events live:
- **Compliant Crawl** → green COMPLIANT row appears
- **No Token / Forged JWT / Path Violation** → red BLOCKED rows
- **Adversarial Burst** → 5 attacks in sequence
- **Change Policy** → tighten the rate limit live, no restart

See `USER_GUIDE.md` for a full walk-through script.

---

## 4. Hosting (free, public URL)

### Option A — Render.com (easiest, recommended)
1. Push the `cpnp/` folder to a GitHub repo.
2. Go to [render.com](https://render.com) → **New** → **Blueprint**.
3. Connect your repo. Render reads `render.yaml` and deploys automatically.
4. You get a public URL like `https://cpnp-server.onrender.com`.
5. Share `https://your-url.onrender.com/dashboard` with your supervisor.

Free tier sleeps after 15 min idle, wakes in ~30s. Fine for demos.

### Option B — Docker (any host)
```bash
docker build -t cpnp .
docker run -p 8000:8000 cpnp
# open http://localhost:8000/dashboard
```
This image runs on Fly.io, Railway, Google Cloud Run, AWS, Azure — anywhere
that runs containers.

### Option C — Railway
1. Push to GitHub.
2. [railway.app](https://railway.app) → New Project → Deploy from GitHub.
3. Railway reads the `Procfile` and deploys. Public URL provided.

### Option D — Hugging Face Spaces (free, no card)
1. Create a Space → Docker SDK.
2. Push the repo. The `Dockerfile` builds it.
3. URL: `https://your-name-cpnp.hf.space/dashboard`

---

## 5. Testing each layer

### 5.1 Identity layer (Ed25519, DIDs, Credentials)
```bash
python3 -c "
import sys; sys.path.insert(0,'.')
from app.identity.keys import generate_keypair

# Generate a real Ed25519 keypair + DID
kp = generate_keypair('test-crawler')
print('DID:', kp.did)

# Sign and verify
msg = b'hello cpnp'
sig = kp.sign(msg)
print('Valid signature:', kp.verify(msg, sig))

# Tampering is detected
print('Tampered detected:', not kp.verify(b'hello cpnX', sig))
"
```
Expected: a `did:key:z6Mk...` identifier, `Valid signature: True`,
`Tampered detected: True`.

### 5.2 Cryptographic verifiability demonstration
```bash
python3 -c "
import sys; sys.path.insert(0,'.')
from app.identity.keys import generate_keypair
crawler = generate_keypair('crawler')
attacker = generate_keypair('attacker')
msg = b'{\"rate\":20}'
sig = crawler.sign(msg)
print('1. Crawler signs, server verifies:', crawler.verify(msg, sig))
print('2. Tampered (rate changed) rejected:', not crawler.verify(b'{\"rate\":9999}', sig))
print('3. Attacker forgery rejected:', not crawler.verify(msg, attacker.sign(msg)))
"
```
Expected: all three lines `True` — proving the cryptographic claims.

### 5.3 Negotiation round bound (the "why N rounds?" demonstration)
```bash
python3 CPNP_negotiation_demo.py
```
Self-contained, needs only Python. Shows the formula, runs 5,000 negotiations,
prints the measured round distribution, and proves it's reproducible (run twice,
identical numbers). See `HOW_TO_DEMO_NEGOTIATION.md`.

### 5.4 Full handshake over HTTP (with the server running)
In one terminal start the server, then in another:
```bash
# Fetch the policy
curl http://localhost:8000/cpnp/policy

# Try to crawl without a token → blocked with HTTP 451
curl -i http://localhost:8000/site/blog
```
Expected: the policy as JSON, then a `451` response with a `CPNP-Verdict:
BLOCKED_NO_TOKEN` header.

---

## 6. Reproducing every measured result

### Run everything at once

```bash
python3 produce_results.py --iterations 2000 --trials 200 --scenarios 10000 --duration 10
```

### Or run each experiment individually
```bash
python3 benchmarks/benchmark.py --iterations 1000 --warmup 100   # latency
python3 benchmarks/security_eval.py --trials 100                 # security
python3 benchmarks/convergence_eval.py --scenarios 5000          # round bound
python3 benchmarks/throughput_eval.py --duration 5              # throughput
python3 benchmarks/expressiveness_eval.py                       # expressiveness
python3 benchmarks/run_all.py                                   # all + summary
```

### What you get

| Experiment | Measures | Output file |
|------------|----------|-------------|
| `benchmark.py` | Per-operation + end-to-end latency | `results/summary_statistics.csv` |
| `security_eval.py` | Adversarial detection over 1,400 trials | `results/confusion_matrix.json` |
| `convergence_eval.py` | Negotiation rounds distribution | `results/convergence_summary.json` |
| `throughput_eval.py` | Operations per second | `results/throughput_results.csv` |
| `expressiveness_eval.py` | robots.txt vs CPNP policy gap | `results/expressiveness_results.csv` |

---

## 7. Website audit (empirical robots.txt study)

This is the only test that needs **internet access** — run it on your own
machine, not a sandbox.

```bash
pip install requests
python3 audit/robots_audit.py
```

It fetches the real robots.txt from 50 websites, measures which of the 14 CPNP
governance dimensions each can express, and saves everything. See
`audit/RUNBOOK.md` for full detail and the site list.

Outputs in `audit/results/`:
- `audit_per_site.csv`, `audit_per_dimension.csv`, `audit_per_stratum.csv`
- `audit_summary.json`
- `robots_raw/*.txt` (the actual files, as evidence)

---

## 8. Interpreting results

| Measured value (typical) | Meaning |
|--------------------------|---------|
| Handshake ~0.6 ms mean | The full cryptographic + negotiation handshake is sub-millisecond. Real-world latency is dominated by network, not CPNP. |
| Detection 100%, 0 false positives (1,400 trials) | Every forged/expired/tampered/spoofed request is rejected; no legitimate request is wrongly blocked. |
| Mean ~2–3 negotiation rounds; ~95% within 3 | Negotiations converge quickly; the round bound is sufficient. |
| ~1,600 handshakes/sec/core | One core sustains heavy load; scales horizontally. |
| CPNP 14/14 vs robots.txt 1 native | CPNP expresses governance intents robots.txt structurally cannot. |

---

## 9. Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: fastapi` | `pip install -r requirements.txt` |
| `cryptography` build error | `pip install --upgrade pip` then retry; or use the Docker image |
| Port 8000 in use | `uvicorn app.server:app --port 8001` |
| Dashboard shows OFFLINE | Server crashed — check the terminal, restart it |
| Audit tool fails to fetch | Needs internet; some sites may rate-limit — the tool records failures and continues |
| Results differ slightly between runs | Expected for latency/throughput (machine load). Negotiation uses a fixed seed and is identical every run. |

---

## Reproducibility statement 

All experiments are deterministic where it matters: the negotiation analysis
uses a fixed random seed (42) and produces identical results on every run.
Latency and throughput vary marginally with machine load, so distributions
(mean, median, p95, p99) are reported rather than single values. Every script
records its parameters and environment. The complete source, experiments, and
raw outputs are in this repository, enabling independent verification.
