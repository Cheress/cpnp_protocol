from __future__ import annotations
import json, uuid, base64
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from typing import Optional
from .keys import generate_keypair, KeyPair, _b64url, _b64url_decode
from .did_document import build_did_document, register_did, get_public_key_b64

@dataclass
class CredentialVerificationResult:
    valid: bool; error: str = ""; subject_did: str = ""
    allowed_purposes: list = None; operator_name: str = ""; max_crawl_rate: Optional[int] = None
    def __post_init__(self):
        if self.allowed_purposes is None: self.allowed_purposes = []

TRUSTED_CA_DIDS: set[str] = set()

class CredentialIssuer:
    def __init__(self, name="cpnp-mock-ca"):
        self.keypair = generate_keypair(name); self.name = name
        self._issued: dict[str,dict] = {}; self._revoked: set[str] = set()
        register_did(build_did_document(self.keypair,operator_name="CPNP Mock CA",operator_contact="ca@cpnp.example"))
    @property
    def did(self): return self.keypair.did
    def issued_count(self): return len(self._issued)
    def issue(self,subject_did,operator_name,operator_contact,purposes,max_crawl_rate=60,validity_days=30,jurisdiction="KE") -> dict:
        now=datetime.now(timezone.utc); exp=now+timedelta(days=validity_days)
        vc_id=f"urn:uuid:{uuid.uuid4()}"
        vc={"@context":["https://www.w3.org/2018/credentials/v1"],"id":vc_id,
            "type":["VerifiableCredential","CPNPCrawlerCredential"],"issuer":self.did,
            "issuanceDate":now.strftime("%Y-%m-%dT%H:%M:%SZ"),"expirationDate":exp.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "credentialSubject":{"id":subject_did,"operatorName":operator_name,"operatorContact":operator_contact,
                                 "allowedPurposes":purposes,"maxCrawlRate":max_crawl_rate,"jurisdiction":jurisdiction}}
        vc["proof"]=self._sign(vc); self._issued[vc_id]=vc; return vc
    def revoke(self,vc_id): self._revoked.add(vc_id)
    def is_revoked(self,vc_id): return vc_id in self._revoked
    def _sign(self,vc):
        pl=_canonical_vc(vc); sig=self.keypair.sign(pl.encode())
        now=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return {"type":"Ed25519Signature2020","created":now,"verificationMethod":f"{self.did}#key-1","proofPurpose":"assertionMethod","proofValue":sig}

def register_trusted_ca(ca: CredentialIssuer): TRUSTED_CA_DIDS.add(ca.did)

def verify_credential(vc: dict, ca: Optional[CredentialIssuer]=None) -> CredentialVerificationResult:
    for f in ("id","issuer","issuanceDate","expirationDate","credentialSubject","proof"):
        if f not in vc: return CredentialVerificationResult(valid=False,error=f"MALFORMED_VC: missing '{f}'")
    subj=vc.get("credentialSubject",{}); subject_did=subj.get("id","")
    issuer_did=vc.get("issuer","")
    if TRUSTED_CA_DIDS and issuer_did not in TRUSTED_CA_DIDS:
        return CredentialVerificationResult(valid=False,error=f"UNTRUSTED_ISSUER: '{issuer_did}'")
    try:
        exp=datetime.strptime(vc["expirationDate"],"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc)>exp: return CredentialVerificationResult(valid=False,error=f"CREDENTIAL_EXPIRED: at {vc['expirationDate']}")
    except ValueError: return CredentialVerificationResult(valid=False,error="INVALID_EXPIRY_DATE")
    if ca and ca.is_revoked(vc.get("id","")): return CredentialVerificationResult(valid=False,error=f"CREDENTIAL_REVOKED: '{vc['id']}'")
    pub_b64=get_public_key_b64(issuer_did)
    if pub_b64 is None: return CredentialVerificationResult(valid=False,error=f"ISSUER_DID_NOT_FOUND: '{issuer_did}'")
    payload_bytes=_canonical_vc(vc).encode()
    try:
        raw_pub=base64.urlsafe_b64decode(pub_b64+"==")
        raw_sig=_b64url_decode(vc["proof"]["proofValue"])
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        Ed25519PublicKey.from_public_bytes(raw_pub).verify(raw_sig,payload_bytes)
    except Exception as e: return CredentialVerificationResult(valid=False,error=f"INVALID_VC_SIGNATURE: {type(e).__name__}")
    return CredentialVerificationResult(valid=True,subject_did=subject_did,
        allowed_purposes=subj.get("allowedPurposes",[]),operator_name=subj.get("operatorName",""),
        max_crawl_rate=subj.get("maxCrawlRate"))

def _canonical_vc(vc): return json.dumps({k:v for k,v in vc.items() if k!="proof"},sort_keys=True,separators=(",",":"),ensure_ascii=False)
