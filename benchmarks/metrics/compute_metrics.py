#!/usr/bin/env python3
"""
benchmark_crawlers/metrics/compute_metrics.py
═══════════════════════════════════════════════
Computes the three benchmark metrics from the server request log.

METRIC DEFINITIONS (state these precisely in the thesis):

  COVERAGE = (allowed pages fetched) / (total allowed pages)
    How completely did the crawler retrieve the content it was PERMITTED to take?
    Range [0,1]; higher is better. A good crawler covers all allowed pages.

  POLITENESS = 1 - (violation_ratio), where violation_ratio is the fraction of
    time-windows in which the crawler exceeded the declared rate limit.
    Measures whether the crawler honoured the Crawl-delay / rate ceiling.
    Range [0,1]; higher is better (1.0 = never exceeded the limit).

  POLICY-FIDELITY = 1 - (forbidden pages accessed) / (total forbidden pages)
    Did the crawler respect the robots.txt Disallow rules?
    Range [0,1]; higher is better. 1.0 = never touched a forbidden page.
    Under CPNP enforcement, forbidden fetches are BLOCKED (451), so even a
    non-compliant crawler is forced to fidelity 1.0 — this is the key result.

USAGE:
  python3 compute_metrics.py --label "Scrapy (obey)" --mode robots
  python3 compute_metrics.py --label "Naive"          --mode cpnp

  # After running all crawlers, aggregate:
  python3 compute_metrics.py --report
"""
import argparse, json, os, csv
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "..", "results")
LOG = os.path.join(RESULTS, "server_log.jsonl")
GT = os.path.join(RESULTS, "ground_truth.json")
TABLE = os.path.join(RESULTS, "benchmark_results.csv")


def load_log():
    rows = []
    with open(LOG) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def compute(label, mode):
    gt = json.load(open(GT))
    allowed = set(gt["allowed"])
    forbidden = set(gt["forbidden"])
    rate_limit = gt["rate_limit"]
    rows = load_log()

    # COVERAGE: distinct allowed pages successfully fetched (200)
    allowed_fetched = set(r["path"] for r in rows
                          if r["class"] == "allowed" and r["status"] == 200
                          and r["path"] in allowed)
    coverage = len(allowed_fetched) / len(allowed) if allowed else 0

    # POLICY-FIDELITY: forbidden pages that were successfully ACCESSED (200)
    forbidden_accessed = set(r["path"] for r in rows
                             if r["class"] == "forbidden" and r["status"] == 200
                             and r["path"] in forbidden)
    forbidden_blocked = set(r["path"] for r in rows
                            if r["class"] == "forbidden" and r["status"] == 451)
    fidelity = 1 - (len(forbidden_accessed) / len(forbidden)) if forbidden else 1.0

    # POLITENESS: check request rate per 60s window vs the declared limit
    if rows:
        t0 = min(r["ts"] for r in rows)
        windows = defaultdict(int)
        for r in rows:
            w = int((r["ts"] - t0) // 60)   # 60-second buckets
            windows[w] += 1
        violated = sum(1 for c in windows.values() if c > rate_limit)
        politeness = 1 - (violated / len(windows)) if windows else 1.0
        peak_rate = max(windows.values()) if windows else 0
    else:
        politeness, peak_rate = 1.0, 0

    result = {
        "label": label, "mode": mode,
        "coverage": round(coverage, 3),
        "politeness": round(politeness, 3),
        "policy_fidelity": round(fidelity, 3),
        "allowed_fetched": len(allowed_fetched),
        "allowed_total": len(allowed),
        "forbidden_accessed": len(forbidden_accessed),
        "forbidden_blocked": len(forbidden_blocked),
        "forbidden_total": len(forbidden),
        "peak_req_per_min": peak_rate,
        "rate_limit": rate_limit,
    }

    # Append to the results table
    header = not os.path.exists(TABLE)
    with open(TABLE, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(result.keys()))
        if header:
            w.writeheader()
        w.writerow(result)

    print(f"\n  ── {label}  (server mode: {mode}) ──")
    print(f"     Coverage:        {result['coverage']:.3f}  "
          f"({result['allowed_fetched']}/{result['allowed_total']} allowed pages)")
    print(f"     Politeness:      {result['politeness']:.3f}  "
          f"(peak {result['peak_req_per_min']}/min vs limit {rate_limit})")
    print(f"     Policy-Fidelity: {result['policy_fidelity']:.3f}  "
          f"({result['forbidden_accessed']} accessed, {result['forbidden_blocked']} blocked, "
          f"of {result['forbidden_total']} forbidden)")
    return result


def report():
    if not os.path.exists(TABLE):
        print("No results yet. Run crawlers + compute_metrics.py first.")
        return
    print("\n" + "=" * 78)
    print("  BENCHMARK RESULTS — Crawler Policy Fidelity")
    print("=" * 78)
    rows = list(csv.DictReader(open(TABLE)))
    print(f"\n  {'Crawler':22s} {'Mode':7s} {'Coverage':9s} {'Politeness':11s} {'Fidelity':9s}")
    print(f"  {'-'*22} {'-'*7} {'-'*9} {'-'*11} {'-'*9}")
    for r in rows:
        print(f"  {r['label']:22s} {r['mode']:7s} "
              f"{r['coverage']:>8s} {r['politeness']:>10s} {r['policy_fidelity']:>8s}")
    print(f"\n  Full data: {TABLE}")
    print("\n  KEY OBSERVATION TO DISCUSS:")
    print("  Under 'robots' mode, policy-fidelity depends entirely on the crawler's")
    print("  goodwill. Under 'cpnp' mode, forbidden fetches are blocked (451), forcing")
    print("  fidelity to 1.0 even for a crawler that ignores robots.txt. This is the")
    print("  difference between ADVISORY policy and ENFORCED policy.\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="crawler")
    ap.add_argument("--mode", default="robots")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    if args.report:
        report()
    else:
        compute(args.label, args.mode)


if __name__ == "__main__":
    main()
