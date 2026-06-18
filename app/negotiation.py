from __future__ import annotations
import uuid
from datetime import datetime, timedelta
from .models import (PolicyManifest,IntentDeclaration,CounterOfferResponse,
    AccessToken,NegotiationSession,NegotiationRound,NegotiationStatus,
    RejectReason,NegotiationResponse,CrawlerPurpose)

MAX_ROUNDS=5; CONCESSION_STEP=2

def negotiate_intent(session,policy,intent):
    if session.status in (NegotiationStatus.AGREED,NegotiationStatus.REJECTED): return _terminal_guard(session)
    session.current_round+=1; rn=session.current_round
    session.declared_purpose=intent.declared_purpose.value
    session.crawler_minimum_rate=intent.minimum_crawl_rate
    if intent.declared_purpose not in policy.allowed_purposes:
        _record(session,"CRAWLER","INTENT_DECLARATION",_is(intent),NegotiationStatus.REJECTED)
        return _reject(session,RejectReason.PURPOSE_NOT_ALLOWED,f"Purpose '{intent.declared_purpose.value}' not permitted. Allowed: {[p.value for p in policy.allowed_purposes]}")
    missing=[r for r in policy.data_use_restrictions if r not in intent.data_use_commitments]
    if missing:
        _record(session,"CRAWLER","INTENT_DECLARATION",_is(intent),NegotiationStatus.REJECTED)
        return _reject(session,RejectReason.PURPOSE_NOT_ALLOWED,f"Missing data-use commitments: {missing}")
    score,issues,proposal=_score(policy,intent.requested_crawl_rate,intent.requested_paths,rn)
    _record(session,"CRAWLER","INTENT_DECLARATION",_is(intent),NegotiationStatus.AGREED if score==1.0 else NegotiationStatus.COUNTERED)
    if score==1.0: return _agree(session,policy,intent.declared_purpose,proposal["crawl_rate"],proposal["paths"])
    if not intent.accepts_counter_offer: return _reject(session,RejectReason.COUNTER_REJECTED,"Crawler set accepts_counter_offer=False.")
    if rn>=MAX_ROUNDS: return _reject(session,RejectReason.MAX_ROUNDS_EXCEEDED,f"Max rounds ({MAX_ROUNDS}) reached.")
    if intent.minimum_crawl_rate and proposal["crawl_rate"]<intent.minimum_crawl_rate:
        return _reject(session,RejectReason.RATE_TOO_HIGH,f"Server best offer ({proposal['crawl_rate']}) < crawler minimum ({intent.minimum_crawl_rate}).")
    return _issue_counter(session,policy,issues,proposal,rn)

def negotiate_response(session,policy,response):
    if session.status in (NegotiationStatus.AGREED,NegotiationStatus.REJECTED): return _terminal_guard(session)
    if session.status!=NegotiationStatus.COUNTERED:
        return NegotiationResponse(session_id=session.session_id,status=session.status,round=session.current_round,history=session.history,message=f"Session is '{session.status}'. Nothing to respond to.")
    session.current_round+=1; rn=session.current_round; last=session.last_server_proposal or {}
    if response.accept:
        _record(session,"CRAWLER","ACCEPT",{"accepted":last},NegotiationStatus.AGREED)
        return _agree(session,policy,_session_purpose(session),last.get("crawl_rate",policy.max_crawl_rate),last.get("paths",policy.allowed_paths))
    if not response.revised_crawl_rate and not response.revised_paths:
        _record(session,"CRAWLER","REJECT",{"reason":response.rejection_reason},NegotiationStatus.REJECTED)
        return _reject(session,RejectReason.COUNTER_REJECTED,f"Crawler rejected. Reason: {response.rejection_reason or 'not stated'}")
    if _is_deadlock(session,response): return _reject(session,RejectReason.MAX_ROUNDS_EXCEEDED,"Deadlock: identical terms repeated.")
    rev_rate=response.revised_crawl_rate or last.get("crawl_rate",policy.max_crawl_rate)
    rev_paths=response.revised_paths or last.get("paths",policy.allowed_paths)
    _record(session,"CRAWLER","REVISED_OFFER",{"crawl_rate":rev_rate,"paths":rev_paths},NegotiationStatus.COUNTERED)
    score,issues,proposal=_score(policy,rev_rate,rev_paths,rn)
    if score==1.0: return _agree(session,policy,_session_purpose(session),proposal["crawl_rate"],proposal["paths"])
    if rn>=MAX_ROUNDS: return _reject(session,RejectReason.MAX_ROUNDS_EXCEEDED,f"Max rounds ({MAX_ROUNDS}) reached.")
    conceded=min(last.get("crawl_rate",policy.max_crawl_rate)+CONCESSION_STEP,policy.max_crawl_rate)
    proposal["crawl_rate"]=min(max(proposal["crawl_rate"],conceded),policy.max_crawl_rate)
    min_rate=session.crawler_minimum_rate
    if min_rate and proposal["crawl_rate"]<min_rate: return _reject(session,RejectReason.RATE_TOO_HIGH,f"Server best offer below crawler minimum ({min_rate}).")
    return _issue_counter(session,policy,issues,proposal,rn)

def _score(policy,rate,paths,rn):
    score=1.0; issues=[]; agreed_rate=rate; agreed_paths=[]; blocked=[]
    if rate>policy.max_crawl_rate: score-=0.50; agreed_rate=policy.max_crawl_rate; issues.append(f"Rate {rate} > max {policy.max_crawl_rate}")
    for p in paths:
        ok=any(p.startswith(ap) for ap in policy.allowed_paths)
        bad=any(p.startswith(dp) for dp in policy.disallowed_paths)
        (blocked if (bad or not ok) else agreed_paths).append(p)
    if blocked: score-=0.50*(len(blocked)/max(len(paths),1)); issues.append(f"Blocked paths: {blocked}")
    if not agreed_paths: agreed_paths=policy.allowed_paths
    return max(0.0,round(score,4)),issues,{"crawl_rate":agreed_rate,"paths":agreed_paths,"data_use_restrictions":policy.data_use_restrictions,"compatibility_score":round(max(0.0,score),4)}

def _issue_counter(session,policy,issues,proposal,rn):
    session.last_server_proposal=proposal; session.status=NegotiationStatus.COUNTERED
    _record(session,"SERVER","COUNTER_OFFER",proposal,NegotiationStatus.COUNTERED)
    return NegotiationResponse(session_id=session.session_id,status=NegotiationStatus.COUNTERED,round=rn,
        counter_offer={"compatibility_score":proposal.get("compatibility_score",0),"issues_found":issues,
            "server_proposal":{"crawl_rate":proposal["crawl_rate"],"paths":proposal["paths"],"data_use_restrictions":proposal["data_use_restrictions"]},
            "rounds_remaining":MAX_ROUNDS-rn,"how_to_respond":"POST /cpnp/negotiate/respond — accept=true or revised_crawl_rate+revised_paths"},
        history=session.history,message=f"Round {rn}/{MAX_ROUNDS} · score={proposal.get('compatibility_score',0):.2f} · {len(issues)} issue(s) · {MAX_ROUNDS-rn} rounds left")

def _agree(session,policy,purpose,rate,paths):
    token=_mint_token(policy,session.crawler_did,purpose,rate,paths)
    session.access_token=token; session.status=NegotiationStatus.AGREED; session.updated_at=_now()
    _record(session,"SERVER","AGREEMENT_REACHED",{"token_id":token.token_id,"rate":rate,"paths":paths},NegotiationStatus.AGREED)
    return NegotiationResponse(session_id=session.session_id,status=NegotiationStatus.AGREED,round=session.current_round,
        access_token=token,history=session.history,
        message=f"✅ AGREED in {session.current_round} round(s). Token: {token.token_id[:12]}... · Rate: {rate} req/min · Paths: {paths}")

def _reject(session,reason,message):
    session.status=NegotiationStatus.REJECTED; session.updated_at=_now()
    _record(session,"SERVER","REJECTED",{"reason":reason.value,"message":message},NegotiationStatus.REJECTED)
    return NegotiationResponse(session_id=session.session_id,status=NegotiationStatus.REJECTED,round=session.current_round,reject_reason=reason,history=session.history,message=f"❌ {message}")

def _terminal_guard(session):
    return NegotiationResponse(session_id=session.session_id,status=session.status,round=session.current_round,access_token=session.access_token,history=session.history,message=f"Session already {session.status}.")

def _is_deadlock(session,response):
    for h in reversed(session.history):
        if h.actor=="CRAWLER":
            return h.terms_offered.get("crawl_rate")==response.revised_crawl_rate and h.terms_offered.get("paths")==response.revised_paths
    return False

def _record(session,actor,action,terms,outcome):
    session.history.append(NegotiationRound(round_number=session.current_round,actor=actor,action=action,terms_offered=terms,outcome=outcome,timestamp=_now()))
    session.updated_at=_now()

def _session_purpose(session):
    try: return CrawlerPurpose(session.declared_purpose)
    except: return CrawlerPurpose.RESEARCH

def _is(intent): return {"declared_purpose":intent.declared_purpose.value,"requested_crawl_rate":intent.requested_crawl_rate,"requested_paths":intent.requested_paths}

def _mint_token(policy,crawler_did,purpose,agreed_rate,agreed_paths):
    now=datetime.utcnow()
    token=AccessToken(token_id=str(uuid.uuid4()),crawler_did=crawler_did,server_did=policy.server_did,
        agreed_purpose=purpose,agreed_crawl_rate=agreed_rate,agreed_paths=agreed_paths,
        data_use_restrictions=policy.data_use_restrictions,
        issued_at=now.isoformat()+"Z",expires_at=(now+timedelta(hours=24)).isoformat()+"Z")
    try:
        import app as _app_pkg
        if _app_pkg._SERVER_ISSUER is not None: token.signature=_app_pkg._SERVER_ISSUER.issue(token)
    except Exception: pass
    return token

def _now(): return datetime.utcnow().isoformat()+"Z"
