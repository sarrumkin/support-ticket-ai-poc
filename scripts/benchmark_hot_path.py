#!/usr/bin/env python3
"""Synthetic CPU-only benchmark for the proposed synchronous decision path.

The benchmark deliberately excludes databases, brokers, networks and real models. It measures the
local Python orchestration ceiling of deterministic adapters and must not be used for replica sizing.
"""

from __future__ import annotations

import argparse
import json
import math
import platform
import re
import statistics
import sys
import time
from collections import Counter
from dataclasses import dataclass
from typing import Iterable


AVERAGE_RPS = 200_000 / 86_400
OBSERVED_PEAK_RPS = 20_000 / 600
DESIGN_TARGET_RPS = OBSERVED_PEAK_RPS * 2
HOT_PATH_SLO_MS = 500.0
MIN_IN_FLIGHT = math.ceil(DESIGN_TARGET_RPS * HOT_PATH_SLO_MS / 1_000)

EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
SPACE_PATTERN = re.compile(r"\s+")


@dataclass(frozen=True)
class SyntheticTicket:
    ticket_id: str
    text: str
    locale: str = "ru-RU"


@dataclass(frozen=True)
class Decision:
    route: str
    reason: str
    intent: str
    pii_result: str


FIXTURES = (
    "Не могу войти в аккаунт, помогите восстановить доступ",
    "Где мой заказ? Email для связи user@example.test",
    "Оспариваю списание, требуется chargeback и проверка специалиста",
    "Описание неполное, confidence low",
)


def normalize(text: str) -> str:
    return SPACE_PATTERN.sub(" ", text.strip().lower())


def redact_pii(text: str) -> tuple[str, str]:
    redacted, count = EMAIL_PATTERN.subn("<email_redacted>", text)
    return redacted, "redacted" if count else "not_detected"


def classify(text: str) -> str:
    if "заказ" in text:
        return "order_status"
    if "войти" in text or "доступ" in text:
        return "account_access"
    if "списание" in text or "chargeback" in text:
        return "payment_dispute"
    return "unknown"


def route(text: str, intent: str) -> tuple[str, str]:
    if intent == "payment_dispute":
        return "human_review_required", "sensitive_intent"
    if "confidence low" in text or intent == "unknown":
        return "human_review_required", "low_confidence"
    return "automatic_resolution_candidate", "safe_high_confidence"


def process_ticket(ticket: SyntheticTicket) -> Decision:
    normalized = normalize(ticket.text)
    redacted, pii_result = redact_pii(normalized)
    intent = classify(redacted)
    selected_route, reason = route(redacted, intent)
    return Decision(selected_route, reason, intent, pii_result)


def percentile(values: list[float], percentile_value: float) -> float:
    if not values:
        raise ValueError("values must not be empty")
    if not 0 <= percentile_value <= 100:
        raise ValueError("percentile must be between 0 and 100")
    ordered = sorted(values)
    rank = (len(ordered) - 1) * percentile_value / 100
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[lower]
    fraction = rank - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def synthetic_tickets(count: int) -> Iterable[SyntheticTicket]:
    for index in range(count):
        yield SyntheticTicket(ticket_id=f"synthetic-{index}", text=FIXTURES[index % len(FIXTURES)])


def run_benchmark(
    ticket_count: int,
    warmup_count: int,
    min_throughput: float,
    max_p95_ms: float,
) -> dict[str, object]:
    if ticket_count <= 0:
        raise ValueError("ticket_count must be positive")
    if warmup_count < 0:
        raise ValueError("warmup_count must not be negative")

    for ticket in synthetic_tickets(warmup_count):
        process_ticket(ticket)

    latencies_ms: list[float] = []
    route_counts: Counter[str] = Counter()
    intent_counts: Counter[str] = Counter()

    benchmark_started = time.perf_counter_ns()
    for ticket in synthetic_tickets(ticket_count):
        ticket_started = time.perf_counter_ns()
        decision = process_ticket(ticket)
        latencies_ms.append((time.perf_counter_ns() - ticket_started) / 1_000_000)
        route_counts[decision.route] += 1
        intent_counts[decision.intent] += 1
    elapsed_seconds = (time.perf_counter_ns() - benchmark_started) / 1_000_000_000

    throughput = ticket_count / elapsed_seconds
    latency = {
        "p50_ms": percentile(latencies_ms, 50),
        "p95_ms": percentile(latencies_ms, 95),
        "p99_ms": percentile(latencies_ms, 99),
        "mean_ms": statistics.fmean(latencies_ms),
    }
    passed = throughput >= min_throughput and latency["p95_ms"] <= max_p95_ms

    return {
        "evidence_boundary": (
            "CPU-only deterministic Python adapters; excludes database, broker, network, "
            "channel provider and real ML/LLM latency"
        ),
        "environment": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.system(),
            "machine": platform.machine(),
        },
        "capacity_assumptions": {
            "average_rps": AVERAGE_RPS,
            "observed_peak_rps": OBSERVED_PEAK_RPS,
            "design_target_rps": DESIGN_TARGET_RPS,
            "hot_path_slo_ms": HOT_PATH_SLO_MS,
            "minimum_in_flight": MIN_IN_FLIGHT,
        },
        "benchmark": {
            "mode": "single-process-cpu-ceiling",
            "tickets": ticket_count,
            "warmup_tickets": warmup_count,
            "elapsed_seconds": elapsed_seconds,
            "throughput_tickets_per_second": throughput,
            "latency": latency,
            "route_counts": dict(sorted(route_counts.items())),
            "intent_counts": dict(sorted(intent_counts.items())),
        },
        "thresholds": {
            "min_throughput_tickets_per_second": min_throughput,
            "max_p95_ms": max_p95_ms,
        },
        "passed": passed,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tickets", type=int, default=20_000)
    parser.add_argument("--warmup", type=int, default=1_000)
    parser.add_argument("--min-throughput", type=float, default=67.0)
    parser.add_argument("--max-p95-ms", type=float, default=500.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = run_benchmark(
            ticket_count=args.tickets,
            warmup_count=args.warmup,
            min_throughput=args.min_throughput,
            max_p95_ms=args.max_p95_ms,
        )
    except ValueError as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
