# Контракт обработки тикета

**Статус:** проектный контракт Slice 2; реализация отсутствует.

Документ определяет outcomes, policy, пользовательские статусы и end-to-end flow. Компонентные
границы целевой системы описаны в [`docs/architecture.md`](architecture.md), требования и scope — в
[`docs/brief.md`](brief.md).

## Продуктовая граница

Около 40% типовых и повторяющихся обращений — верхняя оценка пула кандидатов на дешёвый direct-answer
path, а не обещанная доля auto-reply и не требование вызывать LLM для каждого такого тикета. Система
сначала пытается вернуть versioned approved text из knowledge base и использует generation только
при отсутствии надёжного готового ответа.

## Policy и outcomes

Контроли разделены по происхождению ответа:

- `RoutingPolicy` на синхронном hot path выбирает `human_review_required` или
  `automatic_resolution_candidate`;
- `LayeredAnswerResolver` сам проверяет eligibility для готовых approved answers;
- `GeneratedResponsePolicy` применяется только к сгенерированному draft и выбирает `auto_reply`,
  `operator_review_with_draft` или `human_review_without_draft`.

`LayeredAnswerResolver` работает вне hot path в следующем порядке:

1. Exact lookup по `intent`, `incident_id` и `locale` возвращает versioned `ApprovedAnswer`, только
   если он active, актуален и имеет `auto_reply_eligible = true`. Иначе результат считается miss.
2. При miss выполняется semantic search только среди таких же eligible approved KB entries. После
   lookup применяется единственный дополнительный gate — подтверждённый semantic-match confidence.
3. Stale или low-confidence match переводится в retrieval + generation; конфликтующие approved
   ответы переводятся в human review без draft.

Direct-answer path не вызывает генеративную модель и не проходит отдельную `ResponsePolicy`:
eligibility exact-ответа является частью lookup, а semantic-ответ после предварительной фильтрации
проходит только match-confidence gate. Incident mode и auto-reply kill switch учитываются при
формировании eligible candidate set. Generated draft требует evidence, grounding, safety result и
отдельное решение `GeneratedResponsePolicy`. Если draft пригоден для оператора, но auto-reply
запрещён, оператор получает draft вместе с evidence. Unsafe draft не передаётся оператору как
готовый ответ.

Итоговый outcome:

- `auto_reply` → `answered`;
- `operator_review_with_draft` → human review с draft и evidence → `answered`;
- `human_review_without_draft` → human review без непроверенного draft → `answered`.

## Минимальные data contracts

### `ApprovedAnswer`

- `answer_id`, `version`, `locale`, `text`;
- `match_keys`: поддерживаемые `intent`, `incident_id` и exact keys;
- `source_ref`, `valid_from`, `valid_until`, `status`;
- `auto_reply_eligible`.

### `AnswerCandidate`

- `origin`: `approved_exact | approved_semantic | generated`;
- `content`, `evidence_refs`, `confidence`;
- `safety_result`: `passed | failed | not_applicable`;
- версии resolver/model/knowledge, необходимые для audit.

### `GeneratedResponsePolicyAction`

- `auto_reply`;
- `operator_review_with_draft`;
- `human_review_without_draft`.

## Пользовательские статусы

- `processing_automatically`: «Запрос принят. Подбираем решение»;
- `waiting_for_specialist`: «Чтобы дать точный ответ, мы передали обращение специалисту»;
- `reviewing_with_specialist`: «Ответ подготовлен и передан специалисту на проверку»;
- `escalated_to_specialist`: «Автоматически подготовить ответ не получилось. Обращение уже передано
  специалисту; повторно описывать проблему не нужно»;
- `answered`: содержательный ответ доставлен пользователю.

`reviewing_with_specialist` используется только для пригодного draft. `escalated_to_specialist`
создаётся только после фактической смены route из-за conflict/failure, когда пригодного draft нет, а
не при отдельном retry.

Hot path фиксирует route, новое внутреннее состояние, audit record и status event, но не ждёт
channel-provider delivery. Для chat/web тот же результат можно вернуть как синхронный acknowledgement;
для email/mobile доставка status выполняется асинхронно. Поэтому `<= 500 ms` относится к техническому
acknowledgement и routing decision, а не к наблюдаемой пользователем доставке через любой канал.

Status/reply events обрабатываются `at-least-once`; стабильный `event_id` позволяет consumer подавлять
повторный side effect. Причина выбора и ограничения внешнего provider подробно описаны в разделе
«Надёжность доставки событий» [`docs/architecture.md`](architecture.md).

## Минимальный lifecycle

Internal state отделён от пользовательского status. `answered` означает подтверждённую доставку
содержательного ответа и переводит внутреннее состояние в `pending_customer`, а не является
синонимом попытки отправки.

```mermaid
stateDiagram-v2
    [*] --> accepted
    accepted --> resolving_automatically: automatic_resolution_candidate / processing_automatically
    accepted --> waiting_for_specialist: human_review_required / waiting_for_specialist

    resolving_automatically --> delivery_pending: approved или generated auto-reply
    resolving_automatically --> reviewing_with_specialist: пригодный draft / reviewing_with_specialist
    resolving_automatically --> waiting_for_specialist: conflict или failure / escalated_to_specialist

    reviewing_with_specialist --> delivery_pending: оператор подтвердил ответ
    waiting_for_specialist --> delivery_pending: оператор подготовил ответ
    delivery_pending --> delivery_pending: retry с тем же event_id
    delivery_pending --> pending_customer: delivery confirmed / answered

    pending_customer --> accepted: customer reply / processing_cycle + 1
    pending_customer --> closed: configurable 24h timeout
    closed --> [*]
```

Таймаут 24 часа — явная product assumption, а не исходное требование. Будущий PoC моделирует оба
перехода из `pending_customer` через simulated clock или явную команду `advance`, без фонового
scheduler.

## End-to-end pipeline

Диаграмма показывает product-level decision flow и намеренно не раскрывает transport, persistence,
outbox, retry или worker topology. Узлы пользовательских статусов означают выбранный status outcome,
а не синхронный вызов внешнего channel provider. Reference implementation вынесена в отдельную
диаграмму [`docs/architecture.md`](architecture.md#reference-implementation-diagram).

```mermaid
flowchart TD
    user["Запрос пользователя"] --> ingress["Channel ingress<br/>chat · email · web · mobile"]

    subgraph sync["Синхронный hot path ≤ 500 ms"]
        ingress --> normalize["Validation и normalization"]
        normalize --> risk["PII redaction и risk detection"]
        risk --> classify["Intent classification<br/>и confidence"]
        classify --> routingPolicy{"RoutingPolicy"}
        routingPolicy -->|"automatic_resolution_candidate"| processingStatus["processing_automatically<br/>Подбираем решение"]
        routingPolicy -->|"human_review_required"| waitingStatus["waiting_for_specialist<br/>Обращение передано специалисту"]
    end

    subgraph resolution["Асинхронный resolution path"]
        resolver["LayeredAnswerResolver"] --> exact["1. Exact lookup<br/>intent · incident_id · locale"]
        exact -->|"eligible hit"| approvedExact["ApprovedAnswer<br/>approved_exact"]
        exact -->|"miss · ineligible"| semantic["2. Semantic search<br/>eligible approved KB only"]
        semantic -->|"reliable hit"| approvedSemantic["ApprovedAnswer<br/>approved_semantic"]
        semantic -->|"miss · stale · low confidence"| generation["3. Retrieval + generation"]
        generation --> generated["Generated draft + evidence"]
        generated --> safety["Grounding и safety checks"]
        safety --> generatedPolicy{"GeneratedResponsePolicy"}
    end

    subgraph humanPath["Асинхронный human-review path"]
        reviewQueue["Human review queue"] --> operator["Оператор проверяет<br/>и готовит ответ"]
    end

    routingPolicy -->|"automatic_resolution_candidate"| resolver
    routingPolicy -->|"human_review_required"| reviewQueue
    semantic -. "conflicting answers" .-> noDraftHandoff["human_review_without_draft"]
    generation -. "generation failure" .-> noDraftHandoff
    safety -. "safety failed" .-> noDraftHandoff

    approvedExact --> autoReply["auto_reply_sent"]
    approvedSemantic --> autoReply
    generatedPolicy -->|"auto_reply"| autoReply
    generatedPolicy -->|"operator_review_with_draft"| reviewPackage["Draft + evidence"]
    generatedPolicy -->|"human_review_without_draft"| noDraftHandoff

    reviewPackage --> reviewStatus["reviewing_with_specialist"]
    reviewStatus --> reviewQueue
    noDraftHandoff --> escalationStatus["escalated_to_specialist"]
    escalationStatus --> reviewQueue
    operator --> answered["answered<br/>Final support response"]
    autoReply --> answered

    resolver -. "match + content versions" .-> audit[("Audit log")]
    routingPolicy -. "route + reason" .-> audit
    generatedPolicy -. "action + gates" .-> audit
    reviewQueue -. "human route" .-> audit
    answered -. "final action" .-> audit
```

## Инварианты и fallback

- Сам факт обнаружения PII не запрещает automation: после успешной redaction safe-категория может
  продолжить flow. Sensitive или unredactable PII, risky intent и low confidence не входят в
  `LayeredAnswerResolver`.
- Exact lookup возвращает только active, актуальный и `auto_reply_eligible` content; остальные
  результаты считаются miss.
- Semantic lookup ищет в том же eligible candidate set и не отправляет match ниже подтверждённого
  confidence threshold.
- Lookup miss отличается от dependency outage. KB/semantic/LLM outage не блокирует приём тикета и
  fail closed переводит его в human fallback; недоступность не трактуется как обычный miss.
- Incident mode предпочитает versioned approved incident response/cache и не создаёт LLM-вызов на
  каждый дубликат.
- Каждый route, lookup/match, generated policy action, content/model version, delivery intent и
  подтверждённое итоговое действие оставляют audit record.
