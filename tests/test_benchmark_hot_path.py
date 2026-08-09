import math
import unittest

from scripts.benchmark_hot_path import (
    DESIGN_TARGET_RPS,
    HOT_PATH_SLO_MS,
    MIN_IN_FLIGHT,
    SyntheticTicket,
    percentile,
    process_ticket,
    redact_pii,
    run_benchmark,
)


class HotPathContractTests(unittest.TestCase):
    def test_capacity_concurrency_matches_littles_law(self) -> None:
        expected = math.ceil(DESIGN_TARGET_RPS * HOT_PATH_SLO_MS / 1_000)
        self.assertEqual(MIN_IN_FLIGHT, 34)
        self.assertEqual(MIN_IN_FLIGHT, expected)

    def test_email_is_redacted_before_routing(self) -> None:
        redacted, pii_result = redact_pii("Напишите user@example.test")
        self.assertEqual(pii_result, "redacted")
        self.assertNotIn("user@example.test", redacted)

    def test_sensitive_intent_routes_to_human(self) -> None:
        decision = process_ticket(
            SyntheticTicket("sensitive", "Оспариваю списание, требуется chargeback")
        )
        self.assertEqual(decision.route, "human_review_required")
        self.assertEqual(decision.reason, "sensitive_intent")

    def test_safe_known_intent_is_automation_candidate(self) -> None:
        decision = process_ticket(SyntheticTicket("safe", "Где мой заказ?"))
        self.assertEqual(decision.route, "automatic_resolution_candidate")

    def test_percentile_interpolates(self) -> None:
        self.assertEqual(percentile([1.0, 2.0, 3.0, 4.0], 50), 2.5)

    def test_small_benchmark_reports_all_tickets_and_passes_relaxed_thresholds(self) -> None:
        report = run_benchmark(
            ticket_count=100,
            warmup_count=10,
            min_throughput=1.0,
            max_p95_ms=500.0,
        )
        benchmark = report["benchmark"]
        route_total = sum(benchmark["route_counts"].values())
        self.assertEqual(route_total, 100)
        self.assertTrue(report["passed"])


if __name__ == "__main__":
    unittest.main()
