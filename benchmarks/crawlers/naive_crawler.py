#!/usr/bin/env python3
"""
benchmark_crawlers/crawlers/naive_crawler.py
══════════════════════════════════════════════
The NAIVE BASELINE crawler — the experimental control.

This crawler discovers pages from the index and fetches EVERYTHING it finds,
ignoring robots.txt entirely. It represents the worst case: an unrestricted
crawler that respects no policy. Its results establish the baseline against
which robots.txt-respecting crawlers (Scrapy, Nutch, Heritrix) and CPNP
enforcement are compared.

It also demonstrates the core CPNP thesis directly: run it against the server
in robots mode and it reaches every forbidden page; run it against the server
in CPNP mode and every forbidden fetch is blocked with HTTP 451 — WITHOUT the
crawler changing its behaviour at all. That is enforcement vs. advice.

USAGE:
  python3 naive_crawler.py --base http://localhost:8080 [--token cpnp:/public]

Needs only the Python standard library.
"""
import argparse, time, re, urllib.request, urllib.error

def fetch(url, token=None):
    req = urllib.request.Request(url, headers={"User-Agent": "naive-crawler/1.0"})
    if token:
        req.add_header("CPNP-Token", token)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return None, str(e)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8080")
    ap.add_argument("--token", default=None,
                    help="Optional CPNP token, e.g. cpnp:/public (makes it CPNP-aware)")
    ap.add_argument("--delay", type=float, default=0.0,
                    help="Seconds between requests (naive crawler defaults to 0 = impolite)")
    args = ap.parse_args()

    print(f"Naive crawler starting against {args.base}")
    print(f"  CPNP token: {args.token or 'NONE (not CPNP-aware)'}")
    print(f"  Politeness delay: {args.delay}s\n")

    # 1. Fetch index, discover links
    status, html = fetch(f"{args.base}/", args.token)
    links = re.findall(r'href="([^"]+)"', html)
    print(f"Discovered {len(links)} links from index")

    # 2. Fetch EVERY link, ignoring robots.txt
    fetched = blocked = 0
    for link in links:
        url = args.base + link
        status, _ = fetch(url, args.token)
        if status == 200:
            fetched += 1
        elif status == 451:
            blocked += 1
        if args.delay:
            time.sleep(args.delay)

    print(f"\nNaive crawler done.")
    print(f"  Fetched (200): {fetched}")
    print(f"  Blocked (451): {blocked}")
    print(f"  → See results/server_log.jsonl for the authoritative record.")
    print(f"  → Run metrics/compute_metrics.py to score this run.")

if __name__ == "__main__":
    main()
