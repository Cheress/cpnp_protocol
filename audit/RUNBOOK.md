# CPNP Empirical robots.txt Audit — Runbook

## What this experiment proves

It empirically measures the **expressiveness gap** that CPNP fills, using 50
real websites' actual `robots.txt` files. The finding — that real-world
`robots.txt` files can express only a small fraction of the 14 governance
dimensions CPNP supports.

---

## What you can honestly claim from it

- "Across 50 real `robots.txt` files audited on [date], the mean number of the
  14 CPNP governance dimensions even partially expressible was X.X / 14."
- "CPNP expresses all 14 dimensions; the dominant real-world mechanism expresses
  primarily path restriction (D1), with rate-limiting and AI-bot blocking used
  by a minority of sites."
- "N of 50 sites attempt to block AI-training crawlers by name, but this relies
  on voluntary user-agent honesty and is unenforceable — the exact weakness CPNP
  addresses cryptographically."

What you must NOT claim:
- That any site negotiated with CPNP.
- That the numbers are anything other than a point-in-time snapshot (robots.txt
  changes; always cite the access date).

---

## Step-by-step process

### Step 1 — Prepare your machine (not the sandbox)
This experiment needs internet access. Run it on your own laptop/PC.

```bash
cd cpnp
pip install requests
```

### Step 2 — Review the sample
```bash
python audit/website_list.py
```
This prints the 50 sites grouped by stratum. Confirm they're reachable from
your location. If any are blocked in Kenya, note it — that itself is a finding
(jurisdiction-specific access, dimension D13).

### Step 3 — Run the audit
```bash
python audit/robots_audit.py
```
It fetches each site's `robots.txt`, saves a copy, analyses it against the 14
dimensions, and writes results. Takes ~2 minutes (there's a polite 0.5s delay
between sites). You'll see live progress per site.

### Step 4 — Inspect the outputs
All in `audit/results/`:

| File | Use in thesis |
|------|---------------|
| `audit_per_site.csv` | Appendix table — every site's measured features |
| `audit_per_dimension.csv` | Main results table — the 14-dimension gap |
| `audit_per_stratum.csv` | Per-category analysis — is the gap universal? |
| `audit_summary.json` | Headline numbers for the abstract |
| `robots_raw/*.txt` | Evidence — the actual files you analysed |

### Step 5 — Re-run for reproducibility
Run it a second time a week later. If results differ, that demonstrates
robots.txt volatility — another argument for CPNP's stable, negotiated
agreements. Cite both access dates.

---

## How to write it up (Methodology Section 3.6)

> "To empirically establish the expressiveness limitations of the incumbent
> Robots Exclusion Protocol, a stratified purposive sample of 50 high-traffic
> websites was assembled across six sectors (news, academic, e-commerce, social,
> reference, and government). Each site's `robots.txt` was retrieved from its
> well-known location and parsed to determine which of 14 crawl-governance
> dimensions it could express. The dimensions were derived from [your taxonomy
> section]. Expressiveness was classified as native, partial, or not-expressible
> per dimension. The same 14 dimensions were then assessed against the CPNP
> Policy Manifest. Audit was conducted on [DATE]; raw files are archived in the
> replication package."

---

## Ethics note (include in thesis)

Fetching `robots.txt` is explicitly sanctioned by RFC 9309 — it is the public
mechanism the web provides for crawlers to read crawl policy. No site *content*
was accessed; only the public policy file. Requests used a transparent academic
user-agent string identifying the research and institution. A 0.5-second
inter-request delay was applied as a courtesy. This audit imposes negligible
load (one small file per site).

---

## Limitations to state honestly

1. **Point-in-time snapshot** — robots.txt changes; results are dated.
2. **Sample is purposive, not random** — chosen for sector coverage, so
   proportions don't generalise to the whole web (state this explicitly).
3. **Partial-expressibility is generous to robots.txt** — counting crawl-delay
   and AI-bot blocks as "partial" gives robots.txt the benefit of the doubt;
   the true enforceable gap is even wider, since none of these are cryptographically
   enforced.
4. **n=50** — adequate for a focused audit; Longpre et al. (2024) used thousands.
   Frame yours as a focused, sector-stratified complement, not a census.
