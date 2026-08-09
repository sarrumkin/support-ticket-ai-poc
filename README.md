# AI Hub Support PoC

System Design проект AI/ML-системы для автоматизации обработки тикетов поддержки крупного
онлайн-сервиса: классификация и маршрутизация на быстром пути, retrieval и подготовка ответа на
асинхронном пути, human-in-the-loop для рискованных случаев и полный audit trail решений.

## Статус

**Slice 1 — Repository bootstrap**, **Slice 2 — Ticket processing flow** и **Slice 3 — Architecture,
capacity and latency** завершены. Product-level ticket flow отделён от reference implementation
diagram; также зафиксированы lifecycle, delivery semantics и sizing под incident burst. Основной PoC
ещё не реализован; следующий слайс будет определён только после отдельного checkpoint.

## Планируемый demo-сценарий

1. На вход поступает синтетический mock-ticket.
2. Система определяет тему, риск и confidence.
3. Для безопасного типового тикета сначала ищет готовый approved answer; generation используется
   только при отсутствии надёжного exact/semantic match.
4. Для risky или low-confidence тикета выбирает маршрут к оператору.
5. Оба пути записывают audit log решения.

## Реализация и target design

- **Будет реализовано в PoC:** один воспроизводимый happy path, один risky/fallback path, локальные
  fixtures, demo-скрипт, audit log и smoke-test.
- **Останется архитектурным дизайном:** production queues, autoscaling, внешние интеграции, полноценная
  vector DB, MLOps и обучение моделей на историческом потоке.
- **Открытое решение:** конкретный ML/LLM baseline выбирается в отдельном слайсе; в bootstrap он не
  фиксируется преждевременно.

## Проверка Slice 3

Пока основной PoC не реализован, доступен только synthetic CPU benchmark deterministic hot-path
adapters:

```bash
python3 -m unittest discover -s tests -v
python3 scripts/benchmark_hot_path.py --tickets 20000 --warmup 1000 \
  --min-throughput 67 --max-p95-ms 500
```

Benchmark не поднимает PostgreSQL, broker, внешние providers или модели и не подтверждает
production latency/replica sizing. Его назначение — воспроизводимо проверить арифметику thresholds,
JSON report и локальный orchestration overhead.

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
