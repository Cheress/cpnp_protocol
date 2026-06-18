## Script 1 — `produce_results.py` (the crypto/negotiation/security numbers)

Runs five experiments in one command and prints a claim-vs-measured table.
Needs only the `cryptography` library. 

```bash
pip install cryptography
python3 produce_results.py
```

For larger/more rigorous runs :
```bash
python3 produce_results.py --iterations 2000 --trials 200 --scenarios 10000 --duration 10
```


Outputs: `results/mvp_measured_results.json` and `.csv`.

---

## Script 2 — `audit/robots_audit.py` (the real-website numbers)

Fetches the actual robots.txt from 50 real websites and measures the
expressiveness gap empirically. **Needs internet — run on your own machine,
NOT in a sandbox.**

```bash
pip install requests
python3 audit/robots_audit.py
```

Outputs in `audit/results/`:
- `audit_per_site.csv` — every site's measured features
- `audit_per_dimension.csv` — the 14-dimension gap, measured
- `audit_per_stratum.csv` — gap broken down by sector
- `audit_summary.json` — headline numbers
- `robots_raw/*.txt` — the actual files (your evidence)

---



If you want the sample to be 100, expand `audit/website_list.py` to 100 sites
FIRST, run the audit, THEN report 100. 

---

## Order of operations

1. Run `produce_results.py` on any machine → get the crypto/negotiation/security numbers.
2. Run `audit/robots_audit.py` on a networked machine → get the real website numbers.
3. Open the manuscript and replace each fabricated figure with its measured
   counterpart, using `results/mvp_measured_results.csv` and
   `audit/results/audit_summary.json` as the source of truth.

