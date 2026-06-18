from __future__ import annotations
import os, base64, json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import (
    Encoding, PublicFormat, PrivateFormat, NoEncryption,
    load_pem_private_key, load_pem_public_key)

@dataclass
class KeyPair:
    name: str
    private_key: Ed25519PrivateKey
    public_key: Ed25519PublicKey
    public_b64: str
    did: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def sign(self, data: bytes) -> str:
        return _b64url(self.private_key.sign(data))

    def verify(self, data: bytes, signature_b64: str) -> bool:
        try:
            self.public_key.verify(_b64url_decode(signature_b64), data)
            return True
        except Exception:
            return False

    def public_bytes(self) -> bytes:
        return self.public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)

def generate_keypair(name: str) -> KeyPair:
    priv = Ed25519PrivateKey.generate()
    pub  = priv.public_key()
    pb   = pub.public_bytes(Encoding.Raw, PublicFormat.Raw)
    return KeyPair(name=name, private_key=priv, public_key=pub,
                   public_b64=_b64url(pb), did=_derive_did(pb))

def save_keypair(kp: KeyPair, directory: str = "./keys") -> dict:
    os.makedirs(directory, exist_ok=True)
    pp = os.path.join(directory, f"{kp.name}.private.pem")
    qp = os.path.join(directory, f"{kp.name}.public.pem")
    mp = os.path.join(directory, f"{kp.name}.meta.json")
    with open(pp,"wb") as f: f.write(kp.private_key.private_bytes(Encoding.PEM,PrivateFormat.PKCS8,NoEncryption()))
    with open(qp,"wb") as f: f.write(kp.public_key.public_bytes(Encoding.PEM,PublicFormat.SubjectPublicKeyInfo))
    with open(mp,"w") as f: json.dump({"name":kp.name,"did":kp.did,"public_b64":kp.public_b64,"created_at":kp.created_at},f,indent=2)
    return {"private":pp,"public":qp,"meta":mp}

def load_keypair(name: str, directory: str = "./keys") -> KeyPair:
    with open(os.path.join(directory,f"{name}.private.pem"),"rb") as f: priv=load_pem_private_key(f.read(),password=None)
    with open(os.path.join(directory,f"{name}.public.pem"),"rb") as f: pub=load_pem_public_key(f.read())
    with open(os.path.join(directory,f"{name}.meta.json")) as f: meta=json.load(f)
    pb = pub.public_bytes(Encoding.Raw, PublicFormat.Raw)
    return KeyPair(name=name,private_key=priv,public_key=pub,public_b64=_b64url(pb),did=meta["did"],created_at=meta["created_at"])

def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def _b64url_decode(s: str) -> bytes:
    p = 4 - len(s)%4
    if p!=4: s += "="*p
    return base64.urlsafe_b64decode(s)

def _derive_did(pub_bytes: bytes) -> str:
    prefixed = bytes([0xed,0x01]) + pub_bytes
    return f"did:key:z{_base58_encode(prefixed)}"

def _base58_encode(data: bytes) -> str:
    A = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    n = int.from_bytes(data,"big"); r=[]
    while n: n,rem=divmod(n,58); r.append(A[rem])
    for b in data:
        if b==0: r.append(A[0])
        else: break
    return "".join(reversed(r))
