from __future__ import annotations

import hashlib
import re
import unicodedata

from support_poc.contracts import (
    AnswerOrigin,
    AuditRecord,
    ComponentRef,
    FailureCode,
    GenerationRequest,
    ProcessingOutcome,
    ProcessingResult,
    TicketInput,
)
from support_poc.errors import AdapterError
from support_poc.interfaces import (
    AnswerResolver,
    DraftValidator,
    IntentClassifier,
    PIIRedactor,
    RiskDetector,
    TextGenerator,
)


NORMALIZER = ComponentRef(
    provider="python-stdlib",
    implementation="unicodedata-normalize",
    model=None,
    version="poc-v1",
)
ROUTING_POLICY = ComponentRef(
    provider="local",
    implementation="fail-closed-routing-policy",
    model=None,
    version="poc-v1",
)


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold().strip()
    return re.sub(r"\s+", " ", normalized)


class TicketProcessor:
    def __init__(
        self,
        *,
        redactor: PIIRedactor,
        risk_detector: RiskDetector,
        classifier: IntentClassifier,
        resolver: AnswerResolver,
        generator: TextGenerator,
        validator: DraftValidator,
    ) -> None:
        self._redactor = redactor
        self._risk_detector = risk_detector
        self._classifier = classifier
        self._resolver = resolver
        self._generator = generator
        self._validator = validator

    def process(self, ticket: TicketInput) -> ProcessingResult:
        audit: list[AuditRecord] = []
        normalized = normalize_text(ticket.content)
        audit.append(AuditRecord(stage="normalization", action="normalized", component=NORMALIZER))

        pii = self._redactor.redact(normalized)
        audit.append(
            AuditRecord(
                stage="pii",
                action="redacted" if pii.findings else "not_detected",
                reason_codes=pii.findings,
                component=pii.component,
            )
        )
        dedup_key = hashlib.sha256(pii.redacted_text.encode("utf-8")).hexdigest()
        if pii.residual_risk:
            return self._human_result(
                ticket=ticket,
                redacted_text=pii.redacted_text,
                dedup_key=dedup_key,
                reason=FailureCode.PII_UNCERTAIN,
                audit=audit,
            )

        risk = self._risk_detector.assess(pii.redacted_text)
        audit.append(
            AuditRecord(
                stage="risk",
                action="human_review" if risk.risky else "safe",
                reason_codes=risk.labels,
                component=risk.component,
            )
        )
        if risk.risky:
            return self._human_result(
                ticket=ticket,
                redacted_text=pii.redacted_text,
                dedup_key=dedup_key,
                reason="risky_ticket",
                audit=audit,
            )

        prediction = self._classifier.classify(pii.redacted_text)
        audit.append(
            AuditRecord(
                stage="intent",
                action="abstained" if prediction.abstained else "classified",
                reason_codes=[prediction.intent, f"confidence:{prediction.confidence:.4f}"],
                component=prediction.component,
            )
        )
        if prediction.abstained:
            return self._human_result(
                ticket=ticket,
                redacted_text=pii.redacted_text,
                dedup_key=dedup_key,
                reason=FailureCode.LOW_CONFIDENCE,
                audit=audit,
                intent=prediction.intent,
                confidence=prediction.confidence,
            )

        resolution = self._resolver.resolve(
            intent=prediction.intent,
            text=pii.redacted_text,
            locale=ticket.locale,
        )
        audit.append(
            AuditRecord(
                stage="resolution",
                action=resolution.origin,
                reason_codes=(
                    [f"confidence:{resolution.confidence:.4f}"]
                    if resolution.confidence is not None
                    else []
                ),
                component=resolution.component,
            )
        )
        if resolution.origin in {AnswerOrigin.APPROVED_EXACT, AnswerOrigin.APPROVED_SEMANTIC}:
            audit.append(
                AuditRecord(
                    stage="routing",
                    action=ProcessingOutcome.AUTO_REPLY,
                    component=ROUTING_POLICY,
                )
            )
            return ProcessingResult(
                ticket_id=ticket.ticket_id,
                outcome=ProcessingOutcome.AUTO_REPLY,
                route_reason=resolution.origin,
                redacted_text=pii.redacted_text,
                dedup_key=dedup_key,
                intent=prediction.intent,
                intent_confidence=prediction.confidence,
                answer=resolution.content,
                evidence_refs=[item.evidence_id for item in resolution.evidence],
                audit=audit,
            )

        if not resolution.evidence:
            return self._human_result(
                ticket=ticket,
                redacted_text=pii.redacted_text,
                dedup_key=dedup_key,
                reason=FailureCode.RETRIEVAL_MISS,
                audit=audit,
                intent=prediction.intent,
                confidence=prediction.confidence,
            )
        if not pii.external_processing_allowed:
            return self._human_result(
                ticket=ticket,
                redacted_text=pii.redacted_text,
                dedup_key=dedup_key,
                reason=FailureCode.PII_UNCERTAIN,
                audit=audit,
                intent=prediction.intent,
                confidence=prediction.confidence,
            )

        request = GenerationRequest(
            redacted_ticket=pii.redacted_text,
            intent=prediction.intent,
            locale=ticket.locale,
            evidence=resolution.evidence,
        )
        try:
            draft = self._generator.generate(request)
        except AdapterError as error:
            audit.append(
                AuditRecord(
                    stage="generation",
                    action="failed",
                    reason_codes=[error.code],
                    component=error.component,
                )
            )
            return self._human_result(
                ticket=ticket,
                redacted_text=pii.redacted_text,
                dedup_key=dedup_key,
                reason=error.code,
                audit=audit,
                intent=prediction.intent,
                confidence=prediction.confidence,
            )
        audit.append(AuditRecord(stage="generation", action="drafted", component=draft.component))

        validation = self._validator.validate(draft, request)
        audit.append(
            AuditRecord(
                stage="draft_validation",
                action="passed" if validation.valid else "failed",
                reason_codes=[validation.failure] if validation.failure else [],
                component=validation.component,
            )
        )
        if not validation.valid:
            return self._human_result(
                ticket=ticket,
                redacted_text=pii.redacted_text,
                dedup_key=dedup_key,
                reason=validation.failure or FailureCode.SAFETY_FAILED,
                audit=audit,
                intent=prediction.intent,
                confidence=prediction.confidence,
            )

        audit.append(
            AuditRecord(
                stage="routing",
                action=ProcessingOutcome.OPERATOR_REVIEW_WITH_DRAFT,
                component=ROUTING_POLICY,
            )
        )
        return ProcessingResult(
            ticket_id=ticket.ticket_id,
            outcome=ProcessingOutcome.OPERATOR_REVIEW_WITH_DRAFT,
            route_reason="generated_draft_requires_review",
            redacted_text=pii.redacted_text,
            dedup_key=dedup_key,
            intent=prediction.intent,
            intent_confidence=prediction.confidence,
            draft=draft.content,
            evidence_refs=draft.evidence_refs,
            audit=audit,
        )

    @staticmethod
    def _human_result(
        *,
        ticket: TicketInput,
        redacted_text: str,
        dedup_key: str,
        reason: str,
        audit: list[AuditRecord],
        intent: str | None = None,
        confidence: float | None = None,
    ) -> ProcessingResult:
        audit.append(
            AuditRecord(
                stage="routing",
                action=ProcessingOutcome.HUMAN_REVIEW_WITHOUT_DRAFT,
                reason_codes=[str(reason)],
                component=ROUTING_POLICY,
            )
        )
        return ProcessingResult(
            ticket_id=ticket.ticket_id,
            outcome=ProcessingOutcome.HUMAN_REVIEW_WITHOUT_DRAFT,
            route_reason=str(reason),
            redacted_text=redacted_text,
            dedup_key=dedup_key,
            intent=intent,
            intent_confidence=confidence,
            audit=audit,
        )
