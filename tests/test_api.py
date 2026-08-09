from fastapi.testclient import TestClient

from support_poc.api import create_app
from support_poc.contracts import AuditRecord, ComponentRef, ProcessingOutcome, ProcessingResult


COMPONENT = ComponentRef(provider="test", implementation="fixed", version="1")


class FixedProcessor:
    def __init__(self, outcome=ProcessingOutcome.AUTO_REPLY, reason="approved_exact"):
        self.outcome = outcome
        self.reason = reason

    def process(self, ticket):
        return ProcessingResult(
            ticket_id=ticket.ticket_id,
            outcome=self.outcome,
            route_reason=self.reason,
            redacted_text="redacted",
            dedup_key="dedup",
            answer="Готовый ответ" if self.outcome is ProcessingOutcome.AUTO_REPLY else None,
            draft="Черновик" if self.outcome is ProcessingOutcome.OPERATOR_REVIEW_WITH_DRAFT else None,
            audit=[AuditRecord(stage="routing", action=self.outcome, component=COMPONENT)],
        )


class ExplodingProcessor:
    def process(self, _ticket):
        raise RuntimeError("synthetic failure that must not escape")


def test_accepts_and_exposes_completed_ticket() -> None:
    client = TestClient(create_app(FixedProcessor()))
    response = client.post("/tickets", json={"ticket_id": "t-1", "content": "Где заказ?"})
    assert response.status_code == 202
    assert response.headers["location"] == "/tickets/t-1"
    assert response.json()["current_status"] == "processing_automatically"

    state = client.get("/tickets/t-1")
    assert state.status_code == 200
    assert state.json()["job_status"] == "completed"
    assert state.json()["current_status"] == "answered"
    assert state.json()["result"]["answer"] == "Готовый ответ"


def test_human_and_escalation_status_mapping() -> None:
    risky = TestClient(create_app(FixedProcessor(ProcessingOutcome.HUMAN_REVIEW_WITHOUT_DRAFT, "risky_ticket")))
    risky.post("/tickets", json={"ticket_id": "risky", "content": "Списание"})
    assert risky.get("/tickets/risky").json()["current_status"] == "waiting_for_specialist"

    failed = TestClient(create_app(FixedProcessor(ProcessingOutcome.HUMAN_REVIEW_WITHOUT_DRAFT, "provider_unavailable")))
    failed.post("/tickets", json={"ticket_id": "failed", "content": "Профиль"})
    assert failed.get("/tickets/failed").json()["current_status"] == "escalated_to_specialist"


def test_duplicate_validation_health_and_missing() -> None:
    client = TestClient(create_app(FixedProcessor()))
    payload = {"ticket_id": "same", "content": "Вопрос"}
    assert client.post("/tickets", json=payload).status_code == 202
    assert client.post("/tickets", json=payload).status_code == 409
    assert client.post("/tickets", json={"ticket_id": "bad", "content": ""}).status_code == 422
    assert client.get("/tickets/missing").status_code == 404
    assert client.get("/health").json()["delivery"] == "polling_demo"
    assert {"/health", "/tickets", "/tickets/{ticket_id}"} <= set(
        client.get("/openapi.json").json()["paths"]
    )


def test_unexpected_failure_is_hidden_and_escalated() -> None:
    client = TestClient(create_app(ExplodingProcessor()))
    assert client.post("/tickets", json={"ticket_id": "boom", "content": "Секрет"}).status_code == 202
    state = client.get("/tickets/boom").json()
    assert state["job_status"] == "failed"
    assert state["current_status"] == "escalated_to_specialist"
    assert state["failure_reason"] == "internal_error"
    assert state["result"] is None
