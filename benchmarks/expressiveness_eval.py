"""
cpnp/benchmarks/expressiveness_eval.py
────────────────────────────────────────
CPNP Expressiveness Evaluation — measured policy-encoding capability.

Run:
  python benchmarks/expressiveness_eval.py
Outputs:
  results/expressiveness_results.csv
"""
from __future__ import annotations
import sys, os, csv, json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# For each, we record whether robots.txt (RFC 9309) and CPNP can express it,
# with a concrete justification grounded in each format's actual capabilities.

DIMENSIONS = [
    # (id, intent, robots_txt_capable, cpnp_capable, robots_mechanism, cpnp_mechanism)
    ("D1", "Restrict crawling to specific URL paths",
     True, True,
     "Disallow: /path directives",
     "allowed_paths / disallowed_paths in Policy Manifest"),
    ("D2", "Limit crawl request rate",
     "partial", True,
     "Crawl-delay (non-standard, widely ignored, not in RFC 9309)",
     "max_crawl_rate, enforced via signed token + middleware"),
    ("D3", "Discriminate access by crawler identity",
     "partial", True,
     "User-agent matching (trivially spoofable string)",
     "Cryptographic DID identity, unforgeable"),
    ("D4", "Permit access by declared purpose (research vs AI training)",
     False, True,
     "No purpose concept exists in robots.txt",
     "declared_purpose checked against allowed_purposes + VC"),
    ("D5", "Bind access to a verifiable operator identity",
     False, True,
     "No authentication mechanism",
     "W3C Verifiable Credential issued by trusted CA"),
    ("D6", "Restrict downstream data use (no AI training)",
     False, True,
     "No data-use semantics",
     "data_use_restrictions in Policy Manifest + token claim"),
    ("D7", "Prohibit commercial resale of crawled data",
     False, True,
     "No data-use semantics",
     "data_use_restrictions: no-commercial-resale"),
    ("D8", "Grant time-limited access (temporal window)",
     False, True,
     "No expiry concept",
     "Token exp claim + policy_expires_at"),
    ("D9", "Negotiate terms bilaterally (counter-offers)",
     False, True,
     "Unilateral declaration only",
     "Alternating-offers negotiation engine"),
    ("D10", "Produce a non-repudiable record of agreement",
     False, True,
     "No agreement artefact",
     "EdDSA-signed JWT Access Token"),
    ("D11", "Enforce compliance cryptographically (not advisory)",
     False, True,
     "Advisory only; honour system",
     "Token signature verified on every request; 451 on violation"),
    ("D12", "Provide an auditable per-request compliance trail",
     False, True,
     "No logging/attribution mechanism",
     "SQLite audit log keyed by crawler DID + token"),
    ("D13", "Express jurisdiction-specific restrictions",
     False, True,
     "No jurisdiction field",
     "jurisdiction attribute in Verifiable Credential"),
    ("D14", "Support compensation / paid-access terms",
     False, True,
     "No commercial terms",
     "Optional compensation terms in Policy Manifest (extensible)"),
]


def robots_can_express(flag):
    return flag is True   # 'partial' counts as NOT fully expressible


def main():
    outdir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
    os.makedirs(outdir, exist_ok=True)

    print(f"\n{'='*72}\n  CPNP Expressiveness Evaluation — 14 policy dimensions\n{'='*72}\n")
    print(f"  {'ID':4s} {'Intent':52s} {'robots':8s} {'CPNP':6s}")
    print(f"  {'-'*4} {'-'*52} {'-'*8} {'-'*6}")

    rows = []
    robots_full = robots_partial = cpnp_yes = 0
    for (did, intent, rtxt, cpnp, rmech, cmech) in DIMENSIONS:
        rtxt_label = "YES" if rtxt is True else ("PARTIAL" if rtxt == "partial" else "NO")
        cpnp_label = "YES" if cpnp else "NO"
        if rtxt is True: robots_full += 1
        elif rtxt == "partial": robots_partial += 1
        if cpnp: cpnp_yes += 1
        rows.append({"dimension": did, "policy_intent": intent,
                     "robots_txt": rtxt_label, "cpnp": cpnp_label,
                     "robots_mechanism": rmech, "cpnp_mechanism": cmech})
        short = intent[:50]
        print(f"  {did:4s} {short:52s} {rtxt_label:8s} {cpnp_label:6s}")

    path = os.path.join(outdir, "expressiveness_results.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["dimension", "policy_intent", "robots_txt",
                                          "cpnp", "robots_mechanism", "cpnp_mechanism"])
        w.writeheader(); w.writerows(rows)

    total = len(DIMENSIONS)
    print(f"\n  ── SUMMARY ──")
    print(f"  Total policy dimensions assessed:        {total}")
    print(f"  robots.txt fully expressible:            {robots_full}/{total}")
    print(f"  robots.txt partially (spoofable/ignored): {robots_partial}/{total}")
    print(f"  robots.txt NOT expressible:              {total - robots_full - robots_partial}/{total}")
    print(f"  CPNP expressible:                        {cpnp_yes}/{total}")
    print(f"\n  Results: {path}\n")


if __name__ == "__main__":
    main()
