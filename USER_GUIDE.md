# CPNP User Demo Guide
### How to play user, break things deliberately, and explain what happens

---

## Setup checklist

```bash
cd cpnp
pip install fastapi uvicorn pydantic cryptography httpx
uvicorn app.server:app --reload --port 8000
# Open http://localhost:8000/dashboard in your browser
```

Keep the terminal visible — you'll see requests logged in real time.

---

## Part 1 — The baseline (5 minutes)

**What to show first:** The system is live. Point to the dashboard.

Explain the three panels on the left:
- **Server Identity** — the server's cryptographic DID (like a passport number). It never changes during the session.
- **Server Policy** — what this server is willing to allow: which crawler types, what rate, which paths.
- **Active Sessions** — negotiations in progress or completed.

**Action:** Click **✅ Compliant Crawl (blog)** in Demo Controls.

Watch the audit log table: a green `COMPLIANT` row appears with the crawler's DID, the path it crawled, and its declared purpose. The stats counter increments.

**Say:** *"This crawler negotiated access, received a signed JWT token, and presented it correctly. The server verified the token cryptographically and served the page. The audit log records this permanently."*

---

## Part 2 — Break it: no token (2 minutes)

**Action:** Click **❌ No Token**.

A red `BLOCKED_NO_TOKEN` row appears. Status 451.

**Say:** *"This is what happens when a crawler tries to crawl without going through the protocol — like the current state of the web with any bot that ignores robots.txt. CPNP blocks it at the server before a single byte of content is served, and logs it with a timestamp."*

**Optional:** Visit `http://localhost:8000/site/blog` directly in your browser (no token in the browser). You'll see the raw JSON 451 response with a `how_to_fix` field telling the crawler where to negotiate.

---

## Part 3 — Break it: forged token (2 minutes)

**Action:** Click **❌ Forged JWT**.

A red `BLOCKED_FORGED` row appears. Status 451.

**Say:** *"This crawler generated a fake token — it claimed to have permission but didn't go through the negotiation. The server rejects it because the Ed25519 signature verification fails. You cannot forge a token without the server's private key. This is the key improvement over robots.txt: compliance is cryptographically enforced, not advisory."*

---

## Part 4 — Break it: path violation (2 minutes)

**Action:** Click **❌ Path Violation (/admin)**.

A red `BLOCKED_PATH_VIOLATION` row appears.

**Say:** *"This crawler has a valid token — it negotiated access correctly — but it's trying to access `/admin`, which was not in its agreed scope. The token's agreed_paths list is checked on every request. Even a compliant crawler cannot exceed what it agreed to."*

---

## Part 5 — Break it: adversarial burst (3 minutes)

**Action:** Click **💥 Adversarial Burst (5 attacks)**.

Five blocked rows appear rapidly. The compliance rate drops visibly.

**Say:** *"Five different attack patterns in sequence. Look at the compliance rate — it just dropped. Now go to `http://localhost:8000/audit/blocked` and you can see every blocked request with its reason, the crawler's identifier, and a timestamp. If this were a real system, a regulator could use this audit trail as evidence."*

---

## Part 6 — Change the policy live (5 minutes — most impressive part)

**This is the demo moment.** No other crawl governance tool can do this.

**Action 1 — Block all crawlers:**

In the Change Policy panel:
1. In "Allowed Purposes", deselect everything (hold Ctrl, click to deselect)
2. Click **⚡ Apply Policy Changes**

Now click **✅ Compliant Crawl (blog)** — it still logs COMPLIANT because the crawler already has a valid token. **Explain:** *"Existing tokens are honoured. Only new negotiations use the updated policy. This models how a real server would phase out access."*

**Action 2 — Lower the rate limit:**

1. Drag the Max Crawl Rate slider down to 5
2. Click **⚡ Apply Policy Changes**

Watch the Policy panel update instantly — no server restart. **Say:** *"A publisher can tighten access policy in real time in response to detected abuse. The next crawler to negotiate will receive a maximum rate of 5 req/min."*

**Action 3 — Remove credential requirement:**

1. Uncheck "Require Verifiable Credential"
2. Click **⚡ Apply Policy Changes**

The badge changes from "VC REQUIRED" to "OPEN". **Say:** *"The credential requirement is configurable. A public search indexer might not require credentials. A research database might require an institutional VC. This is the policy expressiveness that robots.txt can never achieve."*

**Action 4 — Restore defaults:**

1. Drag rate back to 30
2. Reselect ResearchCrawler, SearchIndexer, ArchiveCrawler in purposes
3. Set paths back to `/,/blog,/docs,/research`
4. Re-check credential requirement
5. Click **⚡ Apply Policy Changes**

---

## Part 7 — The audit trail (3 minutes)

Open these URLs for the user to inspect:

```
http://localhost:8000/audit/summary
http://localhost:8000/audit/blocked
http://localhost:8000/audit/sql-queries
```

**Say:** *"Every crawl request — compliant and blocked — is permanently logged in a SQLite database with timestamp, crawler DID, URL, verdict, and reason. The SQL queries endpoint gives you 10 ready-to-run queries. Open the database file `cpnp_audit.db` in DB Browser for SQLite and you can run any of these directly."*

Show the per-crawler compliance report: `http://localhost:8000/audit/crawler/did:key:demo-compliant-crawler`

---

## Questions your user is likely to ask

**"How is this different from just blocking crawlers by IP?"**
*IP blocking is trivially circumvented and provides no evidence trail. CPNP blocks by cryptographic identity — a crawler's DID is tied to its private key, which it cannot share without losing control of its identity. Every block is logged with the specific reason.*

**"Who runs the Credential Authority in production?"**
*In this MVP, a mock CA runs on the same server. In production, it would be an institutional accreditation body — a university for research crawlers, a web-standards body for commercial indexers, analogous to the CA/Browser Forum for TLS certificates.*

**"What stops a crawler from just ignoring CPNP?"**
*The same thing that stops a crawler from ignoring robots.txt: nothing, technically. The difference is that CPNP provides an audit trail of who violated what, when. Combined with legal frameworks like the EU AI Act (Articles 10–11), this audit trail becomes evidence for enforcement. The goal is not perfect prevention but attributable, documented access.*

**"Is this ready for standardisation?"**
*The next step is an IETF Internet-Draft, analogous to the path robots.txt took from informal convention to RFC 9309. The formal specification in the thesis is the foundation for that submission.*

---

## If something breaks

| Problem | Fix |
|---------|-----|
| Server won't start — `pydantic` error | `pip install pydantic==2.6.4 --break-system-packages` |
| Server won't start — `cryptography` error | `pip install cryptography --break-system-packages` |
| Dashboard shows "OFFLINE" | Check the terminal — server may have crashed. Restart it. |
| All requests showing BLOCKED | Check policy panel — purposes may have been cleared. Click Apply with ResearchCrawler selected. |
| Audit log empty | Click any demo crawl button — events only appear after traffic. |
| Port 8000 in use | `uvicorn app.server:app --reload --port 8001` then update NEGOTIATE_URL in middleware.py |
