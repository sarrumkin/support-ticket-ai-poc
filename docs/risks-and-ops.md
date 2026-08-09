# Risks and operations

**Статус:** skeleton; итоговый файл останется коротким — по 3–4 ключевых решения на направление.

## Highload и надёжность

- Разделить sync classification/routing и async retrieval/generation.
- Проектировать sync path на стартовый target `66.7 ticket/s` (`2x` observed peak), `p95 <= 500 ms`
  и минимум 34 in-flight операции; replica sizing отложить до реальных измерений dependencies.
- Поглощать bursts durable outbox/очередью и backpressure, не масштабировать LLM-вызовы
  пропорционально дубликатам.
- При LLM outage сохранять приём тикета, deterministic routing и human fallback.
- Не допускать нарушения hot-path latency медленными зависимостями.
- State transition, audit и outbox event создавать атомарно; status/reply events обрабатывать
  `at-least-once` со стабильным `event_id` и delivery ledger. Для provider без idempotency support
  сохраняется наблюдаемый residual duplicate risk.

## Privacy, safety и risk

- Не отправлять сырой PII во внешний LLM; redaction и policy enforcement выполняются до такого вызова.
- Успешно redacted PII сам по себе не запрещает safe automation; sensitive/unredactable PII, risky и
  low-confidence категории требуют human-in-the-loop.
- Разделять controls по происхождению ответа: `RoutingPolicy` выполняется до resolution; exact lookup
  возвращает только eligible approved answer; semantic lookup ищет в таком же candidate set и
  дополнительно проверяет match confidence; `GeneratedResponsePolicy` применяется только к
  generated content. Сам факт успешной generation не разрешает немедленный auto-reply, а при отказе
  policy оператор получает пригодный draft и evidence для проверки.
- Stale или low-confidence KB match переводить в generation; конфликтующие active approved answers —
  в human review без draft. Incident mode должен использовать versioned approved response/cache и не
  вызывать LLM для каждого дубликата.
- Knowledge/retrieved content и пользовательский текст считать недоверенными относительно prompt
  injection.
- Audit record должен объяснять принятое действие и версии участвовавших policy/model/knowledge.
- Lookup miss нельзя смешивать с KB/semantic outage: недоступность dependency fail closed ведёт в
  human review. `answered` фиксируется только после delivery confirmation.

## Production blockers

- Нет подтверждённого per-intent confidence threshold и допустимого error rate для auto-reply.
  Threshold должен быть откалиброван на размеченной validation set, а приемлемый error rate — утверждён
  по данным пилота. До этого `GeneratedResponsePolicy` должна fail closed в
  `operator_review_with_draft`, даже если generation и остальные проверки завершились успешно.
- Нет подтверждённого semantic-match threshold для прямой отправки approved answer. До калибровки
  semantic result не должен автоматически отправляться только на основании similarity score и
  переводится в generation path.

## Открытые решения

- Конкретные категории запрета автозакрытия.
- Допустимый error rate auto-reply и per-intent calibration thresholds.
- Deduplication key и incident-mode policy.
- Retention/access policy audit storage.
- Circuit breakers, retry budgets и cost caps.
- Retention и reconciliation policy delivery ledger.

## Ограничение performance evidence

Slice 3 содержит только CPU-only synthetic benchmark deterministic adapters. Он проверяет harness,
percentiles и thresholds, но не включает сеть, PostgreSQL, broker, providers или реальные ML/LLM и
не подтверждает production replica count.

## Критерий готовности

Риски должны быть связаны с конкретными preventive/detective controls и fallback, а не перечислены
как общие опасения.
