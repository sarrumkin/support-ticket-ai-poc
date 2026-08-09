from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FailureCode(StrEnum):
    PII_UNCERTAIN = "pii_uncertain"
    LOW_CONFIDENCE = "low_confidence"
    RETRIEVAL_MISS = "retrieval_miss"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    INVALID_OUTPUT = "invalid_output"
    SAFETY_FAILED = "safety_failed"


class ProcessingOutcome(StrEnum):
    AUTO_REPLY = "auto_reply"
    OPERATOR_REVIEW_WITH_DRAFT = "operator_review_with_draft"
    HUMAN_REVIEW_WITHOUT_DRAFT = "human_review_without_draft"


class AnswerOrigin(StrEnum):
    APPROVED_EXACT = "approved_exact"
    APPROVED_SEMANTIC = "approved_semantic"
    MISS = "miss"


class ComponentRef(StrictModel):
    provider: str
    implementation: str
    model: str | None = None
    version: str


class TicketInput(StrictModel):
    ticket_id: str = Field(min_length=1)
    content: str = Field(min_length=1)
    locale: str = "ru"
    incident_id: str | None = None


class PIIRedactionResult(StrictModel):
    redacted_text: str
    findings: list[str] = Field(default_factory=list)
    residual_risk: bool = False
    external_processing_allowed: bool = True
    component: ComponentRef


class RiskAssessment(StrictModel):
    risky: bool
    labels: list[str] = Field(default_factory=list)
    component: ComponentRef


class IntentPrediction(StrictModel):
    intent: str
    confidence: float = Field(ge=0.0, le=1.0)
    abstained: bool
    component: ComponentRef


class Evidence(StrictModel):
    evidence_id: str
    content: str = Field(min_length=1)
    source_ref: str


class ResolutionResult(StrictModel):
    origin: AnswerOrigin
    content: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence: list[Evidence] = Field(default_factory=list)
    component: ComponentRef


class GenerationRequest(StrictModel):
    redacted_ticket: str = Field(min_length=1)
    intent: str
    locale: str
    evidence: list[Evidence] = Field(min_length=1)


class GeneratedDraft(StrictModel):
    content: str = Field(min_length=1)
    evidence_refs: list[str] = Field(min_length=1)
    component: ComponentRef


class ValidationResult(StrictModel):
    valid: bool
    failure: FailureCode | None = None
    component: ComponentRef


class AuditRecord(StrictModel):
    stage: str
    action: str
    reason_codes: list[str] = Field(default_factory=list)
    component: ComponentRef


class ProcessingResult(StrictModel):
    ticket_id: str
    outcome: ProcessingOutcome
    route_reason: str
    redacted_text: str
    dedup_key: str
    intent: str | None = None
    intent_confidence: float | None = None
    answer: str | None = None
    draft: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    audit: list[AuditRecord]


class KnowledgeEntry(StrictModel):
    evidence_id: str
    locale: str
    content: str
    approved_answer: str | None = None
    source_ref: str
    exact_queries: list[str] = Field(default_factory=list)
    auto_reply_eligible: bool = False
