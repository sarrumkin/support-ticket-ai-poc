# AI Hub Support PoC

System Design проект AI/ML-системы для автоматизации обработки тикетов поддержки крупного
онлайн-сервиса: классификация и маршрутизация на быстром пути, retrieval и подготовка ответа на
асинхронном пути, human-in-the-loop для рискованных случаев и полный audit trail решений.

## Статус

Slices 1–4 завершены. В **Slice 4 — Minimal PoC ML baseline** реализован offline-first tracer:
Pydantic/Protocol contracts, Scrubadub, versioned risk rules, scikit-learn intent classifier,
exact lookup, FastEmbed + in-memory Qdrant, fixture/Groq generation adapters и fail-closed audit flow.

## Demo-сценарии

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'

.venv/bin/python -m support_poc.demo exact
.venv/bin/python -m support_poc.demo risky
.venv/bin/python -m support_poc.demo generated
```

Первые два пути не требуют embedding model. `generated` при первом запуске скачивает примерно 220 MB
multilingual MiniLM, строит локальный in-memory index и использует deterministic fixture generator.
Все входы и KB fixtures синтетические.

Optional Groq check включается явно и получает только redacted synthetic ticket:

```bash
GROQ_API_KEY=... .venv/bin/python -m support_poc.demo generated --generator groq
RUN_GROQ_TESTS=1 GROQ_API_KEY=... .venv/bin/python -m pytest -q -m groq
```

Ключ не хранится в репозитории. Без него offline suite и demo полностью работоспособны.

## Реализация и target design

- **Реализовано в PoC:** exact/risky/generated/failure paths, synthetic fixtures, CLI, typed audit и
  replaceable adapters.
- **Останется архитектурным дизайном:** production queues, autoscaling, внешние интеграции, полноценная
  vector DB service, MLOps, real-data evaluation и обучение на историческом потоке.
- **Честная граница:** synthetic confidence и similarity thresholds не calibrated; Scrubadub не
  является полноценным RU PII NER; generated content всегда требует проверки оператора.

## Проверка

```bash
.venv/bin/python -m pytest -q
RUN_SEMANTIC_TESTS=1 .venv/bin/python -m pytest -q -m semantic
python3 scripts/benchmark_hot_path.py --tickets 20000 --warmup 1000 \
  --min-throughput 67 --max-p95-ms 500
```

Обязательный pytest suite не использует сеть или API key. Marked semantic check скачивает локальную
модель; Groq integration запускается отдельно. Benchmark Slice 3 не включает реальные dependencies и
не подтверждает production latency/replica sizing.

## Ценность для бизнеса

Система должна снизить стоимость обработки повторяющихся обращений, доля которых оценивается примерно
в 40% потока, и ускорить первый ответ без ухудшения безопасности. Быстрая классификация и точная
маршрутизация уменьшают ручную сортировку и риск нарушения SLA в периоды инцидентов. Черновики ответов
освобождают время операторов, а human-in-the-loop ограничивает стоимость ошибок модели. Audit trail и
контроль LLM-затрат делают автоматизацию управляемой, а не бесконтрольной заменой операторов.

## Документация

- [Требования и scope AI-трека](docs/brief.md)
- [Slice map](SLICE_MAP.md)
- [Архитектура](docs/architecture.md)
- [Контракт обработки тикета](docs/ticket-processing-flow.md)
- [ML/LLM-подход](docs/ml.md)
- [Мониторинг](docs/monitoring.md)
- [Риски и эксплуатация](docs/risks-and-ops.md)
- [Использование AI](AI_USAGE.md)
- [Self-review](SELF_REVIEW.md)
