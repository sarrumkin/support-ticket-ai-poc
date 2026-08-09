from __future__ import annotations

import argparse
from importlib.resources import files
from pathlib import Path

from support_poc.adapters import (
    DeterministicDraftValidator,
    FixtureGenerator,
    GroqQwenGenerator,
    QdrantAnswerResolver,
    RuleRiskDetector,
    ScrubadubRedactor,
    SklearnIntentClassifier,
)
from support_poc.contracts import TicketInput
from support_poc.pipeline import TicketProcessor
from support_poc.settings import Settings


SCENARIOS = {
    "exact": "где мой заказ",
    "risky": "с моей карты списали деньги, мой email test@example.com",
    "generated": "как изменить имя в профиле",
}


def fixture_path(name: str) -> Path:
    return Path(str(files("support_poc").joinpath("fixtures", name)))


def build_processor(settings: Settings) -> TicketProcessor:
    redactor = ScrubadubRedactor()
    if settings.generator_provider == "fixture":
        generator = FixtureGenerator()
    elif settings.generator_provider == "groq":
        if not settings.groq_api_key:
            raise SystemExit("Для generator=groq требуется GROQ_API_KEY")
        generator = GroqQwenGenerator(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
        )
    else:
        raise SystemExit(f"Неизвестный generation provider: {settings.generator_provider}")

    return TicketProcessor(
        redactor=redactor,
        risk_detector=RuleRiskDetector.from_json(fixture_path("risk_rules.json")),
        classifier=SklearnIntentClassifier.from_json(
            fixture_path("intents.json"),
            threshold=settings.intent_threshold,
        ),
        resolver=QdrantAnswerResolver.from_json(
            fixture_path("knowledge.json"),
            semantic_threshold=settings.semantic_threshold,
            top_k=settings.semantic_top_k,
            embedding_model=settings.embedding_model,
        ),
        generator=generator,
        validator=DeterministicDraftValidator(redactor),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline-first support ticket ML PoC")
    parser.add_argument("scenario", choices=SCENARIOS, nargs="?", default="exact")
    parser.add_argument("--generator", choices=("fixture", "groq"))
    args = parser.parse_args()

    settings = Settings.from_env()
    if args.generator:
        settings = settings.model_copy(update={"generator_provider": args.generator})
    result = build_processor(settings).process(
        TicketInput(
            ticket_id=f"synthetic-{args.scenario}",
            content=SCENARIOS[args.scenario],
        )
    )
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
