from __future__ import annotations
from enum import Enum
from typing import Optional
try:
    from pydantic import BaseModel, Field, field_validator
    HAS_PYDANTIC = True
except ImportError:
    from dataclasses import dataclass as BaseModel
    def Field(*a,**kw): return kw.get("default", None)
    def field_validator(*a,**kw): return lambda f: f
    HAS_PYDANTIC = False

class CrawlerPurpose(str, Enum):
    SEARCH_INDEXER = "SearchIndexer"
    RESEARCH       = "ResearchCrawler"
    AI_TRAINER     = "AITrainer"
    SECURITY_AUDIT = "SecurityAuditor"
    ARCHIVER       = "ArchiveCrawler"

class NegotiationStatus(str, Enum):
    INIT="INIT"; OFFERED="OFFERED"; COUNTERED="COUNTERED"
    AGREED="AGREED"; REJECTED="REJECTED"; EXPIRED="EXPIRED"

class RejectReason(str, Enum):
    PURPOSE_NOT_ALLOWED="PURPOSE_NOT_ALLOWED"; RATE_TOO_HIGH="RATE_TOO_HIGH"
    SCOPE_TOO_BROAD="SCOPE_TOO_BROAD"; NO_CREDENTIAL="NO_CREDENTIAL"
    MAX_ROUNDS_EXCEEDED="MAX_ROUNDS_EXCEEDED"; COUNTER_REJECTED="COUNTER_REJECTED"
    SESSION_EXPIRED="SESSION_EXPIRED"

if HAS_PYDANTIC:
    class PolicyManifest(BaseModel):
        server_did: str
        allowed_purposes: list[CrawlerPurpose]
        max_crawl_rate: int = Field(ge=1,le=600)
        allowed_paths: list[str] = ["/"]
        disallowed_paths: list[str] = ["/admin","/private"]
        data_use_restrictions: list[str] = ["no-ai-training","no-commercial-resale"]
        requires_credential: bool = False
        policy_expires_at: Optional[str] = None

    class IntentDeclaration(BaseModel):
        crawler_did: str
        declared_purpose: CrawlerPurpose
        requested_crawl_rate: int = Field(ge=1,le=600)
        requested_paths: list[str] = ["/"]
        operator_name: str
        operator_contact: str
        compliance_commitment: str = "Will respect agreed rate limits and scope."
        accepts_counter_offer: bool = True
        data_use_commitments: list[str] = ["no-ai-training","no-commercial-resale"]
        minimum_crawl_rate: Optional[int] = Field(default=None,ge=1,le=600)

        @field_validator("requested_paths")
        @classmethod
        def paths_must_start_with_slash(cls,v):
            for p in v:
                if not p.startswith("/"): raise ValueError(f"Path '{p}' must start with '/'")
            return v

    class CounterOfferResponse(BaseModel):
        session_id: str; accept: bool
        revised_crawl_rate: Optional[int] = Field(default=None,ge=1,le=600)
        revised_paths: Optional[list[str]] = None
        rejection_reason: Optional[str] = None

    class AccessToken(BaseModel):
        token_id: str; crawler_did: str; server_did: str
        agreed_purpose: CrawlerPurpose; agreed_crawl_rate: int
        agreed_paths: list[str]; data_use_restrictions: list[str]
        issued_at: str; expires_at: str
        signature: str = "PLACEHOLDER_SIGNATURE_WEEK3"

    class NegotiationRound(BaseModel):
        round_number: int; actor: str; action: str
        terms_offered: dict; outcome: NegotiationStatus; timestamp: str

    class NegotiationSession(BaseModel):
        session_id: str; crawler_did: str; operator_name: str
        status: NegotiationStatus; current_round: int = 0
        history: list[NegotiationRound] = []
        last_server_proposal: Optional[dict] = None
        access_token: Optional[AccessToken] = None
        opened_at: str; updated_at: str
        declared_purpose: Optional[str] = None
        crawler_minimum_rate: Optional[int] = None

    class CPNPInitRequest(BaseModel):
        crawler_did: str; operator_name: str; cpnp_version: str = "1.0"

    class NegotiationResponse(BaseModel):
        session_id: str; status: NegotiationStatus; round: int
        policy_manifest: Optional[PolicyManifest] = None
        access_token: Optional[AccessToken] = None
        counter_offer: Optional[dict] = None
        reject_reason: Optional[RejectReason] = None
        message: str = ""; history: list[NegotiationRound] = []
