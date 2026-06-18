from __future__ import annotations
import sys, os, csv, json, time, re
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from audit.website_list import WEBSITES

# Known AI-training / LLM crawler user-agents (for D6 detection).
# Source: public bot documentation as of 2025.
AI_BOTS = [
    "GPTBot", "ChatGPT-User", "CCBot", "Google-Extended", "anthropic-ai",
    "ClaudeBot", "Claude-Web", "Omgilibot", "FacebookBot", "Applebot-Extended",
    "Bytespider", "PerplexityBot", "Diffbot", "ImagesiftBot", "cohere-ai",
    "Meta-ExternalAgent", "Amazonbot", "YouBot", "Timpibot",
]


DIMENSIONS = [
    ("D1",  "Path restriction",             "native"),
    ("D2",  "Rate limiting",                "partial"),
    ("D3",  "Identity discrimination",      "partial"),
    ("D4",  "Purpose-based access",         "none"),
    ("D5",  "Verifiable operator identity", "none"),
    ("D6",  "Data-use restriction",         "partial"),
    ("D7",  "No commercial resale",         "none"),
    ("D8",  "Temporal access window",       "none"),
    ("D9",  "Bilateral negotiation",        "none"),
    ("D10", "Non-repudiable agreement",     "none"),
    ("D11", "Cryptographic enforcement",    "none"),
    ("D12", "Auditable compliance trail",   "none"),
    ("D13", "Jurisdiction restriction",     "none"),
    ("D14", "Compensation / paid access",   "none"),
]


def fetch_robots(url, timeout=15):
    """Fetches a robots.txt. Returns (status, text, error)."""
    import requests
    headers = {"User-Agent": "CPNP-Research-Audit/1.0 (academic study)"}
    try:
        r = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        return r.status_code, r.text, ""
    except Exception as e:
        return None, "", f"{type(e).__name__}: {e}"


def analyse_robots(text):
    """
    Parses a robots.txt and extracts measured features.
    Returns a dict of observed properties.
    """
    lines = [ln.strip() for ln in text.splitlines()]
    nonblank = [ln for ln in lines if ln and not ln.startswith("#")]

    user_agents = []
    has_crawl_delay = False
    has_sitemap = False
    disallow_count = 0
    allow_count = 0
    ai_bots_named = []

    for ln in nonblank:
        low = ln.lower()
        if low.startswith("user-agent:"):
            ua = ln.split(":", 1)[1].strip()
            user_agents.append(ua)
            for bot in AI_BOTS:
                if bot.lower() == ua.lower():
                    ai_bots_named.append(bot)
        elif low.startswith("crawl-delay:"):
            has_crawl_delay = True
        elif low.startswith("sitemap:"):
            has_sitemap = True
        elif low.startswith("disallow:"):
            disallow_count += 1
        elif low.startswith("allow:"):
            allow_count += 1

    # De-dup AI bots
    ai_bots_named = sorted(set(ai_bots_named))

    return {
        "user_agent_groups": len(set(user_agents)),
        "has_crawl_delay": has_crawl_delay,
        "has_sitemap": has_sitemap,
        "disallow_count": disallow_count,
        "allow_count": allow_count,
        "ai_bots_named": ai_bots_named,
        "ai_bots_count": len(ai_bots_named),
        "total_directives": disallow_count + allow_count,
        "byte_size": len(text.encode("utf-8")),
    }


def expressible_for_site(dim_id, capability, features):
    """
    Decides whether a given dimension is actually expressed/expressible for
    THIS site, based on measured features.

    Returns one of: "expressed", "expressible_unused", "partial", "not_expressible"
    """
    if capability == "native":
        # D1 path restriction — expressed if any disallow/allow present
        if dim_id == "D1":
            return "expressed" if features["total_directives"] > 0 else "expressible_unused"
        return "expressible_unused"

    if capability == "partial":
        if dim_id == "D2":   # rate limiting via crawl-delay
            return "partial" if features["has_crawl_delay"] else "not_expressible"
        if dim_id == "D3":   # identity discrimination via user-agent
            return "partial" if features["user_agent_groups"] > 1 else "not_expressible"
        if dim_id == "D6":   # data-use restriction via AI-bot blocks (approximation)
            return "partial" if features["ai_bots_count"] > 0 else "not_expressible"
        return "not_expressible"

    # capability == "none"  → structurally impossible in robots.txt
    return "not_expressible"


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    outdir = os.path.join(here, "results")
    raw_dir = os.path.join(outdir, "robots_raw")
    os.makedirs(raw_dir, exist_ok=True)

    print(f"\n{'='*72}")
    print(f"  CPNP Empirical robots.txt Audit — {len(WEBSITES)} websites")
    print(f"  Access date: {datetime.now(timezone.utc).isoformat()}")
    print(f"{'='*72}\n")

    per_site = []
    # dimension expressibility counts across all sites
    dim_counts = {d[0]: {"expressed": 0, "expressible_unused": 0,
                          "partial": 0, "not_expressible": 0} for d in DIMENSIONS}

    fetched = failed = 0

    for i, (domain, stratum, url) in enumerate(WEBSITES, 1):
        print(f"  [{i:2d}/{len(WEBSITES)}] {domain:24s} ", end="", flush=True)
        status, text, err = fetch_robots(url)

        if status != 200 or not text:
            failed += 1
            print(f"FAILED ({err or status})")
            per_site.append({"domain": domain, "stratum": stratum, "url": url,
                             "fetch_status": status or "ERROR", "error": err,
                             "user_agent_groups": 0, "has_crawl_delay": False,
                             "has_sitemap": False, "disallow_count": 0,
                             "ai_bots_named": "", "ai_bots_count": 0,
                             "byte_size": 0, "dimensions_expressible": 0})
            continue

        fetched += 1
        # Save raw file
        safe = domain.replace("/", "_")
        with open(os.path.join(raw_dir, f"{safe}.txt"), "w", encoding="utf-8") as f:
            f.write(text)

        features = analyse_robots(text)

        # Evaluate all 14 dimensions for this site
        site_expressible = 0
        for (dim_id, label, cap) in DIMENSIONS:
            verdict = expressible_for_site(dim_id, cap, features)
            dim_counts[dim_id][verdict] += 1
            if verdict in ("expressed", "partial"):
                site_expressible += 1

        per_site.append({
            "domain": domain, "stratum": stratum, "url": url,
            "fetch_status": status, "error": "",
            "user_agent_groups": features["user_agent_groups"],
            "has_crawl_delay": features["has_crawl_delay"],
            "has_sitemap": features["has_sitemap"],
            "disallow_count": features["disallow_count"],
            "ai_bots_named": ";".join(features["ai_bots_named"]),
            "ai_bots_count": features["ai_bots_count"],
            "byte_size": features["byte_size"],
            "dimensions_expressible": site_expressible,
        })
        ai_note = f"  AI-bots:{features['ai_bots_count']}" if features["ai_bots_count"] else ""
        cd_note = "  crawl-delay" if features["has_crawl_delay"] else ""
        print(f"OK  {features['disallow_count']:3d} disallow  "
              f"{features['user_agent_groups']:2d} UA-groups{ai_note}{cd_note}")
        time.sleep(0.5)   # polite delay between fetches

    # ── Write per-site CSV ───────────────────────────────────────────────────
    ps_path = os.path.join(outdir, "audit_per_site.csv")
    with open(ps_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(per_site[0].keys()))
        w.writeheader(); w.writerows(per_site)

    # ── Write per-dimension CSV ──────────────────────────────────────────────
    pd_path = os.path.join(outdir, "audit_per_dimension.csv")
    with open(pd_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["dimension", "label", "robots_capability",
                    "sites_expressed", "sites_partial", "sites_expressible_unused",
                    "sites_not_expressible", "cpnp_expressible"])
        for (dim_id, label, cap) in DIMENSIONS:
            c = dim_counts[dim_id]
            w.writerow([dim_id, label, cap, c["expressed"], c["partial"],
                        c["expressible_unused"], c["not_expressible"], "YES"])

    # ── Per-stratum aggregates ───────────────────────────────────────────────
    strata = {}
    for row in per_site:
        if row["fetch_status"] != 200:
            continue
        s = row["stratum"]
        strata.setdefault(s, {"sites": 0, "total_expressible": 0,
                              "ai_bot_sites": 0, "crawl_delay_sites": 0})
        strata[s]["sites"] += 1
        strata[s]["total_expressible"] += row["dimensions_expressible"]
        if row["ai_bots_count"] > 0: strata[s]["ai_bot_sites"] += 1
        if row["has_crawl_delay"]:   strata[s]["crawl_delay_sites"] += 1

    pstr_path = os.path.join(outdir, "audit_per_stratum.csv")
    with open(pstr_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["stratum", "sites_fetched", "avg_dimensions_expressible_of_14",
                    "sites_blocking_ai_bots", "sites_with_crawl_delay"])
        for s, d in sorted(strata.items()):
            avg = round(d["total_expressible"] / d["sites"], 2) if d["sites"] else 0
            w.writerow([s, d["sites"], avg, d["ai_bot_sites"], d["crawl_delay_sites"]])

    # ── Summary JSON ─────────────────────────────────────────────────────────
    total_ok = fetched
    avg_expressible = round(
        sum(r["dimensions_expressible"] for r in per_site if r["fetch_status"] == 200)
        / total_ok, 2) if total_ok else 0
    ai_blocking_sites = sum(1 for r in per_site if r["ai_bots_count"] > 0)
    crawl_delay_sites = sum(1 for r in per_site if r["has_crawl_delay"])

    summary = {
        "access_date": datetime.now(timezone.utc).isoformat(),
        "sites_total": len(WEBSITES),
        "sites_fetched_ok": fetched,
        "sites_failed": failed,
        "dimensions_assessed": len(DIMENSIONS),
        "avg_dimensions_expressible_robots_of_14": avg_expressible,
        "cpnp_dimensions_expressible_of_14": 14,
        "sites_attempting_ai_bot_blocks": ai_blocking_sites,
        "sites_with_crawl_delay": crawl_delay_sites,
        "key_finding": (
            f"Across {fetched} real robots.txt files, the average number of the 14 "
            f"CPNP governance dimensions even partially expressible was "
            f"{avg_expressible}/14. CPNP expresses all 14. This empirically "
            f"confirms the expressiveness gap."
        ),
    }
    sum_path = os.path.join(outdir, "audit_summary.json")
    with open(sum_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'='*72}")
    print(f"  AUDIT COMPLETE")
    print(f"{'='*72}")
    print(f"  Sites fetched OK:           {fetched}/{len(WEBSITES)}")
    print(f"  Sites failed:               {failed}")
    print(f"  Avg dimensions expressible: {avg_expressible}/14  (robots.txt)")
    print(f"  CPNP dimensions:            14/14")
    print(f"  Sites blocking AI bots:     {ai_blocking_sites}/{fetched}")
    print(f"  Sites with Crawl-delay:     {crawl_delay_sites}/{fetched}")
    print(f"\n  Results in: {outdir}/")
    print(f"    audit_per_site.csv        ({len(per_site)} rows)")
    print(f"    audit_per_dimension.csv   (14 rows)")
    print(f"    audit_per_stratum.csv     ({len(strata)} rows)")
    print(f"    audit_summary.json")
    print(f"    robots_raw/               (saved robots.txt files)\n")


if __name__ == "__main__":
    main()
