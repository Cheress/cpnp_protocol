"""
cpnp/benchmarks/throughput_eval.py
────────────────────────────────────
CPNP Throughput Evaluation — measured operations-per-second and overhead.

Run:
  python benchmarks/throughput_eval.py --duration 5
Outputs:
  results/throughput_results.csv
"""
from __future__ import annotations
import sys, os, json, csv, time, argparse, uuid
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.identity.keys import generate_keypair, _b64url, _b64url_decode
from app.identity.did_document import build_did_document, register_did
from app.identity.signatures import build_signed_intent, verify_intent_signature
from app.identity.credentials import CredentialIssuer, verify_credential, register_trusted_ca

_H = _b64url(json.dumps({"alg": "EdDSA", "typ": "JWT"}, separators=(",", ":")).encode())

def jwt_issue(s, did, rate, paths):
    now = datetime.now(timezone.utc)
    pl = {"jti": str(uuid.uuid4()), "sub": did, "iss": s.did, "iat": int(now.timestamp()),
          "exp": int((now+timedelta(hours=24)).timestamp()), "purpose": "ResearchCrawler",
          "rate": rate, "paths": paths, "restrictions": ["no-ai-training"]}
    p = _b64url(json.dumps(pl, separators=(",", ":")).encode())
    return f"{_H}.{p}.{s.sign(f'{_H}.{p}'.encode())}"

def jwt_verify(s, tok):
    h, p, sig = tok.split(".")
    if not s.verify(f"{h}.{p}".encode(), sig): return False
    pl = json.loads(_b64url_decode(p))
    return pl.get("iss") == s.did and int(datetime.now(timezone.utc).timestamp()) <= pl["exp"]


def measure_ops_per_sec(fn, duration_s):
    """Runs fn() in a tight loop for duration_s seconds, returns ops/sec."""
    count = 0
    end = time.perf_counter() + duration_s
    while time.perf_counter() < end:
        fn(); count += 1
    return count / duration_s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration", type=float, default=5.0)
    ap.add_argument("--outdir", default=os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results"))
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    print(f"\n{'='*68}\n  CPNP Throughput Evaluation  (duration={args.duration}s per test)\n{'='*68}\n")

    s = generate_keypair("tp-server"); register_did(build_did_document(s, operator_name="S"))
    ca = CredentialIssuer("tp-ca"); register_trusted_ca(ca)
    c = generate_keypair("tp-crawler"); register_did(build_did_document(c, purposes=["ResearchCrawler"], operator_name="C"))
    vc = ca.issue(subject_did=c.did, operator_name="C", operator_contact="c@t.com", purposes=["ResearchCrawler"])
    intent = {"crawler_did": c.did, "declared_purpose": "ResearchCrawler",
              "requested_crawl_rate": 20, "requested_paths": ["/blog"],
              "operator_name": "C", "operator_contact": "c@t.com",
              "data_use_commitments": ["no-ai-training"]}
    signed = build_signed_intent(intent, c)
    tok = jwt_issue(s, c.did, 20, ["/", "/blog"])

    tests = {
        "token_verify_per_request": lambda: jwt_verify(s, tok),
        "credential_verify":        lambda: verify_credential(vc, ca),
        "intent_verify":            lambda: verify_intent_signature(signed),
        "token_issue":              lambda: jwt_issue(s, c.did, 20, ["/", "/blog"]),
        "full_handshake": lambda: (build_signed_intent(intent, c),
                                   verify_intent_signature(signed),
                                   verify_credential(vc, ca),
                                   jwt_issue(s, c.did, 20, ["/blog"]),
                                   jwt_verify(s, tok)),
    }

    rows = []
    for name, fn in tests.items():
        ops = measure_ops_per_sec(fn, args.duration)
        rows.append({"operation": name, "ops_per_sec": round(ops, 1),
                     "mean_latency_ms": round(1000.0 / ops, 4) if ops else 0})
        print(f"  {name:30s}  {ops:12,.0f} ops/sec   ({1000.0/ops:.4f} ms/op)")

    path = os.path.join(args.outdir, "throughput_results.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["operation", "ops_per_sec", "mean_latency_ms"])
        w.writeheader(); w.writerows(rows)

    hs = next(r for r in rows if r["operation"] == "full_handshake")
    tv = next(r for r in rows if r["operation"] == "token_verify_per_request")
    print(f"\n  ── HEADLINE ──")
    print(f"  Sustained handshakes:        {hs['ops_per_sec']:,.0f} per second per core")
    print(f"  Per-request enforcement cost: {tv['mean_latency_ms']:.4f} ms "
          f"({tv['ops_per_sec']:,.0f} checks/sec)")
    print(f"\n  Results: {path}\n")


if __name__ == "__main__":
    main()
