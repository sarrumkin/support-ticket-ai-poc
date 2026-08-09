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

## Критерий готовности

Для каждой критичной деградации должен существовать наблюдаемый сигнал, владелец реакции и безопасное
fallback-поведение. Пороги должны быть помечены как стартовые assumptions или подтверждённые пилотом.
