from __future__ import annotations

import json

import pytest

from support_poc.contracts import ProcessingOutcome
from support_poc.scenarios import (
    ScenarioProfile,
    generated_request_payload,
    load_catalog,
    run_case,
)


CATALOG = load_catalog()


def test_catalog_is_versioned_unique_and_covers_documented_outcomes() -> None:
    assert CATALOG.version == "poc-scenarios-v1"
    assert len({case.scenario_id for case in CATALOG.cases}) == len(CATALOG.cases)
    assert len({case.ticket.ticket_id for case in CATALOG.cases}) == len(CATALOG.cases)
    assert {case.expected.outcome for case in CATALOG.cases} == set(ProcessingOutcome)
    assert {case.profile for case in CATALOG.cases} == set(ScenarioProfile)


@pytest.mark.parametrize("case", CATALOG.cases, ids=lambda case: case.scenario_id)
def test_synthetic_scenario_matches_expected_contract(case) -> None:
    run = run_case(case)

    assert run.mismatches == []
    assert run.passed is True
    assert run.result.audit[-1].stage == "routing"


def test_generated_request_payload_is_jsonl_safe_and_http_ready() -> None:
    payloads = [generated_request_payload(case, CATALOG.version) for case in CATALOG.cases]
    encoded = "\n".join(json.dumps(payload, ensure_ascii=False) for payload in payloads)
    decoded = [json.loads(line) for line in encoded.splitlines()]

    assert len(decoded) == len(CATALOG.cases)
    assert all(item["catalog_version"] == CATALOG.version for item in decoded)
    expected_request_fields = {"ticket_id", "content", "locale", "incident_id"}
    assert all(set(item["request"]) == expected_request_fields for item in decoded)
    assert all(item["request"]["content"] for item in decoded)
