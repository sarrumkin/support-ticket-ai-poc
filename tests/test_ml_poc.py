from __future__ import annotations

import os

import pytest

from support_poc.adapters import (
    DeterministicDraftValidator,
    FixtureGenerator,
    GroqQwenGenerator,
    QdrantAnswerResolver,
    RuleRiskDetector,
    ScrubadubRedactor,
)
from support_poc.contracts import (
    AnswerOrigin,
    ComponentRef,
    Evidence,
    FailureCode,
    GeneratedDraft,
    IntentPrediction,
    ProcessingOutcome,
    ResolutionResult,
    TicketInput,
)
from support_poc.demo import build_processor, fixture_path
from support_poc.errors import AdapterError
from support_poc.pipeline import TicketProcessor
from support_poc.settings import Settings


TEST_COMPONENT = ComponentRef(
    provider="test",
    implementation="deterministic-test-adapter",
    model=None,
    version="test-v1",
)


class FixedClassifier:
    def __init__(self, intent: str = "profile_update") -> None:
        self.intent = intent
        self.called = False

    def classify(self, _text: str) -> IntentPrediction:
        self.called = True
        return IntentPrediction(
            intent=self.intent,
            confidence=0.99,
            abstained=False,
            component=TEST_COMPONENT,
        )


class EvidenceMissResolver:
    def __init__(self) -> None:
        self.called = False

    def resolve(self, *, intent: str, text: str, locale: str) -> ResolutionResult:
        self.called = True
        return ResolutionResult(
            origin=AnswerOrigin.MISS,
            evidence=[
                Evidence(
                    evidence_id="kb-profile-name",
                    content="Имя можно изменить в настройках профиля.",
                    source_ref="synthetic-kb://profile/name",
                )
            ],
            component=TEST_COMPONENT,
        )


class SpyGenerator:
    def __init__(self, failure: FailureCode | None = None) -> None:
        self.called = False
        self.failure = failure

    def generate(self, request):
        self.called = True
        if self.failure:
            raise AdapterError(self.failure, TEST_COMPONENT, "synthetic provider failure")
        return GeneratedDraft(
            content="Измените имя в настройках профиля.",
            evidence_refs=[request.evidence[0].evidence_id],
            component=TEST_COMPONENT,
        )


class UnknownEvidenceGenerator:
    def generate(self, _request):
        return GeneratedDraft(
            content="Непроверенный ответ.",
            evidence_refs=["unknown-evidence"],
            component=TEST_COMPONENT,
        )


def processor(*, classifier, resolver, generator) -> TicketProcessor:
    redactor = ScrubadubRedactor()
    return TicketProcessor(
        redactor=redactor,
        risk_detector=RuleRiskDetector.from_json(fixture_path("risk_rules.json")),
        classifier=classifier,
        resolver=resolver,
        generator=generator,
        validator=DeterministicDraftValidator(redactor),
    )


def test_exact_answer_skips_embeddings_and_generator() -> None:
    resolver = QdrantAnswerResolver.from_json(fixture_path("knowledge.json"))
    generator = SpyGenerator()
    result = processor(
        classifier=FixedClassifier("order_status"),
        resolver=resolver,
        generator=generator,
    ).process(TicketInput(ticket_id="exact-1", content="где мой заказ"))

    assert result.outcome is ProcessingOutcome.AUTO_REPLY
    assert result.route_reason == AnswerOrigin.APPROVED_EXACT
    assert result.answer
    assert resolver._client is None
    assert generator.called is False
    resolution_audit = next(item for item in result.audit if item.stage == "resolution")
    assert resolution_audit.component.implementation == "versioned-json-dict"
    assert resolution_audit.component.model is None


def test_risky_ticket_redacts_pii_and_skips_downstream_adapters() -> None:
    classifier = FixedClassifier()
    resolver = EvidenceMissResolver()
    generator = SpyGenerator()
    result = processor(
        classifier=classifier,
        resolver=resolver,
        generator=generator,
    ).process(
        TicketInput(
            ticket_id="risky-1",
            content="С моей карты списали деньги, email test@example.com",
        )
    )

    assert result.outcome is ProcessingOutcome.HUMAN_REVIEW_WITHOUT_DRAFT
    assert result.route_reason == "risky_ticket"
    assert "test@example.com" not in result.redacted_text
    assert classifier.called is False
    assert resolver.called is False
    assert generator.called is False


def test_evidence_miss_builds_reviewable_offline_draft() -> None:
    result = processor(
        classifier=FixedClassifier(),
        resolver=EvidenceMissResolver(),
        generator=FixtureGenerator(),
    ).process(TicketInput(ticket_id="generated-1", content="изменить имя в профиле"))

    assert result.outcome is ProcessingOutcome.OPERATOR_REVIEW_WITH_DRAFT
    assert result.route_reason == "generated_draft_requires_review"
    assert result.draft
    assert result.evidence_refs == ["kb-profile-name"]


@pytest.mark.parametrize(
    ("generator", "expected_reason"),
    [
        (SpyGenerator(FailureCode.PROVIDER_UNAVAILABLE), FailureCode.PROVIDER_UNAVAILABLE),
        (UnknownEvidenceGenerator(), FailureCode.SAFETY_FAILED),
    ],
)
def test_provider_or_validation_failure_fails_closed(generator, expected_reason) -> None:
    result = processor(
        classifier=FixedClassifier(),
        resolver=EvidenceMissResolver(),
        generator=generator,
    ).process(TicketInput(ticket_id="failure-1", content="изменить имя в профиле"))

    assert result.outcome is ProcessingOutcome.HUMAN_REVIEW_WITHOUT_DRAFT
    assert result.route_reason == expected_reason
    assert result.draft is None


def test_groq_malformed_json_maps_to_typed_failure() -> None:
    class Message:
        content = "not-json"

    class Choice:
        message = Message()

    class Completions:
        @staticmethod
        def create(**_kwargs):
            return type("Response", (), {"choices": [Choice()]})()

    client = type(
        "Client",
        (),
        {"chat": type("Chat", (), {"completions": Completions()})()},
    )()
    generator = GroqQwenGenerator(api_key="synthetic", client=client)
    request = type(
        "Request",
        (),
        {
            "evidence": [],
            "locale": "ru",
            "intent": "profile_update",
            "redacted_ticket": "изменить имя",
        },
    )()

    with pytest.raises(AdapterError) as error:
        generator.generate(request)
    assert error.value.code is FailureCode.INVALID_OUTPUT


@pytest.mark.semantic
@pytest.mark.skipif(
    os.getenv("RUN_SEMANTIC_TESTS") != "1",
    reason="set RUN_SEMANTIC_TESTS=1 to download and run FastEmbed",
)
def test_real_local_semantic_generated_path() -> None:
    result = build_processor(Settings()).process(
        TicketInput(ticket_id="semantic-1", content="как изменить имя в профиле")
    )
    assert result.outcome is ProcessingOutcome.OPERATOR_REVIEW_WITH_DRAFT
    assert result.evidence_refs


@pytest.mark.groq
@pytest.mark.skipif(
    os.getenv("RUN_GROQ_TESTS") != "1" or not os.getenv("GROQ_API_KEY"),
    reason="set RUN_GROQ_TESTS=1 and GROQ_API_KEY for the optional network check",
)
def test_real_groq_with_synthetic_redacted_ticket() -> None:
    settings = Settings.from_env().model_copy(update={"generator_provider": "groq"})
    result = build_processor(settings).process(
        TicketInput(ticket_id="groq-1", content="как изменить имя в профиле")
    )
    assert result.outcome in {
        ProcessingOutcome.OPERATOR_REVIEW_WITH_DRAFT,
        ProcessingOutcome.HUMAN_REVIEW_WITHOUT_DRAFT,
    }
