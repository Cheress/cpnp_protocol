"""
cpnp/app/server.py  —  WEEK 4: Dashboard + Polish
────────────────────────────────────────────────────
New in Week 4:
  • GET /status              — polling endpoint returning full live state as JSON
  • GET /dashboard           — the supervisor demo dashboard (single HTML page)
  • POST /cpnp/policy/update — change policy live without restarting server
  • POST /demo/crawl         — trigger a compliant or adversarial crawl from the UI
"""
from __future__ import annotations
import uuid, json, time, threading
from typing import Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .models import (PolicyManifest, IntentDeclaration, CounterOfferResponse,
    CPNPInitRequest, NegotiationResponse, NegotiationStatus,
    NegotiationSession, CrawlerPurpose, AccessToken, RejectReason)
from .negotiation import negotiate_intent, negotiate_response, _now
from .identity import (generate_keypair, build_did_document, register_did,
    resolve_did, DID_REGISTRY, verify_intent_signature,
    CredentialIssuer, verify_credential, register_trusted_ca)
from .enforcement import (TokenIssuer, AuditLog, CrawlRequestLog,
    CPNPEnforcementMiddleware, website_router)
import app as _app_pkg

# ══════════════════════════════════════════════════════════════════════════════
# BOOTSTRAP
# ══════════════════════════════════════════════════════════════════════════════
SERVER_KEYPAIR = generate_keypair("cpnp-server-jkuat")
register_did(build_did_document(SERVER_KEYPAIR,cpnp_endpoint="http://localhost:8000",
    operator_name="JKUAT CPNP Research Server",operator_contact="cheressbernard@gmail.com"))

TOKEN_ISSUER = TokenIssuer(SERVER_KEYPAIR)
_app_pkg._SERVER_ISSUER = TOKEN_ISSUER

CA = CredentialIssuer("cpnp-mock-ca")
register_trusted_ca(CA)

AUDIT = AuditLog("cpnp_audit.db")

# ══════════════════════════════════════════════════════════════════════════════
# MUTABLE POLICY (Week 4: can be changed live from dashboard)
# ══════════════════════════════════════════════════════════════════════════════
_policy_lock = threading.Lock()

def _make_policy(purposes=None, max_rate=30, allowed_paths=None,
                 disallowed_paths=None, requires_credential=True):
    return PolicyManifest(
        server_did=SERVER_KEYPAIR.did,
        allowed_purposes=purposes or [CrawlerPurpose.SEARCH_INDEXER,
                                       CrawlerPurpose.RESEARCH, CrawlerPurpose.ARCHIVER],
        max_crawl_rate=max_rate,
        allowed_paths=allowed_paths or ["/","/blog","/docs","/research"],
        disallowed_paths=disallowed_paths or ["/admin","/private","/user"],
        data_use_restrictions=["no-ai-training","no-commercial-resale"],
        requires_credential=requires_credential,
        policy_expires_at="2025-12-31T23:59:59Z"
    )

SERVER_POLICY = _make_policy()

# ══════════════════════════════════════════════════════════════════════════════
# APP
# ══════════════════════════════════════════════════════════════════════════════
application = FastAPI(
    title="CPNP — Crawl Policy Negotiation Protocol",
    description="Week 4 MVP with live dashboard",
    version="0.5.0-week4"
)
application.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["*"],allow_headers=["*"])
application.add_middleware(CPNPEnforcementMiddleware,issuer=TOKEN_ISSUER,audit=AUDIT)
application.include_router(website_router)
app = application

sessions: dict[str, NegotiationSession] = {}

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def _get_session(sid):
    if sid not in sessions: raise HTTPException(404,f"Session '{sid}' not found.")
    return sessions[sid]

def _verify_identity(intent):
    intent_dict = intent.model_dump(exclude={"proof","verifiable_credential"})
    if intent.proof:
        intent_dict["proof"] = intent.proof
        result = verify_intent_signature(intent_dict)
        if not result.valid: return f"SIGNATURE_FAILED: {result.error}"
    if SERVER_POLICY.requires_credential:
        if not intent.verifiable_credential:
            return "NO_CREDENTIAL: This server requires a Verifiable Credential. POST /identity/credential"
        vr = verify_credential(intent.verifiable_credential, CA)
        if not vr.valid: return f"CREDENTIAL_INVALID: {vr.error}"
        if vr.subject_did != intent.crawler_did: return f"CREDENTIAL_MISMATCH: VC for '{vr.subject_did}' used by '{intent.crawler_did}'"
        if intent.declared_purpose.value not in vr.allowed_purposes: return f"PURPOSE_NOT_IN_CREDENTIAL: '{intent.declared_purpose.value}' not in {vr.allowed_purposes}"
    return None

# ══════════════════════════════════════════════════════════════════════════════
# PYDANTIC REQUEST MODELS
# ══════════════════════════════════════════════════════════════════════════════
class RegisterDIDRequest(BaseModel):
    did_document: dict

class IssueCredentialRequest(BaseModel):
    subject_did: str; operator_name: str; operator_contact: str
    purposes: list[str]; max_crawl_rate: int = 60; validity_days: int = 30
    model_config = {"json_schema_extra":{"example":{
        "subject_did":"did:key:z6Mk...","operator_name":"JKUAT Research Lab",
        "operator_contact":"cheressbernard@gmail.com","purposes":["ResearchCrawler"],
        "max_crawl_rate":60,"validity_days":30}}}

class SignedIntentDeclaration(IntentDeclaration):
    proof: Optional[dict] = None
    verifiable_credential: Optional[dict] = None

class PolicyUpdateRequest(BaseModel):
    allowed_purposes: Optional[list[str]] = None
    max_crawl_rate: Optional[int] = None
    allowed_paths: Optional[list[str]] = None
    requires_credential: Optional[bool] = None
    model_config = {"json_schema_extra":{"example":{
        "allowed_purposes":["ResearchCrawler","SearchIndexer"],
        "max_crawl_rate":15,"allowed_paths":["/","/blog"],"requires_credential":False}}}

class DemoCrawlRequest(BaseModel):
    mode: str = "compliant"   # "compliant" | "no_token" | "forged" | "path_violation"
    target_path: str = "/site/blog"

# ══════════════════════════════════════════════════════════════════════════════
# WEEK 4 — STATUS POLLING ENDPOINT
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/status", tags=["Week 4 — Dashboard"],
         summary="Live system state — poll this every 2s for dashboard")
def get_status():
    """
    Returns the full live state of the CPNP system as a single JSON object.
    The dashboard polls this every 2 seconds.

    Includes: server identity, active policy, session stats,
    recent audit events, per-verdict counts, and recent crawl history.
    """
    audit_summary = AUDIT.summary()
    recent = AUDIT.recent_events(limit=30)

    session_stats = {"total":0,"agreed":0,"rejected":0,"countered":0,"init":0}
    for s in sessions.values():
        session_stats["total"]+=1
        k = s.status.value.lower()
        if k in session_stats: session_stats[k]+=1

    active_sessions = [
        {"session_id":sid[:12]+"...", "operator":s.operator_name,
         "status":s.status.value, "round":s.current_round,
         "has_token":s.access_token is not None,
         "purpose":s.declared_purpose or "unknown",
         "opened_at":s.opened_at}
        for sid,s in list(sessions.items())[-10:]
    ]

    return {
        "timestamp": _now(),
        "server": {
            "did": SERVER_KEYPAIR.did,
            "did_short": SERVER_KEYPAIR.did[:28]+"...",
            "ca_did": CA.did[:28]+"...",
            "credentials_issued": CA.issued_count(),
            "registered_dids": len(DID_REGISTRY),
        },
        "policy": {
            "allowed_purposes": [p.value for p in SERVER_POLICY.allowed_purposes],
            "max_crawl_rate": SERVER_POLICY.max_crawl_rate,
            "allowed_paths": SERVER_POLICY.allowed_paths,
            "disallowed_paths": SERVER_POLICY.disallowed_paths,
            "requires_credential": SERVER_POLICY.requires_credential,
            "data_use_restrictions": SERVER_POLICY.data_use_restrictions,
        },
        "sessions": session_stats,
        "active_sessions": active_sessions,
        "audit": {
            "total_requests": audit_summary["total_requests"],
            "compliant": audit_summary["compliant_requests"],
            "blocked": audit_summary["blocked_requests"],
            "compliance_rate": audit_summary["compliance_rate_pct"],
            "by_verdict": audit_summary["by_verdict"],
        },
        "recent_events": recent,
    }

# ══════════════════════════════════════════════════════════════════════════════
# WEEK 4 — CHANGE POLICY LIVE
# ══════════════════════════════════════════════════════════════════════════════
@app.post("/cpnp/policy/update", tags=["Week 4 — Dashboard"],
          summary="Change server policy live (no restart needed)")
def update_policy(req: PolicyUpdateRequest):
    """
    Changes the server's Policy Manifest without restarting.
    Used by the dashboard's Change Policy panel.

    Existing tokens are still valid — only new negotiations use the updated policy.
    """
    global SERVER_POLICY
    with _policy_lock:
        purposes = [CrawlerPurpose(p) for p in req.allowed_purposes] if req.allowed_purposes else SERVER_POLICY.allowed_purposes
        SERVER_POLICY = _make_policy(
            purposes=purposes,
            max_rate=req.max_crawl_rate or SERVER_POLICY.max_crawl_rate,
            allowed_paths=req.allowed_paths or SERVER_POLICY.allowed_paths,
            requires_credential=req.requires_credential if req.requires_credential is not None else SERVER_POLICY.requires_credential,
        )
    return {"message":"Policy updated.","new_policy":{
        "allowed_purposes":[p.value for p in SERVER_POLICY.allowed_purposes],
        "max_crawl_rate":SERVER_POLICY.max_crawl_rate,
        "allowed_paths":SERVER_POLICY.allowed_paths,
        "requires_credential":SERVER_POLICY.requires_credential}}

# ══════════════════════════════════════════════════════════════════════════════
# WEEK 4 — DEMO CRAWL TRIGGER (used by dashboard buttons)
# ══════════════════════════════════════════════════════════════════════════════
@app.post("/demo/crawl", tags=["Week 4 — Dashboard"],
          summary="Trigger a demo crawl from the dashboard")
def demo_crawl(req: DemoCrawlRequest):
    """
    Simulates a crawl request so you can see audit log entries appear live.
    Mode: compliant | no_token | forged | path_violation
    """
    import os, base64
    path = req.target_path
    url  = f"http://localhost:8000{path}"

    if req.mode == "no_token":
        AUDIT.record_request(CrawlRequestLog(
            crawler_did="did:key:demo-adversarial", token_id="",
            method="GET", url=url, path=path.replace("/site","") or "/",
            status_code=451, verdict="BLOCKED_NO_TOKEN",
            violation_detail="No CPNP-Token header. Demo adversarial crawl."))
        return {"verdict":"BLOCKED_NO_TOKEN","status":451}

    elif req.mode == "forged":
        AUDIT.record_request(CrawlRequestLog(
            crawler_did="did:key:demo-adversarial", token_id="forged-demo",
            method="GET", url=url, path=path.replace("/site","") or "/",
            status_code=451, verdict="BLOCKED_FORGED",
            violation_detail="INVALID_SIGNATURE: forged JWT. Demo adversarial crawl."))
        return {"verdict":"BLOCKED_FORGED","status":451}

    elif req.mode == "path_violation":
        AUDIT.record_request(CrawlRequestLog(
            crawler_did="did:key:demo-adversarial", token_id="tok-path-viol",
            method="GET", url="http://localhost:8000/site/admin", path="/admin",
            status_code=451, verdict="BLOCKED_PATH_VIOLATION",
            violation_detail="Path '/admin' not in agreed paths ['/','/blog']. Demo."))
        return {"verdict":"BLOCKED_PATH_VIOLATION","status":451}

    else:  # compliant
        AUDIT.record_request(CrawlRequestLog(
            crawler_did="did:key:demo-compliant-crawler", token_id="tok-demo-compliant",
            method="GET", url=url, path=path.replace("/site","") or "/",
            status_code=200, verdict="COMPLIANT",
            agreed_rate=20, agreed_paths=["/","/blog","/research"], purpose="ResearchCrawler"))
        return {"verdict":"COMPLIANT","status":200}

# ══════════════════════════════════════════════════════════════════════════════
# ROOT + DASHBOARD REDIRECT
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def root():
    s = AUDIT.summary()
    agreed   = sum(1 for x in sessions.values() if x.status==NegotiationStatus.AGREED)
    rejected = sum(1 for x in sessions.values() if x.status==NegotiationStatus.REJECTED)
    return f"""<html><body style="font-family:monospace;padding:2rem;background:#0d1117;color:#e6edf3">
<h2 style="color:#58a6ff">🤝 CPNP Server — Week 4</h2>
<table border=1 cellpadding=8 style="border-collapse:collapse;border-color:#30363d;margin-bottom:1rem">
<tr><td>Sessions AGREED/REJECTED</td><td><b style="color:#3fb950">{agreed}</b> / <b style="color:#f85149">{rejected}</b></td></tr>
<tr><td>Total crawl requests</td><td><b>{s['total_requests']}</b></td></tr>
<tr><td>Compliance rate</td><td><b>{s['compliance_rate_pct']}%</b></td></tr>
</table>
<a href="/dashboard" style="background:#238636;color:#fff;padding:.6rem 1.2rem;border-radius:6px;text-decoration:none;font-weight:bold">📊 Open Dashboard</a>
&nbsp;&nbsp;<a href="/docs" style="color:#58a6ff">API Docs</a>
&nbsp;&nbsp;<a href="/site/" style="color:#58a6ff">Test Website</a>
</body></html>"""

# ══════════════════════════════════════════════════════════════════════════════
# IDENTITY ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════
@app.post("/identity/register",tags=["Identity"])
def register_crawler_did(req: RegisterDIDRequest):
    doc=req.did_document; did=doc.get("id","")
    if not did.startswith("did:"): raise HTTPException(400,"DID must start with 'did:'")
    register_did(doc); return {"registered":did}

@app.post("/identity/credential",tags=["Identity"],summary="Issue Verifiable Credential")
def issue_credential(req: IssueCredentialRequest):
    if not resolve_did(req.subject_did): raise HTTPException(400,f"DID '{req.subject_did}' not registered.")
    vc=CA.issue(subject_did=req.subject_did,operator_name=req.operator_name,
        operator_contact=req.operator_contact,purposes=req.purposes,
        max_crawl_rate=req.max_crawl_rate,validity_days=req.validity_days)
    return {"verifiable_credential":vc,"message":f"VC issued. Valid {req.validity_days} days."}

@app.get("/identity/did/{did_suffix:path}",tags=["Identity"])
def resolve_did_ep(did_suffix):
    did=did_suffix if did_suffix.startswith("did:") else f"did:key:{did_suffix}"
    doc=resolve_did(did)
    if not doc: raise HTTPException(404,f"DID '{did}' not found.")
    return doc

@app.get("/identity/ca",tags=["Identity"])
def ca_info(): return {"ca_did":CA.did,"credentials_issued":CA.issued_count()}

# ══════════════════════════════════════════════════════════════════════════════
# CPNP HANDSHAKE ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════
@app.post("/cpnp/init",response_model=NegotiationResponse,tags=["CPNP Handshake"])
def cpnp_init(request: CPNPInitRequest):
    sid=str(uuid.uuid4()); now=_now()
    sessions[sid]=NegotiationSession(session_id=sid,crawler_did=request.crawler_did,
        operator_name=request.operator_name,status=NegotiationStatus.INIT,opened_at=now,updated_at=now)
    AUDIT.record_negotiation(sid,"INIT",request.crawler_did,request.operator_name)
    return NegotiationResponse(session_id=sid,status=NegotiationStatus.INIT,round=0,
        message=f"Session opened for '{request.operator_name}'.")

@app.get("/cpnp/policy",response_model=PolicyManifest,tags=["CPNP Handshake"])
def get_policy(): return SERVER_POLICY

@app.post("/cpnp/negotiate",response_model=NegotiationResponse,tags=["CPNP Handshake"])
def cpnp_negotiate(session_id: str, intent: SignedIntentDeclaration):
    session=_get_session(session_id)
    if session.status in (NegotiationStatus.AGREED,NegotiationStatus.REJECTED):
        return NegotiationResponse(session_id=session_id,status=session.status,
            round=session.current_round,access_token=session.access_token,
            history=session.history,message=f"Session already {session.status}.")
    err=_verify_identity(intent)
    if err:
        session.status=NegotiationStatus.REJECTED
        AUDIT.record_negotiation(session_id,"REJECTED",intent.crawler_did,intent.operator_name,{"reason":err})
        return NegotiationResponse(session_id=session_id,status=NegotiationStatus.REJECTED,
            round=session.current_round,reject_reason=RejectReason.NO_CREDENTIAL,message=f"❌ IDENTITY CHECK FAILED: {err}")
    base_intent=IntentDeclaration(**{k:v for k,v in intent.model_dump().items() if k in IntentDeclaration.model_fields})
    result=negotiate_intent(session,SERVER_POLICY,base_intent)
    if result.status==NegotiationStatus.AGREED:
        AUDIT.record_negotiation(session_id,"AGREED",intent.crawler_did,intent.operator_name,
            {"token_id":result.access_token.token_id if result.access_token else "","rate":result.access_token.agreed_crawl_rate if result.access_token else 0})
    elif result.status==NegotiationStatus.REJECTED:
        AUDIT.record_negotiation(session_id,"REJECTED",intent.crawler_did,intent.operator_name,{"reason":result.message})
    return result

@app.post("/cpnp/negotiate/respond",response_model=NegotiationResponse,tags=["CPNP Handshake"])
def cpnp_respond(response: CounterOfferResponse):
    session=_get_session(response.session_id)
    if session.status!=NegotiationStatus.COUNTERED:
        return NegotiationResponse(session_id=response.session_id,status=session.status,
            round=session.current_round,history=session.history,message=f"Session is '{session.status}'.")
    return negotiate_response(session,SERVER_POLICY,response)

# ══════════════════════════════════════════════════════════════════════════════
# AUDIT ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/audit/summary",tags=["Audit Log"])
def audit_summary(): return AUDIT.summary()
@app.get("/audit/blocked",tags=["Audit Log"])
def audit_blocked(limit:int=50): return {"blocked":AUDIT.blocked_requests(limit)}
@app.get("/audit/compliant",tags=["Audit Log"])
def audit_compliant(limit:int=50): return {"compliant":AUDIT.compliant_requests(limit)}
@app.get("/audit/crawler/{crawler_did:path}",tags=["Audit Log"])
def audit_crawler(crawler_did:str): return AUDIT.compliance_report(crawler_did)
@app.get("/audit/sql-queries",tags=["Audit Log"])
def audit_sql(): return {"sql_queries":AUDIT.export_sql_queries(),"db_file":AUDIT.db_path}

# ══════════════════════════════════════════════════════════════════════════════
# INSPECTION
# ══════════════════════════════════════════════════════════════════════════════
@app.get("/cpnp/sessions",tags=["Inspection"])
def list_sessions():
    return {"total":len(sessions),"sessions":[
        {"session_id":sid,"operator":s.operator_name,"status":s.status,
         "rounds":s.current_round,"has_token":s.access_token is not None}
        for sid,s in sessions.items()]}
@app.delete("/cpnp/sessions",tags=["Inspection"])
def clear_sessions(): sessions.clear(); return {"message":"All sessions cleared."}
@app.get("/health",tags=["Inspection"])
def health(): return {"status":"ok","server_did":SERVER_KEYPAIR.did}

# ── Dashboard (Week 4) ─────────────────────────────────────────────────────
from .dashboard import router as dashboard_router
app.include_router(dashboard_router)
