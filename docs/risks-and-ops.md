# Risks and operations

**Статус:** skeleton; итоговый файл останется коротким — по 3–4 ключевых решения на направление.

## Highload и надёжность

- Разделить sync classification/routing и async retrieval/generation.
- Поглощать bursts очередью и backpressure, не масштабировать LLM-вызовы пропорционально дубликатам.
- При LLM outage сохранять приём тикета, deterministic routing и human fallback.
- Не допускать нарушения hot-path latency медленными зависимостями.

## Privacy, safety и risk

- Не отправлять сырой PII во внешний LLM; redaction и policy enforcement выполняются до такого вызова.
- Risky, чувствительные и low-confidence категории требуют human-in-the-loop.
- Knowledge/retrieved content и пользовательский текст считать недоверенными относительно prompt
  injection.
- Audit record должен объяснять принятое действие и версии участвовавших policy/model/knowledge.

## Открытые решения

- Конкретные категории запрета автозакрытия.
- Deduplication key и incident-mode policy.
- Retention/access policy audit storage.
- Circuit breakers, retry budgets и cost caps.

## Критерий готовности

Риски должны быть связаны с конкретными preventive/detective controls и fallback, а не перечислены
как общие опасения.
