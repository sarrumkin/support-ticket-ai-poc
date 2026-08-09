from __future__ import annotations

import argparse
import json
from enum import StrEnum
from importlib.resources import files
from pathlib import Path
from typing import Any

from pydantic import Field, model_validator

from support_poc.adapters import (
    DeterministicDraftValidator,
    FixtureGenerator,
    RuleRiskDetector,
    ScrubadubRedactor,
    load_json,
)
from support_poc.contracts import (
    AnswerOrigin,
    AuditRecord,
    ComponentRef,
    Evidence,
    FailureCode,
    GeneratedDraft,
    GenerationRequest,
    IntentPrediction,
    PIIRedactionResult,
    ProcessingOutcome,
    ProcessingResult,
    ResolutionResult,
    StrictModel,
    TicketInput,
)
from support_poc.errors import AdapterError
from support_poc.pipeline import TicketProcessor


class ScenarioProfile(StrEnum):
    EXACT = "exact"
    SEMANTIC = "semantic"
    GENERATED = "generated"
    RISKY = "risky"
    PII_UNCERTAIN = "pii_uncertain"
    LOW_CONFIDENCE = "low_confidence"
    RETRIEVAL_MISS = "retrieval_miss"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    SAFETY_FAILED = "safety_failed"


class AuditExpectation(StrictModel):
    stage: str
    action: str
    reason_code: str | None = None


class ScenarioExpectation(StrictModel):
    outcome: ProcessingOutcome
    route_reason: str
    answer_present: bool = False
    draft_present: bool = False
    redacted_absent: list[str] = Field(default_factory=list)
    audit_contains: list[AuditExpectation] = Field(min_length=1)
    audit_absent_stages: list[str] = Field(default_factory=list)


class TestScenario(StrictModel):
    scenario_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    profile: ScenarioProfile
    ticket: TicketInput
    expected: ScenarioExpectation


class ScenarioCatalog(StrictModel):
    version: str = Field(min_length=1)
    cases: list[TestScenario] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_identifiers(self) -> "ScenarioCatalog":
        scenario_ids = [case.scenario_id for case in self.cases]
        ticket_ids = [case.ticket.ticket_id for case in self.cases]
        if len(scenario_ids) != len(set(scenario_ids)):
            raise ValueError("scenario_id values must be unique")
        if len(ticket_ids) != len(set(ticket_ids)):
            raise ValueError("ticket_id values must be unique")
        return self


class ScenarioRun(StrictModel):
    scenario_id: str
    passed: bool
    mismatches: list[str]
    result: ProcessingResult


SCENARIO_COMPONENT = ComponentRef(
    provider="fixture",
    implementation="scenario-control-adapter",
    model=None,
    version="poc-v1",
)


def fixture_path(name: str) -> Path:
    return Path(str(files("support_poc").joinpath("fixtures", name)))


def catalog_path() -> Path:
    return fixture_path("test_requests.json")


def load_catalog(path: Path | None = None) -> ScenarioCatalog:
    return ScenarioCatalog.model_validate(load_json(path or catalog_path()))


class _ScenarioRedactor:
    def __init__(self, delegate: ScrubadubRedactor, profile: ScenarioProfile) -> None:
        self._delegate = delegate
        self._profile = profile

    def redact(self, text: str) -> PIIRedactionResult:
        result = self._delegate.redact(text)
        if self._profile is not ScenarioProfile.PII_UNCERTAIN:
            return result
        return result.model_copy(
            update={
                "findings": [*result.findings, "scenario_uncertain_pii"],
                "residual_risk": True,
                "external_processing_allowed": False,
                "component": SCENARIO_COMPONENT,
            }
        )


class _ScenarioClassifier:
    def __init__(self, profile: ScenarioProfile) -> None:
        self._profile = profile

    def classify(self, _text: str) -> IntentPrediction:
        if self._profile is ScenarioProfile.LOW_CONFIDENCE:
            return IntentPrediction(
                intent="unknown",
                confidence=0.10,
                abstained=True,
                component=SCENARIO_COMPONENT,
            )
        intent = "order_status" if self._profile is ScenarioProfile.EXACT else "profile_update"
        return IntentPrediction(
            intent=intent,
            confidence=0.99,
            abstained=False,
            component=SCENARIO_COMPONENT,
        )


class _ScenarioResolver:
    def __init__(self, profile: ScenarioProfile) -> None:
        self._profile = profile

    def resolve(self, *, intent: str, text: str, locale: str) -> ResolutionResult:
        del intent, text
        evidence = Evidence(
            evidence_id="kb-scenario",
            content="Синтетическая статья базы знаний для проверки маршрута.",
            source_ref="synthetic-kb://scenario/control",
        )
        if self._profile is ScenarioProfile.EXACT:
            return ResolutionResult(
                origin=AnswerOrigin.APPROVED_EXACT,
                content="Синтетический утверждённый exact-ответ.",
                confidence=1.0,
                evidence=[evidence],
                component=SCENARIO_COMPONENT,
            )
        if self._profile is ScenarioProfile.SEMANTIC:
            return ResolutionResult(
                origin=AnswerOrigin.APPROVED_SEMANTIC,
                content="Синтетический утверждённый semantic-ответ.",
                confidence=0.95,
                evidence=[evidence],
                component=SCENARIO_COMPONENT,
            )
        if self._profile is ScenarioProfile.RETRIEVAL_MISS:
            return ResolutionResult(
                origin=AnswerOrigin.MISS,
                evidence=[],
                component=SCENARIO_COMPONENT,
            )
        if locale != "ru":
            return ResolutionResult(
                origin=AnswerOrigin.MISS,
                evidence=[],
                component=SCENARIO_COMPONENT,
            )
        return ResolutionResult(
            origin=AnswerOrigin.MISS,
            evidence=[evidence],
            component=SCENARIO_COMPONENT,
        )


class _ScenarioGenerator:
    def __init__(self, profile: ScenarioProfile) -> None:
        self._profile = profile
        self._delegate = FixtureGenerator()

    def generate(self, request: GenerationRequest) -> GeneratedDraft:
        if self._profile is ScenarioProfile.PROVIDER_UNAVAILABLE:
            raise AdapterError(
                FailureCode.PROVIDER_UNAVAILABLE,
                SCENARIO_COMPONENT,
                "Synthetic provider outage",
            )
        if self._profile is ScenarioProfile.SAFETY_FAILED:
            return GeneratedDraft(
                content="Синтетический неподтверждённый черновик.",
                evidence_refs=["unknown-evidence"],
                component=SCENARIO_COMPONENT,
            )
        return self._delegate.generate(request)


def build_scenario_processor(profile: ScenarioProfile) -> TicketProcessor:
    base_redactor = ScrubadubRedactor()
    return TicketProcessor(
        redactor=_ScenarioRedactor(base_redactor, profile),
        risk_detector=RuleRiskDetector.from_json(fixture_path("risk_rules.json")),
        classifier=_ScenarioClassifier(profile),
        resolver=_ScenarioResolver(profile),
        generator=_ScenarioGenerator(profile),
        validator=DeterministicDraftValidator(base_redactor),
    )


def verify_result(case: TestScenario, result: ProcessingResult) -> list[str]:
    expected = case.expected
    mismatches: list[str] = []
    if result.outcome is not expected.outcome:
        mismatches.append(f"outcome: expected {expected.outcome}, got {result.outcome}")
    if result.route_reason != expected.route_reason:
        mismatches.append(
            f"route_reason: expected {expected.route_reason}, got {result.route_reason}"
        )
    if bool(result.answer) is not expected.answer_present:
        mismatches.append(f"answer_present: expected {expected.answer_present}")
    if bool(result.draft) is not expected.draft_present:
        mismatches.append(f"draft_present: expected {expected.draft_present}")
    for sensitive_value in expected.redacted_absent:
        if sensitive_value.casefold() in result.redacted_text.casefold():
            mismatches.append(f"redacted_text still contains {sensitive_value!r}")
    for audit_expected in expected.audit_contains:
        if not any(_audit_matches(record, audit_expected) for record in result.audit):
            reason = (
                f", reason_code={audit_expected.reason_code}"
                if audit_expected.reason_code
                else ""
            )
            mismatches.append(
                "missing audit record: "
                f"stage={audit_expected.stage}, action={audit_expected.action}{reason}"
            )
    for stage in expected.audit_absent_stages:
        if any(record.stage == stage for record in result.audit):
            mismatches.append(f"unexpected audit stage: {stage}")
    return mismatches


def _audit_matches(record: AuditRecord, expected: AuditExpectation) -> bool:
    return (
        record.stage == expected.stage
        and record.action == expected.action
        and (
            expected.reason_code is None
            or expected.reason_code in record.reason_codes
        )
    )


def run_case(case: TestScenario) -> ScenarioRun:
    result = build_scenario_processor(case.profile).process(case.ticket)
    mismatches = verify_result(case, result)
    return ScenarioRun(
        scenario_id=case.scenario_id,
        passed=not mismatches,
        mismatches=mismatches,
        result=result,
    )


def generated_request_payload(case: TestScenario, catalog_version: str) -> dict[str, Any]:
    return {
        "catalog_version": catalog_version,
        "scenario_id": case.scenario_id,
        "description": case.description,
        "request": case.ticket.model_dump(mode="json"),
        "expected": case.expected.model_dump(mode="json"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate or verify deterministic synthetic support requests"
    )
    parser.add_argument("command", choices=("generate", "verify"), nargs="?", default="verify")
    parser.add_argument("--scenario", help="Run or print one scenario_id")
    args = parser.parse_args()

    catalog = load_catalog()
    cases = [
        case
        for case in catalog.cases
        if not args.scenario or case.scenario_id == args.scenario
    ]
    if not cases:
        parser.error(f"unknown scenario_id: {args.scenario}")

    if args.command == "generate":
        for case in cases:
            print(
                json.dumps(
                    generated_request_payload(case, catalog.version),
                    ensure_ascii=False,
                )
            )
        return

    runs = [run_case(case) for case in cases]
    print(
        json.dumps(
            [run.model_dump(mode="json") for run in runs],
            ensure_ascii=False,
            indent=2,
        )
    )
    if not all(run.passed for run in runs):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
