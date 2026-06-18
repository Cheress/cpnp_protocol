from __future__ import annotations
import json, uuid, base64
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional
from ..identity.keys import KeyPair, _b64url, _b64url_decode

@dataclass
class TokenVerificationResult:
    valid: bool; error: str = ""; token_id: str = ""; crawler_did: str = ""
    agreed_purpose: str = ""; agreed_crawl_rate: int = 0
    agreed_paths: list = None; data_use_restrictions: list = None; expires_at: str = ""
    def __post_init__(self):
        if self.agreed_paths is None: self.agreed_paths=[]
        if self.data_use_restrictions is None: self.data_use_restrictions=[]

class TokenIssuer:
    HEADER = {"alg":"EdDSA","typ":"JWT"}
    def __init__(self, server_keypair: KeyPair):
        self._kp = server_keypair
        self._header_b64 = _b64url(json.dumps(self.HEADER,separators=(",",":")).encode())
    def issue(self, token) -> str:
        now = datetime.now(timezone.utc); exp = now+timedelta(hours=24)
        purpose = token.agreed_purpose.value if hasattr(token.agreed_purpose,"value") else str(token.agreed_purpose)
        payload = {"jti":token.token_id,"sub":token.crawler_did,"iss":token.server_did,
                   "iat":int(now.timestamp()),"exp":int(exp.timestamp()),
                   "purpose":purpose,"rate":token.agreed_crawl_rate,
                   "paths":token.agreed_paths,"restrictions":token.data_use_restrictions}
        p64 = _b64url(json.dumps(payload,separators=(",",":")).encode())
        sig  = self._kp.sign(f"{self._header_b64}.{p64}".encode("ascii"))
        return f"{self._header_b64}.{p64}.{sig}"
    def verify(self, jwt_str: str) -> TokenVerificationResult:
        parts = jwt_str.strip().split(".")
        if len(parts)!=3: return TokenVerificationResult(valid=False,error=f"MALFORMED_JWT: expected 3 parts, got {len(parts)}")
        h,p,s = parts
        try: hdr=json.loads(_b64url_decode(h))
        except: return TokenVerificationResult(valid=False,error="MALFORMED_JWT: cannot decode header")
        if hdr.get("alg")!="EdDSA": return TokenVerificationResult(valid=False,error=f"WRONG_ALGORITHM: expected EdDSA, got '{hdr.get('alg')}'")
        if not self._kp.verify(f"{h}.{p}".encode("ascii"),s): return TokenVerificationResult(valid=False,error="INVALID_SIGNATURE: JWT signature verification failed.")
        try: payload=json.loads(_b64url_decode(p))
        except: return TokenVerificationResult(valid=False,error="MALFORMED_JWT: cannot decode payload")
        now_ts=int(datetime.now(timezone.utc).timestamp())
        if now_ts>payload.get("exp",0):
            exp_at=datetime.fromtimestamp(payload["exp"],tz=timezone.utc).isoformat()
            return TokenVerificationResult(valid=False,error=f"TOKEN_EXPIRED: expired at {exp_at}.")
        if payload.get("iss")!=self._kp.did: return TokenVerificationResult(valid=False,error=f"WRONG_ISSUER: token from '{payload.get('iss')}', server is '{self._kp.did}'")
        exp_dt=datetime.fromtimestamp(payload.get("exp",0),tz=timezone.utc).isoformat()
        return TokenVerificationResult(valid=True,token_id=payload.get("jti",""),crawler_did=payload.get("sub",""),
            agreed_purpose=payload.get("purpose",""),agreed_crawl_rate=payload.get("rate",0),
            agreed_paths=payload.get("paths",[]),data_use_restrictions=payload.get("restrictions",[]),expires_at=exp_dt)
    def decode_unverified(self,jwt_str):
        try:
            parts=jwt_str.split(".")
            if len(parts)!=3: return None
            return json.loads(_b64url_decode(parts[1]))
        except: return None
