"""Minimal ML PoC for support ticket routing."""

from support_poc.contracts import ProcessingOutcome, ProcessingResult, TicketInput
from support_poc.pipeline import TicketProcessor

__all__ = ["ProcessingOutcome", "ProcessingResult", "TicketInput", "TicketProcessor"]
