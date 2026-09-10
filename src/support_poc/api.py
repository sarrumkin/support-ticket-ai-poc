from __future__ import annotations

import json
import logging
import threading
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException, Response, status
from pydantic import Field

from support_poc.contracts import ProcessingOutcome, ProcessingResult, StrictModel, TicketInput
from support_poc.demo import build_processor
from support_poc.pipeline import TicketProcessor
from support_poc.settings import Settings


logger = logging.getLogger("support_poc.audit")
logger.setLevel(logging.INFO)
if not logger.handlers:
    audit_handler = logging.StreamHandler()
    audit_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(audit_handler)
logger.propagate = False


class UserStatus(StrEnum):
    PROCESSING_AUTOMATICALLY = "processing_automatically"
    WAITING_FOR_SPECIALIST = "waiting_for_specialist"
    REVIEWING_WITH_SPECIALIST = "reviewing_with_specialist"
    ESCALATED_TO_SPECIALIST = "escalated_to_specialist"
    ANSWERED = "answered"


class JobStatus(StrEnum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TicketCreateRequest(StrictModel):
    ticket_id: str = Field(min_length=1)
    content: str = Field(min_length=1)
    locale: str = "ru"
    incident_id: str | None = None
    channel: Literal["web", "chat", "email", "mobile"] = "web"


class StatusEvent(StrictModel):
    status: UserStatus
    occurred_at: datetime


class TicketAccepted(StrictModel):
    ticket_id: str
    trace_id: str
    current_status: UserStatus
    status_url: str


class TicketStateResponse(StrictModel):
    ticket_id: str
    trace_id: str
    channel: str
    job_status: JobStatus
    current_status: UserStatus
    status_history: list[StatusEvent]
    result: ProcessingResult | None = None
    failure_reason: str | None = None


class HealthResponse(StrictModel):
    status: str = "ok"
    generator_provider: str
    storage: str = "in_memory"
    delivery: str = "polling_demo"


@dataclass
class JobRecord:
    ticket_id: str
    trace_id: str
    channel: str
    job_status: JobStatus
    current_status: UserStatus
    status_history: list[StatusEvent]
    result: ProcessingResult | None = None
    failure_reason: str | None = None

    def response(self) -> TicketStateResponse:
        return TicketStateResponse(**self.__dict__)


class InMemoryJobStore:
    def __init__(self) -> None:
        self._records: dict[str, JobRecord] = {}
        self._lock = threading.Lock()

    def create(self, ticket_id: str, trace_id: str, channel: str) -> JobRecord:
        with self._lock:
            if ticket_id in self._records:
                raise ValueError("duplicate_ticket_id")
            now = datetime.now(UTC)
            record = JobRecord(
                ticket_id=ticket_id,
                trace_id=trace_id,
                channel=channel,
                job_status=JobStatus.PROCESSING,
                current_status=UserStatus.PROCESSING_AUTOMATICALLY,
                status_history=[StatusEvent(status=UserStatus.PROCESSING_AUTOMATICALLY, occurred_at=now)],
            )
            self._records[ticket_id] = record
            return deepcopy(record)

    def get(self, ticket_id: str) -> JobRecord | None:
        with self._lock:
            record = self._records.get(ticket_id)
            return deepcopy(record) if record else None

    def complete(self, ticket_id: str, result: ProcessingResult) -> None:
        with self._lock:
            record = self._records[ticket_id]
            next_status = status_for_result(result)
            record.job_status = JobStatus.COMPLETED
            record.current_status = next_status
            record.status_history.append(StatusEvent(status=next_status, occurred_at=datetime.now(UTC)))
            record.result = result

    def fail(self, ticket_id: str) -> None:
        with self._lock:
            record = self._records[ticket_id]
            record.job_status = JobStatus.FAILED
            record.current_status = UserStatus.ESCALATED_TO_SPECIALIST
            record.failure_reason = "internal_error"
            record.status_history.append(
                StatusEvent(status=UserStatus.ESCALATED_TO_SPECIALIST, occurred_at=datetime.now(UTC))
            )


DIRECT_HUMAN_REASONS = {"risky_ticket", "pii_uncertain", "low_confidence"}


def status_for_result(result: ProcessingResult) -> UserStatus:
    if result.outcome is ProcessingOutcome.AUTO_REPLY:
        return UserStatus.ANSWERED
    if result.outcome is ProcessingOutcome.OPERATOR_REVIEW_WITH_DRAFT:
        return UserStatus.REVIEWING_WITH_SPECIALIST
    if result.route_reason in DIRECT_HUMAN_REASONS:
        return UserStatus.WAITING_FOR_SPECIALIST
    return UserStatus.ESCALATED_TO_SPECIALIST


class BackgroundJobRunner:
    def __init__(self, processor: TicketProcessor, store: InMemoryJobStore) -> None:
        self._processor = processor
        self._store = store
        self._process_lock = threading.Lock()

    def process(self, ticket: TicketInput, trace_id: str) -> None:
        try:
            with self._process_lock:
                result = self._processor.process(ticket)
            self._store.complete(ticket.ticket_id, result)
            for audit in result.audit:
                logger.info(
                    json.dumps(
                        {"ticket_id": ticket.ticket_id, "trace_id": trace_id, **audit.model_dump(mode="json")},
                        ensure_ascii=False,
                    )
                )
        except Exception as error:  # keep the public path fail-closed
            # Do not include exception text/traceback: third-party errors may echo raw input.
            logger.error("background processing failed: %s", error.__class__.__name__)
            self._store.fail(ticket.ticket_id)


def create_app(processor: TicketProcessor | None = None) -> FastAPI:
    settings = Settings.from_env()
    store = InMemoryJobStore()
    runner = BackgroundJobRunner(processor or build_processor(settings), store)
    app = FastAPI(title="Support Ticket AI PoC", version="0.1.0")

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(generator_provider=settings.generator_provider)

    @app.post("/tickets", response_model=TicketAccepted, status_code=status.HTTP_202_ACCEPTED)
    def create_ticket(
        request: TicketCreateRequest,
        background_tasks: BackgroundTasks,
        response: Response,
    ) -> TicketAccepted:
        trace_id = str(uuid4())
        try:
            store.create(request.ticket_id, trace_id, request.channel)
        except ValueError as error:
            raise HTTPException(status_code=409, detail="ticket_id already exists") from error
        ticket = TicketInput(
            ticket_id=request.ticket_id,
            content=request.content,
            locale=request.locale,
            incident_id=request.incident_id,
        )
        background_tasks.add_task(runner.process, ticket, trace_id)
        status_url = f"/tickets/{request.ticket_id}"
        response.headers["Location"] = status_url
        response.headers["Retry-After"] = "1"
        return TicketAccepted(
            ticket_id=request.ticket_id,
            trace_id=trace_id,
            current_status=UserStatus.PROCESSING_AUTOMATICALLY,
            status_url=status_url,
        )

    @app.get("/tickets/{ticket_id}", response_model=TicketStateResponse)
    def ticket_state(ticket_id: str) -> TicketStateResponse:
        record = store.get(ticket_id)
        if record is None:
            raise HTTPException(status_code=404, detail="ticket not found")
        return record.response()

    return app


app = create_app()
