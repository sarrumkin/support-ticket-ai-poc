# AI Hub Support PoC

Минимальный воспроизводимый PoC AI/ML-системы для обработки тикетов поддержки: быстрый risk-aware
routing, поиск готового ответа, генерация draft, HTTP polling API и audit trail.

## Диаграммы

- [Путь тикета: end-to-end pipeline](docs/ticket-processing-flow.md#end-to-end-pipeline)
- [Lifecycle тикета и пользовательские статусы](docs/ticket-processing-flow.md#минимальный-lifecycle)
- [Целевая архитектура: reference implementation](docs/architecture.md#reference-implementation-diagram)

## Быстрый старт

Требуется Python 3.13+.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'

.venv/bin/python -m support_poc.demo exact
.venv/bin/python -m support_poc.demo risky
.venv/bin/python -m support_poc.demo generated
```

Все тикеты и материалы knowledge base синтетические. Сценарии `exact` и `risky` не загружают
embedding model. При первом запуске `generated` скачивается около 220 MB для multilingual MiniLM;
ответ создаёт deterministic fixture generator, поэтому API key не нужен.

## Что показывают сценарии

| Сценарий | Результат |
|---|---|
| `exact` | Готовый approved answer найден без embeddings и generation |
| `risky` | Рискованный тикет fail closed передан оператору без непроверенного draft |
| `generated` | Semantic retrieval и generation создают draft для проверки оператором |

## HTTP PoC

```bash
.venv/bin/uvicorn support_poc.api:app --host 0.0.0.0 --port 8000 --workers 1

curl -i -X POST http://localhost:8000/tickets \
  -H 'Content-Type: application/json' \
  -d '{"ticket_id":"demo-1","content":"Где мой заказ?","channel":"web"}'

curl http://localhost:8000/tickets/demo-1
```

`POST /tickets` возвращает `202`, обработка продолжается в background task, результат доступен через
polling. Интерактивная OpenAPI-схема — на `http://localhost:8000/docs`, полный контракт — в
[docs/api-contract.md](docs/api-contract.md).

Запуск в Docker:

```bash
docker build -t support-poc .
docker run --rm -p 8000:8000 support-poc
```

## Синтетические тестовые запросы

Versioned catalog `poc-scenarios-v1` покрывает три реализованных outcome и отдельные причины
fail-closed маршрутизации. Команда `generate` печатает JSONL: каждая строка содержит HTTP-ready
`request` и ожидаемый contract. Команда `verify` выполняет все cases через текущий `TicketProcessor`:

```bash
.venv/bin/python -m support_poc.scenarios generate
.venv/bin/python -m support_poc.scenarios generate --scenario risky-payment-with-pii
.venv/bin/python -m support_poc.scenarios verify
```

Offline verifier использует deterministic control adapters для exact/semantic/dependency outcomes,
поэтому не скачивает embedding model и не обращается к сети. Он проверяет orchestration, route и
audit contracts, включая обязательное отсутствие downstream stages после fail-closed решения, но не
измеряет качество intent classification или semantic retrieval. Для реального локального FastEmbed
path остаётся отдельный marked test.

## Граница решения

**Реализовано в PoC:** PII redaction, risk rules, intent classification, exact и semantic retrieval,
fixture/Groq generation adapters, fail-closed routing, typed audit, CLI, async HTTP polling transport
и offline tests.

**Только target design:** production queues и autoscaling, внешние интеграции, отдельная vector DB,
MLOps, real-data evaluation и обучение на исторических тикетах.

**Ограничения:** confidence и similarity thresholds не calibrated; Scrubadub не заменяет полноценный
RU PII NER; сгенерированный ответ всегда требует проверки оператора. HTTP state хранится in-memory,
а `BackgroundTasks` и один worker моделируют transport, но не production queue или delivery.

## Проверка

```bash
.venv/bin/python -m pytest -q
RUN_SEMANTIC_TESTS=1 .venv/bin/python -m pytest -q -m semantic
python3 scripts/benchmark_hot_path.py --tickets 20000 --warmup 1000 \
  --min-throughput 67 --max-p95-ms 500
```

Основной suite работает без сети и API key. Semantic check отдельно скачивает локальную модель.
Synthetic benchmark измеряет overhead Python harness, а не production latency внешних сервисов.

Опциональная проверка Groq получает только redacted synthetic ticket:

```bash
GROQ_API_KEY=... .venv/bin/python -m support_poc.demo generated --generator groq
RUN_GROQ_TESTS=1 GROQ_API_KEY=... .venv/bin/python -m pytest -q -m groq
```

## Бизнес-ценность

Около 40% обращений считаются верхней оценкой пула повторяющихся кейсов, а не обещанной долей
автоответов. KB-first path сокращает ручную сортировку и число LLM-вызовов; human-in-the-loop
ограничивает стоимость ошибок; audit trail делает каждое автоматическое решение проверяемым.

## Документация

- [Требования и границы](docs/brief.md)
- [Контракт обработки тикета](docs/ticket-processing-flow.md)
- [HTTP API contract PoC](docs/api-contract.md)
- [Архитектура, capacity и latency](docs/architecture.md)
- [ML/LLM-подход и качество](docs/ml.md)
- [Мониторинг](docs/monitoring.md)
- [Privacy, safety и эксплуатационные риски](docs/risks-and-ops.md)
- [Использование AI](AI_USAGE.md)
- [Self-review](SELF_REVIEW.md)
- [Карта выполненных слайсов](SLICE_MAP.md)
