from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Optional
from .keys import KeyPair

DID_REGISTRY: dict[str, dict] = {}

def build_did_document(kp: KeyPair, cpnp_endpoint=None, purposes=None, operator_name=None, operator_contact=None) -> dict:
    did = kp.did; key_id = f"{did}#key-1"
    doc = {
        "@context": ["https://www.w3.org/ns/did/v1","https://w3id.org/security/suites/ed25519-2020/v1"],
        "id": did, "created": datetime.now(timezone.utc).isoformat(),
        "verificationMethod": [{"id":key_id,"type":"Ed25519VerificationKey2020","controller":did,"publicKeyMultibase":f"z{_b58_from_did(did)}"}],
        "authentication": [key_id], "assertionMethod": [key_id], "service": []
    }
    if cpnp_endpoint:
        doc["service"].append({"id":f"{did}#cpnp","type":"CPNPNegotiationEndpoint",
            "serviceEndpoint":{"uri":cpnp_endpoint,"protocol":"CPNP/1.0"}})
    meta = {}
    if purposes: meta["declaredPurposes"] = purposes
    if operator_name: meta["operatorName"] = operator_name
    if operator_contact: meta["operatorContact"] = operator_contact
    if meta: meta["specVersion"]="CPNP/1.0"; doc["cpnpMetadata"]=meta
    return doc

def register_did(doc: dict) -> str:
    did = doc["id"]; DID_REGISTRY[did] = doc; return did

def resolve_did(did: str) -> Optional[dict]:
    return DID_REGISTRY.get(did)

def get_public_key_b64(did: str) -> Optional[str]:
    doc = resolve_did(did)
    if not doc: return None
    methods = doc.get("verificationMethod",[])
    if not methods: return None
    mb = methods[0].get("publicKeyMultibase","")
    if not mb.startswith("z"): return None
    raw = _b58_decode(mb[1:])
    if len(raw)<34: return None
    import base64
    return base64.urlsafe_b64encode(raw[2:]).rstrip(b"=").decode()

def did_document_to_json(doc, indent=2): return json.dumps(doc,indent=indent)

def _b58_from_did(did): return did.split("did:key:z")[-1]

def _b58_decode(s):
    A = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    n = 0
    for c in s: n=n*58+A.index(c)
    r=[]
    while n: n,rem=divmod(n,256); r.append(rem)
    for c in s:
        if c==A[0]: r.append(0)
        else: break
    return bytes(reversed(r))
