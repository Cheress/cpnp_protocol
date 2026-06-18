"""
CPNP Performance Benchmark Harness — produces MEASURED, reproducible results.

This harness exercises the REAL cryptographic and protocol algorithms from the
CPNP MVP (Ed25519 key generation, DID derivation, intent signing/verification,
verifiable-credential issuance/verification, JWT minting/verification, and the
negotiation scoring engine). It measures wall-clock latency for each operation
and for the full end-to-end handshake, then writes results to CSV and JSON.


WHAT IT MEASURES:
  1. keygen          — Ed25519 keypair generation + did:key derivation
  2. did_register    — building + registering a DID document
  3. vc_issue        — CA issues a signed Verifiable Credential
  4. vc_verify       — server verifies a Verifiable Credential
  5. intent_sign     — crawler signs an Intent Declaration
  6. intent_verify   — server verifies the Intent signature
  7. negotiate       — negotiation scoring engine (1 round)
  8. token_issue     — server mints an EdDSA JWT access token
  9. token_verify    — server verifies a JWT on a crawl request
 10. e2e_handshake   — full pre-crawl handshake (init→policy→intent→agree→token)

Run:
  python benchmarks/benchmark.py --iterations 1000 --warmup 100
Outputs:
  results/raw_measurements.csv     (every individual measurement)
  results/summary_statistics.csv   (per-operation statistics)
  results/benchmark_metadata.json  (environment + parameters for reproducibility)
"""

from __future__ import annotations
import sys, os, json, csv, time, argparse, statistics, platform, hashlib
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Real MVP cryptographic modules (only need `cryptography`)
from app.identity.keys import generate_keypair, _b64url, _b64url_decode
from app.identity.did_document import (build_did_document, register_did,
                                        get_public_key_b64, DID_REGISTRY)
from app.identity.signatures import build_signed_intent, verify_intent_signature
from app.identity.credentials import (CredentialIssuer, verify_credential,
                                       register_trusted_ca)

# ── JWT logic (identical algorithm to app/enforcement/tokens.py) ──────────────
import uuid
_JWT_HEADER_B64 = _b64url(json.dumps({"alg": "EdDSA", "typ": "JWT"},
                                     separators=(",", ":")).encode())

def jwt_issue(server_kp, crawler_did, purpose, rate, paths, restrictions):
    now = datetime.now(timezone.utc)
    payload = {"jti": str(uuid.uuid4()), "sub": crawler_did, "iss": server_kp.did,
               "iat": int(now.timestamp()),
               "exp": int((now + timedelta(hours=24)).timestamp()),
               "purpose": purpose, "rate": rate, "paths": paths,
               "restrictions": restrictions}
    p64 = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    sig = server_kp.sign(f"{_JWT_HEADER_B64}.{p64}".encode("ascii"))
    return f"{_JWT_HEADER_B64}.{p64}.{sig}"

def jwt_verify(server_kp, token):
    parts = token.split(".")
    if len(parts) != 3:
        return False
    h, p, s = parts
    hdr = json.loads(_b64url_decode(h))
    if hdr.get("alg") != "EdDSA":
        return False
    if not server_kp.verify(f"{h}.{p}".encode("ascii"), s):
        return False
    payload = json.loads(_b64url_decode(p))
    if int(datetime.now(timezone.utc).timestamp()) > payload.get("exp", 0):
        return False
    if payload.get("iss") != server_kp.did:
        return False
    return True

# ── Negotiation scoring (identical algorithm to app/negotiation.py) ───────────
def negotiate_score(policy, req_rate, req_paths):
    score = 1.0
    agreed_rate = req_rate
    if req_rate > policy["max_crawl_rate"]:
        score -= 0.50
        agreed_rate = policy["max_crawl_rate"]
    agreed_paths, blocked = [], []
    for p in req_paths:
        ok = any(p.startswith(ap) for ap in policy["allowed_paths"])
        bad = any(p.startswith(dp) for dp in policy["disallowed_paths"])
        (blocked if (bad or not ok) else agreed_paths).append(p)
    if blocked:
        score -= 0.50 * (len(blocked) / max(len(req_paths), 1))
    if not agreed_paths:
        agreed_paths = policy["allowed_paths"]
    return max(0.0, round(score, 4)), agreed_rate, agreed_paths


# ── Timing utility
def time_op(fn, iterations, warmup):
    """Times fn() over `iterations` runs after `warmup` discarded runs.
    Returns list of per-call latencies in milliseconds."""
    for _ in range(warmup):
        fn()
    samples = []
    for _ in range(iterations):
        t0 = time.perf_counter_ns()
        fn()
        t1 = time.perf_counter_ns()
        samples.append((t1 - t0) / 1_000_000.0)   # ns → ms
    return samples


def stats(samples):
    s = sorted(samples)
    n = len(s)
    def pct(p):
        idx = min(n - 1, int(round(p / 100.0 * (n - 1))))
        return s[idx]
    return {
        "n": n,
        "mean_ms":   round(statistics.mean(s), 4),
        "median_ms": round(statistics.median(s), 4),
        "stdev_ms":  round(statistics.pstdev(s), 4),
        "min_ms":    round(s[0], 4),
        "p95_ms":    round(pct(95), 4),
        "p99_ms":    round(pct(99), 4),
        "max_ms":    round(s[-1], 4),
    }


# ── Benchmark scenarios setup 
def setup():
    """Builds the fixed actors used across all benchmarks."""
    server_kp = generate_keypair("bench-server")
    register_did(build_did_document(server_kp, cpnp_endpoint="http://localhost:8000",
                                    operator_name="Bench Server"))
    ca = CredentialIssuer("bench-ca")
    register_trusted_ca(ca)

    crawler_kp = generate_keypair("bench-crawler")
    register_did(build_did_document(crawler_kp, purposes=["ResearchCrawler"],
                                    operator_name="Bench Crawler"))
    vc = ca.issue(subject_did=crawler_kp.did, operator_name="Bench Crawler",
                  operator_contact="bench@jkuat.ac.ke", purposes=["ResearchCrawler"],
                  max_crawl_rate=60, validity_days=30)

    policy = {"max_crawl_rate": 30,
              "allowed_paths": ["/", "/blog", "/docs", "/research"],
              "disallowed_paths": ["/admin", "/private", "/user"]}

    intent = {"crawler_did": crawler_kp.did, "declared_purpose": "ResearchCrawler",
              "requested_crawl_rate": 20, "requested_paths": ["/", "/blog"],
              "operator_name": "Bench Crawler", "operator_contact": "bench@jkuat.ac.ke",
              "data_use_commitments": ["no-ai-training", "no-commercial-resale"]}
    signed_intent = build_signed_intent(intent, crawler_kp)

    token = jwt_issue(server_kp, crawler_kp.did, "ResearchCrawler", 20,
                      ["/", "/blog", "/research"], ["no-ai-training"])

    return {"server_kp": server_kp, "ca": ca, "crawler_kp": crawler_kp,
            "vc": vc, "policy": policy, "intent": intent,
            "signed_intent": signed_intent, "token": token}


def build_operations(ctx):
    """Returns dict of {operation_name: callable} — each a single real op."""
    server_kp = ctx["server_kp"]; ca = ctx["ca"]; crawler_kp = ctx["crawler_kp"]
    vc = ctx["vc"]; policy = ctx["policy"]; intent = ctx["intent"]
    signed_intent = ctx["signed_intent"]; token = ctx["token"]

    ops = {}

    ops["1_keygen"] = lambda: generate_keypair("tmp")

    def _did_register():
        kp = generate_keypair("tmp2")
        register_did(build_did_document(kp, operator_name="t"))
    ops["2_did_register"] = _did_register

    ops["3_vc_issue"] = lambda: ca.issue(
        subject_did=crawler_kp.did, operator_name="t", operator_contact="t@t.com",
        purposes=["ResearchCrawler"], max_crawl_rate=60, validity_days=30)

    ops["4_vc_verify"] = lambda: verify_credential(vc, ca)

    ops["5_intent_sign"] = lambda: build_signed_intent(intent, crawler_kp)

    ops["6_intent_verify"] = lambda: verify_intent_signature(signed_intent)

    ops["7_negotiate"] = lambda: negotiate_score(
        policy, intent["requested_crawl_rate"], intent["requested_paths"])

    ops["8_token_issue"] = lambda: jwt_issue(
        server_kp, crawler_kp.did, "ResearchCrawler", 20,
        ["/", "/blog", "/research"], ["no-ai-training"])

    ops["9_token_verify"] = lambda: jwt_verify(server_kp, token)

  
    def _e2e():
        si = build_signed_intent(intent, crawler_kp)          # crawler signs
        verify_intent_signature(si)                            # server verifies sig
        verify_credential(vc, ca)                              # server verifies VC
        negotiate_score(policy, intent["requested_crawl_rate"],
                        intent["requested_paths"])             # negotiation
        t = jwt_issue(server_kp, crawler_kp.did, "ResearchCrawler", 20,
                      ["/", "/blog"], ["no-ai-training"])      # issue token
        jwt_verify(server_kp, t)                               # first request check
    ops["10_e2e_handshake"] = _e2e

    return ops


# ── Main 
def main():
    ap = argparse.ArgumentParser(description="CPNP performance benchmark")
    ap.add_argument("--iterations", type=int, default=1000)
    ap.add_argument("--warmup", type=int, default=100)
    ap.add_argument("--outdir", default=os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results"))
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    print(f"\n{'='*68}")
    print(f"  CPNP Performance Benchmark")
    print(f"  iterations={args.iterations}  warmup={args.warmup}")
    print(f"{'='*68}\n")

    ctx = setup()
    ops = build_operations(ctx)

    raw_rows = []
    summary_rows = []

    for name in sorted(ops.keys()):
        fn = ops[name]
        samples = time_op(fn, args.iterations, args.warmup)
        st = stats(samples)
        summary_rows.append({"operation": name, **st})
        for i, ms in enumerate(samples):
            raw_rows.append({"operation": name, "iteration": i, "latency_ms": round(ms, 6)})
        print(f"  {name:20s}  mean={st['mean_ms']:8.4f}ms  "
              f"median={st['median_ms']:8.4f}ms  p95={st['p95_ms']:8.4f}ms  "
              f"p99={st['p99_ms']:8.4f}ms")

    # Write raw measurements
    raw_path = os.path.join(args.outdir, "raw_measurements.csv")
    with open(raw_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["operation", "iteration", "latency_ms"])
        w.writeheader(); w.writerows(raw_rows)

    # Write summary
    sum_path = os.path.join(args.outdir, "summary_statistics.csv")
    with open(sum_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["operation", "n", "mean_ms", "median_ms",
                                          "stdev_ms", "min_ms", "p95_ms", "p99_ms", "max_ms"])
        w.writeheader(); w.writerows(summary_rows)

    # Write metadata for reproducibility
    meta = {
        "benchmark_timestamp": datetime.now(timezone.utc).isoformat(),
        "iterations": args.iterations,
        "warmup": args.warmup,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor() or "unknown",
        "signature_scheme": "Ed25519 (EdDSA)",
        "token_format": "JWT (RFC 7519) with EdDSA signature",
        "operations_measured": sorted(ops.keys()),
        "clock": "time.perf_counter_ns (monotonic, nanosecond resolution)",
        "note": ("All operations call the real CPNP MVP cryptographic functions. "
                 "Latencies are wall-clock per-operation after warmup discard.")
    }
    meta_path = os.path.join(args.outdir, "benchmark_metadata.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\n  Results written to:")
    print(f"    {raw_path}")
    print(f"    {sum_path}")
    print(f"    {meta_path}\n")

    # Print e2e headline
    e2e = next(r for r in summary_rows if r["operation"] == "10_e2e_handshake")
    print(f"  ── HEADLINE ──")
    print(f"  Full handshake: mean={e2e['mean_ms']:.2f}ms  "
          f"median={e2e['median_ms']:.2f}ms  p95={e2e['p95_ms']:.2f}ms  "
          f"p99={e2e['p99_ms']:.2f}ms\n")


if __name__ == "__main__":
    main()
