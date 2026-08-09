from typing import Protocol

from support_poc.contracts import (
    GeneratedDraft,
    GenerationRequest,
    IntentPrediction,
    PIIRedactionResult,
    ResolutionResult,
    RiskAssessment,
    ValidationResult,
)


class PIIRedactor(Protocol):
    def redact(self, text: str) -> PIIRedactionResult: ...


class RiskDetector(Protocol):
    def assess(self, text: str) -> RiskAssessment: ...


class IntentClassifier(Protocol):
    def classify(self, text: str) -> IntentPrediction: ...


class AnswerResolver(Protocol):
    def resolve(self, *, intent: str, text: str, locale: str) -> ResolutionResult: ...


class TextGenerator(Protocol):
    def generate(self, request: GenerationRequest) -> GeneratedDraft: ...


class DraftValidator(Protocol):
    def validate(self, draft: GeneratedDraft, request: GenerationRequest) -> ValidationResult: ...
