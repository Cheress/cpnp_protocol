"""
CPNP Security / Correctness Evaluation — produces MEASURED detection results.

It runs each scenario N times and records the outcome, producing a confusion
matrix and detection rates. These are the numbers behind any "100% adversarial
detection".

SCENARIOS:
  Legitimate (must be ACCEPTED):
    L1  valid signed intent + valid VC + valid token + allowed path
  Adversarial (must be REJECTED):
    A1  no token presented
    A2  forged JWT signature
    A3  tampered JWT payload (rate escalated)
    A4  expired JWT
    A5  wrong-issuer JWT (token from a different server)
    A6  wrong algorithm header (alg=none / RS256 downgrade)
    A7  path violation (token valid but path not in agreed scope)
    A8  tampered intent (fields changed after signing)
    A9  identity spoofing (claim another crawler's DID)
    A10 expired credential
    A11 revoked credential
    A12 tampered credential (privilege escalation in VC)
    A13 untrusted CA (VC from a CA not in trust store)

Run:
  python benchmarks/security_eval.py --trials 100
Outputs:
  results/security_results.csv      (per-scenario outcomes)
  results/confusion_matrix.json     (TP/TN/FP/FN + detection rate)
"""

from __future__ import annotations
import sys, os, json, csv, argparse, base64, uuid
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.identity.keys import generate_keypair, _b64url, _b64url_decode
from app.identity.did_document import build_did_document, register_did, get_public_key_b64
from app.identity.signatures import build_signed_intent, verify_intent_signature
from app.identity.credentials import (CredentialIssuer, verify_credential,
                                       register_trusted_ca)

_JWT_HEADER_B64 = _b64url(json.dumps({"alg": "EdDSA", "typ": "JWT"}, separators=(",", ":")).encode())

def jwt_issue(server_kp, crawler_did, rate, paths, hours=24):
    now = datetime.now(timezone.utc)
    payload = {"jti": str(uuid.uuid4()), "sub": crawler_did, "iss": server_kp.did,
               "iat": int(now.timestamp()),
               "exp": int((now + timedelta(hours=hours)).timestamp()),
               "purpose": "ResearchCrawler", "rate": rate, "paths": paths,
               "restrictions": ["no-ai-training"]}
    p64 = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    sig = server_kp.sign(f"{_JWT_HEADER_B64}.{p64}".encode("ascii"))
    return f"{_JWT_HEADER_B64}.{p64}.{sig}"

def jwt_verify(server_kp, token):
    """Returns (ok, reason)."""
    if not token:
        return False, "NO_TOKEN"
    parts = token.split(".")
    if len(parts) != 3:
        return False, "MALFORMED"
    h, p, s = parts
    try:
        hdr = json.loads(_b64url_decode(h))
    except Exception:
        return False, "MALFORMED"
    if hdr.get("alg") != "EdDSA":
        return False, "WRONG_ALGORITHM"
    if not server_kp.verify(f"{h}.{p}".encode("ascii"), s):
        return False, "INVALID_SIGNATURE"
    payload = json.loads(_b64url_decode(p))
    if int(datetime.now(timezone.utc).timestamp()) > payload.get("exp", 0):
        return False, "TOKEN_EXPIRED"
    if payload.get("iss") != server_kp.did:
        return False, "WRONG_ISSUER"
    return True, "OK"

def path_in_scope(lp, agreed):
    for ap in agreed:
        if ap == "/" and lp == "/":
            return True
        if ap != "/" and (lp == ap or lp.startswith(ap + "/") or lp.startswith(ap)):
            return True
    return False


def setup():
    server_kp = generate_keypair("sec-server")
    register_did(build_did_document(server_kp, operator_name="Sec Server"))
    other_server_kp = generate_keypair("sec-other-server")   # for wrong-issuer
    register_did(build_did_document(other_server_kp, operator_name="Other Server"))
    ca = CredentialIssuer("sec-ca")
    register_trusted_ca(ca)
    rogue_ca = CredentialIssuer("rogue-ca")                  # NOT trusted

    crawler_kp = generate_keypair("sec-crawler")
    register_did(build_did_document(crawler_kp, purposes=["ResearchCrawler"], operator_name="Crawler"))
    evil_kp = generate_keypair("sec-evil")
    register_did(build_did_document(evil_kp, purposes=["ResearchCrawler"], operator_name="Evil"))

    vc = ca.issue(subject_did=crawler_kp.did, operator_name="Crawler",
                  operator_contact="c@t.com", purposes=["ResearchCrawler"])
    agreed_paths = ["/", "/blog", "/research"]
    good_token = jwt_issue(server_kp, crawler_kp.did, 20, agreed_paths)

    return locals()


def run_scenario(name, ctx):
    """Returns (expected, actual) where each is 'ACCEPT' or 'REJECT'."""
    s = ctx["server_kp"]; ca = ctx["ca"]; ck = ctx["crawler_kp"]
    vc = ctx["vc"]; agreed = ctx["agreed_paths"]; good = ctx["good_token"]

    # ── Legitimate 
    if name == "L1_legitimate":
        ok_t, _ = jwt_verify(s, good)
        ok_p = path_in_scope("/blog", agreed)
        ok_v = verify_credential(vc, ca).valid
        return "ACCEPT", ("ACCEPT" if (ok_t and ok_p and ok_v) else "REJECT")

    # ── Token-layer attacks 
    if name == "A1_no_token":
        ok, _ = jwt_verify(s, "")
        return "REJECT", ("ACCEPT" if ok else "REJECT")
    if name == "A2_forged_sig":
        h, p, _ = good.split("."); forged = f"{h}.{p}.{_b64url(b'X'*64)}"
        ok, _ = jwt_verify(s, forged)
        return "REJECT", ("ACCEPT" if ok else "REJECT")
    if name == "A3_tampered_payload":
        h, p, sig = good.split(".")
        payload = json.loads(_b64url_decode(p)); payload["rate"] = 9999
        p2 = _b64url(json.dumps(payload, separators=(",", ":")).encode())
        ok, _ = jwt_verify(s, f"{h}.{p2}.{sig}")
        return "REJECT", ("ACCEPT" if ok else "REJECT")
    if name == "A4_expired":
        expired = jwt_issue(s, ck.did, 20, agreed, hours=-2)
        ok, _ = jwt_verify(s, expired)
        return "REJECT", ("ACCEPT" if ok else "REJECT")
    if name == "A5_wrong_issuer":
        wrong = jwt_issue(ctx["other_server_kp"], ck.did, 20, agreed)
        ok, _ = jwt_verify(s, wrong)
        return "REJECT", ("ACCEPT" if ok else "REJECT")
    if name == "A6_wrong_algorithm":
        h, p, sig = good.split(".")
        bad_h = _b64url(b'{"alg":"none","typ":"JWT"}')
        ok, _ = jwt_verify(s, f"{bad_h}.{p}.{sig}")
        return "REJECT", ("ACCEPT" if ok else "REJECT")
    if name == "A7_path_violation":
        ok_t, _ = jwt_verify(s, good)
        ok_p = path_in_scope("/admin", agreed)
        return "REJECT", ("ACCEPT" if (ok_t and ok_p) else "REJECT")

    # ── Intent-signature attacks 
    if name == "A8_tampered_intent":
        intent = {"crawler_did": ck.did, "declared_purpose": "ResearchCrawler",
                  "requested_crawl_rate": 20, "requested_paths": ["/blog"],
                  "operator_name": "C", "operator_contact": "c@t.com",
                  "data_use_commitments": ["no-ai-training"]}
        signed = build_signed_intent(intent, ck)
        signed["requested_crawl_rate"] = 9999   # tamper after signing
        res = verify_intent_signature(signed)
        return "REJECT", ("ACCEPT" if res.valid else "REJECT")
    if name == "A9_identity_spoof":
        intent = {"crawler_did": ck.did, "declared_purpose": "ResearchCrawler",
                  "requested_crawl_rate": 20, "requested_paths": ["/blog"],
                  "operator_name": "C", "operator_contact": "c@t.com",
                  "data_use_commitments": ["no-ai-training"]}
        signed = build_signed_intent(intent, ck)
        signed["crawler_did"] = ctx["evil_kp"].did   # claim evil DID
        res = verify_intent_signature(signed)
        return "REJECT", ("ACCEPT" if res.valid else "REJECT")

    # ── Credential attacks 
    if name == "A10_expired_credential":
        exp_vc = json.loads(json.dumps(vc))
        exp_vc["expirationDate"] = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        res = verify_credential(exp_vc, ca)
        return "REJECT", ("ACCEPT" if res.valid else "REJECT")
    if name == "A11_revoked_credential":
        rvc = ca.issue(subject_did=ck.did, operator_name="C", operator_contact="c@t.com",
                       purposes=["ResearchCrawler"])
        ca.revoke(rvc["id"])
        res = verify_credential(rvc, ca)
        return "REJECT", ("ACCEPT" if res.valid else "REJECT")
    if name == "A12_tampered_credential":
        tvc = json.loads(json.dumps(vc))
        tvc["credentialSubject"]["allowedPurposes"] = ["AITrainer"]   # escalate
        res = verify_credential(tvc, ca)
        return "REJECT", ("ACCEPT" if res.valid else "REJECT")
    if name == "A13_untrusted_ca":
        rogue_vc = ctx["rogue_ca"].issue(subject_did=ck.did, operator_name="C",
                                         operator_contact="c@t.com", purposes=["ResearchCrawler"])
        res = verify_credential(rogue_vc, ca)
        return "REJECT", ("ACCEPT" if res.valid else "REJECT")

    raise ValueError(f"unknown scenario {name}")


SCENARIOS = [
    "L1_legitimate",
    "A1_no_token", "A2_forged_sig", "A3_tampered_payload", "A4_expired",
    "A5_wrong_issuer", "A6_wrong_algorithm", "A7_path_violation",
    "A8_tampered_intent", "A9_identity_spoof",
    "A10_expired_credential", "A11_revoked_credential",
    "A12_tampered_credential", "A13_untrusted_ca",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=100)
    ap.add_argument("--outdir", default=os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results"))
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    print(f"\n{'='*68}\n  CPNP Security / Correctness Evaluation  (trials={args.trials})\n{'='*68}\n")

    rows = []
    tp = tn = fp = fn = 0   # TP=adversarial correctly rejected, TN=legit correctly accepted

    for name in SCENARIOS:
        ctx = setup()   # fresh actors per scenario to avoid cross-contamination
        correct = 0
        expected_first = None
        for _ in range(args.trials):
            ctx2 = setup()
            expected, actual = run_scenario(name, ctx2)
            expected_first = expected
            if expected == actual:
                correct += 1
            # confusion matrix accounting
            if expected == "REJECT":
                if actual == "REJECT": tp += 1
                else: fn += 1
            else:
                if actual == "ACCEPT": tn += 1
                else: fp += 1
        rate = round(correct / args.trials * 100, 2)
        is_legit = name.startswith("L")
        rows.append({"scenario": name,
                     "type": "legitimate" if is_legit else "adversarial",
                     "expected": expected_first, "trials": args.trials,
                     "correct": correct, "accuracy_pct": rate})
        icon = "✅" if rate == 100.0 else "⚠️"
        print(f"  {icon} {name:24s} {('legit' if is_legit else 'attack'):7s} "
              f"correct={correct}/{args.trials} ({rate}%)")

    # Write results
    path = os.path.join(args.outdir, "security_results.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["scenario", "type", "expected", "trials", "correct", "accuracy_pct"])
        w.writeheader(); w.writerows(rows)

    total = tp + tn + fp + fn
    detection_rate = round(tp / (tp + fn) * 100, 2) if (tp + fn) else 0
    precision = round(tp / (tp + fp) * 100, 2) if (tp + fp) else 0
    accuracy = round((tp + tn) / total * 100, 2) if total else 0

    cm = {"true_positive_adversarial_rejected": tp,
          "true_negative_legitimate_accepted": tn,
          "false_positive_legitimate_rejected": fp,
          "false_negative_adversarial_accepted": fn,
          "detection_rate_pct": detection_rate,
          "precision_pct": precision,
          "overall_accuracy_pct": accuracy,
          "total_trials": total,
          "scenarios": len(SCENARIOS),
          "trials_per_scenario": args.trials}
    cm_path = os.path.join(args.outdir, "confusion_matrix.json")
    with open(cm_path, "w") as f:
        json.dump(cm, f, indent=2)

    print(f"\n  ── CONFUSION MATRIX ──")
    print(f"  Adversarial correctly rejected (TP): {tp}")
    print(f"  Legitimate correctly accepted  (TN): {tn}")
    print(f"  Legitimate wrongly rejected    (FP): {fp}")
    print(f"  Adversarial wrongly accepted   (FN): {fn}")
    print(f"\n  Detection rate: {detection_rate}%   Precision: {precision}%   Accuracy: {accuracy}%")
    print(f"\n  Results: {path}\n           {cm_path}\n")


if __name__ == "__main__":
    main()
