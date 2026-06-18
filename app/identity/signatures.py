from __future__ import annotations
import json, base64
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from .keys import KeyPair, _b64url, _b64url_decode
from .did_document import get_public_key_b64

MAX_PROOF_AGE_MINUTES = 5

@dataclass
class VerificationResult:
    valid: bool; error: str = ""; crawler_did: str = ""; verified_at: str = ""

def sign_intent(intent_dict: dict, kp: KeyPair) -> dict:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = _canonical_payload(intent_dict)
    sig = kp.sign(payload.encode("utf-8"))
    return {"type":"Ed25519Signature2020","created":now,
            "verificationMethod":f"{kp.did}#key-1","proofPurpose":"authentication","proofValue":sig}

def build_signed_intent(intent_dict: dict, kp: KeyPair) -> dict:
    signed = {k:v for k,v in intent_dict.items() if k!="proof"}
    signed["proof"] = sign_intent(signed, kp)
    return signed

def verify_intent_signature(signed_intent: dict) -> VerificationResult:
    proof = signed_intent.get("proof")
    if not proof: return VerificationResult(valid=False,error="NO_PROOF: IntentDeclaration has no 'proof' field.")
    for f in ("type","created","verificationMethod","proofValue"):
        if f not in proof: return VerificationResult(valid=False,error=f"MALFORMED_PROOF: missing '{f}'")
    if proof["type"]!="Ed25519Signature2020": return VerificationResult(valid=False,error=f"UNSUPPORTED_PROOF_TYPE")
    crawler_did = signed_intent.get("crawler_did","")
    vm = proof.get("verificationMethod","")
    if vm!=f"{crawler_did}#key-1": return VerificationResult(valid=False,error=f"DID_MISMATCH: {vm} vs {crawler_did}#key-1")
    pub_b64 = get_public_key_b64(crawler_did)
    if pub_b64 is None: return VerificationResult(valid=False,error=f"DID_NOT_FOUND: '{crawler_did}' not registered.")
    try:
        pt = datetime.strptime(proof["created"],"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc)-pt
        if age>timedelta(minutes=MAX_PROOF_AGE_MINUTES):
            return VerificationResult(valid=False,error=f"PROOF_EXPIRED: {int(age.total_seconds()/60)} min old.")
    except ValueError: return VerificationResult(valid=False,error="INVALID_TIMESTAMP")
    payload_dict = {k:v for k,v in signed_intent.items() if k!="proof"}
    payload_bytes = _canonical_payload(payload_dict).encode("utf-8")
    try:
        raw_pub = base64.urlsafe_b64decode(pub_b64+"==")
        raw_sig = _b64url_decode(proof["proofValue"])
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        Ed25519PublicKey.from_public_bytes(raw_pub).verify(raw_sig, payload_bytes)
    except Exception as e:
        return VerificationResult(valid=False,error=f"INVALID_SIGNATURE: {type(e).__name__}")
    return VerificationResult(valid=True,crawler_did=crawler_did,verified_at=datetime.now(timezone.utc).isoformat())

def _canonical_payload(d: dict) -> str:
    return json.dumps({k:v for k,v in d.items() if k!="proof"},sort_keys=True,separators=(",",":"),ensure_ascii=False)
