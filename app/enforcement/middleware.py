from __future__ import annotations
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from .tokens import TokenIssuer, TokenVerificationResult
from .audit  import AuditLog, CrawlRequestLog

CPNP_TOKEN_HEADER = "cpnp-token"
NEGOTIATE_URL     = "http://localhost:8000/cpnp/init"
EXEMPT_PREFIXES   = ["/cpnp/","/identity/","/docs","/openapi","/redoc","/favicon","/health","/audit","/status"]

def _path_in_scope(lp,agreed):
    for ap in agreed:
        if ap=="/" and lp=="/": return True
        if ap!="/" and (lp==ap or lp.startswith(ap+"/") or lp.startswith(ap)): return True
    return False

class CPNPEnforcementMiddleware(BaseHTTPMiddleware):
    def __init__(self,app: ASGIApp,issuer: TokenIssuer,audit: AuditLog):
        super().__init__(app); self.issuer=issuer; self.audit=audit
    async def dispatch(self,request,call_next):
        path=request.url.path
        if any(path.startswith(p) for p in EXEMPT_PREFIXES) or path=="/":
            return await call_next(request)
        if not path.startswith("/site"):
            return await call_next(request)
        url=str(request.url); method=request.method
        jwt_str=request.headers.get(CPNP_TOKEN_HEADER,"").strip()
        if not jwt_str:
            return self._block(path,url,method,"BLOCKED_NO_TOKEN",
                "No CPNP-Token header. Negotiate at POST /cpnp/init before crawling.","unknown","")
        vr=self.issuer.verify(jwt_str)
        if not vr.valid:
            verdict="BLOCKED_FORGED"
            if "EXPIRED" in vr.error: verdict="BLOCKED_EXPIRED"
            elif "WRONG_ISSUER" in vr.error: verdict="BLOCKED_WRONG_ISSUER"
            unverified=self.issuer.decode_unverified(jwt_str) or {}
            return self._block(path,url,method,verdict,vr.error,
                unverified.get("sub","unknown"),unverified.get("jti",""),vr=None)
        lp=path.removeprefix("/site") or "/"
        if not _path_in_scope(lp,vr.agreed_paths):
            return self._block(path,url,method,"BLOCKED_PATH_VIOLATION",
                f"Path '{lp}' not in agreed paths {vr.agreed_paths}.",vr.crawler_did,vr.token_id,vr=vr)
        self.audit.record_request(CrawlRequestLog(
            crawler_did=vr.crawler_did,token_id=vr.token_id,method=method,url=url,path=lp,
            status_code=200,verdict="COMPLIANT",agreed_rate=vr.agreed_crawl_rate,
            agreed_paths=vr.agreed_paths,purpose=vr.agreed_purpose))
        response=await call_next(request)
        response.headers["CPNP-Verdict"]="COMPLIANT"
        response.headers["CPNP-Token-ID"]=vr.token_id
        return response
    def _block(self,path,url,method,verdict,detail,crawler_did,token_id,vr=None):
        lp=path.removeprefix("/site") or "/"
        self.audit.record_request(CrawlRequestLog(
            crawler_did=crawler_did,token_id=token_id,method=method,url=url,path=lp,
            status_code=451,verdict=verdict,violation_detail=detail,
            agreed_rate=vr.agreed_crawl_rate if vr else 0,
            agreed_paths=vr.agreed_paths if vr else [],purpose=vr.agreed_purpose if vr else ""))
        return JSONResponse(
            content={"cpnp_version":"1.0","verdict":verdict,"detail":detail,
                     "blocked_path":lp,"negotiate_at":NEGOTIATE_URL,"token_id":token_id or None,
                     "how_to_fix":"POST /cpnp/init → GET /cpnp/policy → POST /cpnp/negotiate → add CPNP-Token header"},
            status_code=451,headers={"CPNP-Verdict":verdict,"CPNP-Negotiate":NEGOTIATE_URL})
