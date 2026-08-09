# HTTP API contract PoC

**Граница:** это demo transport Slice 5, а не production delivery. Состояние хранится in-memory,
задачи выполняются `FastAPI BackgroundTasks`, API запускается с одним worker. Restart теряет jobs.

## Flow

1. `POST /tickets` возвращает `202`, `Location` и начальный `processing_automatically`.
2. Полный синхронный `TicketProcessor` Slice 4 выполняется в background task.
3. Demo-клиент опрашивает `GET /tickets/{ticket_id}` с интервалом из `Retry-After`.

## Endpoints

### `POST /tickets`

Request:

```json
{"ticket_id":"demo-1","content":"Где мой заказ?","locale":"ru","channel":"web"}
```

Response `202`:

```json
{"ticket_id":"demo-1","trace_id":"uuid","current_status":"processing_automatically","status_url":"/tickets/demo-1"}
```

Duplicate `ticket_id` возвращает `409`, invalid body — `422`.

### `GET /tickets/{ticket_id}`

Возвращает `job_status`, `current_status`, timestamped `status_history` и optional существующий
`ProcessingResult`. Unknown ticket возвращает `404`.

Outcome mapping:

| Processing outcome/reason | Final PoC status |
|---|---|
| `auto_reply` | `answered` |
| `operator_review_with_draft` | `reviewing_with_specialist` |
| risky / PII / low confidence | `waiting_for_specialist` |
| retrieval/provider/safety failure | `escalated_to_specialist` |

`answered` здесь означает, что answer доступен polling-клиенту; реальный channel confirmation не
реализован. `channel` — metadata и не влияет на ML или доставку.

### `GET /health`

Показывает liveness, generator mode и явные `in_memory` / `polling_demo` limitations. Интерактивная
OpenAPI-схема доступна в `/docs`.
