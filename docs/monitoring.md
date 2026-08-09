# Monitoring

**Статус:** архитектурные сигналы Slice 3 определены; production thresholds требуют pilot data.

## Обязательные области

- Technical: input throughput; end-to-end и per-stage `p50/p95/p99` hot-path latency; errors, in-flight
  work, queue age/length, consumer saturation и dependency health.
- ML: class distribution, confidence, abstention, offline/online quality, drift и retrieval relevance.
- Product/business: first response SLA, operator touch rate, CSAT, reopen rate и доля безопасной
  автоматизации.
- Resolution: direct-answer hit rate, exact/semantic split, LLM avoidance rate, fallback rate и
  operator-review rate.
- Cost: LLM calls, tokens, cache/dedup hit rate, стоимость ответа/тикета и дневной budget burn.
- Safety: PII redaction, blocked auto-actions, prompt-injection signals и audit completeness.
- Delivery: outbox lag, attempts, retryable/terminal failures, confirmation latency, dedup hits и
  доля providers без native idempotency support.

## Стартовые SLO и capacity signals

- `RoutingDecision` и durable state/audit/outbox commit: `p95 <= 500 ms`.
- Design input target: `66.7 ticket/s` как 2x observed peak; превышение является capacity signal, а
  не основанием молча отбрасывать тикеты.
- SLA содержательного первого ответа: до 15 минут в обычном режиме. Технический acknowledgement и
  status events измеряются отдельно и не закрывают этот SLA.
- Для async paths основной leading indicator — возраст старейшего сообщения. Queue length без
  arrival/consumer rate недостаточен для оценки нарушения SLA.
- `answered_without_delivery_confirmation` и `automatic_action_without_audit` должны всегда быть 0.
- Повторно полученный `event_id` увеличивает `delivery_dedup_hit`, но не user-visible send count.

## Открытые решения

- Severity thresholds поверх SLO, кроме жёстких invariants выше.
- Как отделить деградацию модели от изменения входящего потока.
- Как связывать prediction, action, operator correction и итог обращения.
- Какие метрики доказывают решение исходной задачи, а не только исправность сервисов.
- Как измерять residual duplicate risk для providers без idempotency key/reconciliation API.

## Минимальные сигналы Slice 4

PoC пока не экспортирует metrics backend, но его typed audit позволяет посчитать `route_reason`,
exact/semantic/generated split, abstention, risk/PII blocks, provider/validation failures и версии
фактически вызванных components. Для pilot обязательны также operator correction outcome и связь
`prediction → evidence → draft → final operator answer`; без неё confidence нельзя калибровать по
реальному результату.

## Verification evidence Slice 5

Evidence получен 2026-08-09 на synthetic fixtures. Default/semantic проверки выполнены offline;
внешний Groq check — отдельно с локально заданным `GROQ_API_KEY`, значение которого не логировалось.

### Offline suite

```bash
.venv/bin/python -m pytest -q -rs
```

Результат: `16 passed, 2 skipped, 2 warnings in 2.02s`. Suite подтвердил:

- HTTP contract `202 → polling`, status mapping, duplicate/validation/not-found responses и
  fail-closed обработку unexpected exception;
- exact answer без embeddings/generator, PII redaction до risk routing, risky human fallback,
  fixture draft и отказ от непроверенного draft при provider/validation failure;
- корректность synthetic hot-path benchmark harness и его thresholds.

Skipped tests не являются скрытыми failures: real semantic test запускается отдельным opt-in из-за
загрузки модели, а Groq test требует network и secret.

### Local semantic integration

```bash
RUN_SEMANTIC_TESTS=1 .venv/bin/python -m pytest -q -m semantic -rs
```

Результат: `1 passed, 17 deselected, 2 warnings in 8.37s`. Проверка реально загрузила FastEmbed,
построила in-memory Qdrant index, получила evidence и сформировала offline draft. Это подтверждает
связность semantic/generated path, но не relevance quality и не корректность threshold `0.82` на
реальных данных. Warning о смене pooling multilingual MiniLM остаётся recalibration trigger.

### External Groq integration

```bash
RUN_GROQ_TESTS=1 .venv/bin/python -m pytest -q -m groq -rs
RUN_SEMANTIC_TESTS=1 RUN_GROQ_TESTS=1 .venv/bin/python -m pytest -q -rs
```

Targeted result: `1 passed, 17 deselected, 2 warnings in 6.48s`. Полный suite с обоими opt-in
checks: `18 passed, 4 warnings in 7.15s`, без skipped tests.

Отдельный synthetic probe для `profile_update` завершился за `6.081s`: Groq adapter вызвал
`qwen/qwen3.6-27b`, вернул валидный grounded draft с evidence `kb-profile-name`, а policy выбрала
`operator_review_with_draft`. Это подтверждает текущую доступность provider/model, JSON contract,
evidence validation и безопасный запрет generated auto-send. Один probe не подтверждает p95/p99,
стабильность provider, factual quality, cost или privacy suitability для реальных данных.

### Docker HTTP smoke

Image `ai-hub-support-poc:slice5` успешно собран и запущен с одним worker. `/health` вернул
`generator_provider=fixture`, `storage=in_memory`, `delivery=polling_demo`.

- Exact ticket: `202 processing_automatically → completed/answered`, outcome `auto_reply`, intent
  `order_status`, origin `approved_exact`, match confidence `1.0`.
- Risky ticket с email: `202 processing_automatically → completed/waiting_for_specialist`, outcome
  `human_review_without_draft`, email заменён на `{{EMAIL}}`, risk label `payment_dispute`.
- В обоих путях stdout содержит stage-by-stage audit с `ticket_id`, `trace_id` и component versions.

### Что evidence не доказывает

- `16 passed` проверяют contracts и control flow на synthetic данных, а не production ML quality,
  CSAT, reopen rate или calibrated confidence.
- Semantic pass доказывает работоспособность integration, но не precision/recall retrieval.
- Docker smoke не проверяет durable processing, restart recovery, несколько replicas, настоящую
  channel delivery или SLA первого ответа 15 минут.
- Groq probe подтвердил один synthetic request, но не даёт статистики provider latency/availability,
  cost и output quality; для этого нужны повторные измерения и размеченная evaluation set.
- Два dependency warnings не сломали suite, но TestClient migration и FastEmbed recalibration должны
  быть закрыты перед обновлением runtime dependencies.

## Критерий готовности

Для каждой критичной деградации должен существовать наблюдаемый сигнал, владелец реакции и безопасное
fallback-поведение. Пороги должны быть помечены как стартовые assumptions или подтверждённые пилотом.
