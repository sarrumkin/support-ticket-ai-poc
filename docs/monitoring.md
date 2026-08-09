# Monitoring

**Статус:** skeleton; конкретные метрики и alerts прорабатываются после контрактов и tracer paths.

## Обязательные области

- Technical: throughput, latency hot/async paths, errors, queue lag, saturation и dependency health.
- ML: class distribution, confidence, abstention, offline/online quality, drift и retrieval relevance.
- Product/business: first response SLA, operator touch rate, CSAT, reopen rate и доля безопасной
  автоматизации.
- Cost: LLM calls, tokens, cache/dedup hit rate, стоимость на тикет и дневной budget burn.
- Safety: PII redaction, blocked auto-actions, prompt-injection signals и audit completeness.

## Открытые решения

- Стартовые thresholds и severity alerts.
- Как отделить деградацию модели от изменения входящего потока.
- Как связывать prediction, action, operator correction и итог обращения.
- Какие метрики доказывают решение исходной задачи, а не только исправность сервисов.

## Критерий готовности

Для каждой критичной деградации должен существовать наблюдаемый сигнал, владелец реакции и безопасное
fallback-поведение. Пороги должны быть помечены как стартовые assumptions или подтверждённые пилотом.
