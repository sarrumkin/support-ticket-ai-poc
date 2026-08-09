# Целевая архитектура

**Статус:** skeleton; проектные решения принимаются в Slice 2.

## Уже известные ограничения

- Классификация и маршрутизация находятся на синхронном hot path с ориентиром `<= 500 ms`.
- Retrieval и генерация могут выполняться асинхронно.
- Система должна выдерживать кратковременные incident bursts без безусловного вызова LLM для каждого
  дубликата.
- LLM outage не должен блокировать приём, классификацию и передачу тикета оператору.
- Все автоматические решения требуют audit trail и воспроизводимой версии policy/model/knowledge.

## Компоненты и границы

- `Channel Ingress` принимает неоднородные обращения и приводит их к единому входному контракту.
- Sync hot path выполняет normalization, PII/risk detection, intent classification и
  `RoutingPolicy` за ориентир `<= 500 ms`.
- Async resolution предпочитает exact/semantic match по approved knowledge base и вызывает
  generation только при отсутствии надёжного готового ответа.
- Для exact lookup eligibility встроена в resolver; для semantic lookup после фильтрации approved
  content используется только match-confidence gate.
- `GeneratedResponsePolicy` отделяет получение сгенерированного draft от права отправить его
  автоматически и не применяется к approved answers.
- Human-review path и audit trail являются независимыми от доступности LLM.

Подробные outcomes, data contracts, пользовательские статусы, lifecycle, fallback и Mermaid flow
зафиксированы в [`docs/ticket-processing-flow.md`](ticket-processing-flow.md).

## Что предстоит определить

- Компоненты и ownership boundaries.
- Контракты входного тикета и audit record; response contracts определены в processing contract.
- Очереди, хранилища, deduplication, backpressure и fallback paths target design.
- Human-in-the-loop и категории, запрещённые для автозакрытия.
- Capacity assumptions и component sizing.

## Критерий готовности

Архитектура вместе с processing contract должна позволить пройти путь тикета от ingress до
ответа/маршрута, отличить PoC от target design и объяснить поведение при пике, low confidence, PII и
недоступности внешних сервисов.
