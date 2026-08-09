# Slice Map

## Правила статусов

- `IN_PROGRESS` — текущий слайс; для него существует issue в GitHub Project.
- `BLOCKED` — продолжение невозможно без решения или внешнего изменения.
- `DONE` — результат проверен, checkpoint записан, следующий слайс не начат автоматически.

Карта содержит только фактически начатые или завершённые слайсы. Будущие слайсы заранее не
планируются и не добавляются как placeholders. Новый слайс появляется сразу со статусом
`IN_PROGRESS` после явного checkpoint владельца; одновременно для него создаётся issue. Несколько
активных слайсов допустимы только при явно независимых scopes или записанной dependency; у каждого
остаётся собственный checkpoint.

## Slice 1: Repository bootstrap

**Status:** `DONE`

**Issue:** [#1 — Slice 1: Repository bootstrap](https://github.com/sarrumkin/ai-hub-support-poc/issues/1)

**Goal:** создать управляемую структуру репозитория, правила работы, живой журнал решений и связь с
GitHub Project.

**Included:** обязательные AI-документы с содержательными skeleton-разделами, private GitHub repo,
repository-level Project link и один issue Slice 1.

**Not included:** код PoC, зависимости, Docker и issues для будущих слайсов.

**Verification:** проверить файлы и ссылки, Owner Context, Git history, private remote, Project link и
единственный slice issue.

**Checkpoint:** bootstrap завершён; следующий слайс не создаётся до отдельного решения владельца.

## Slice 2: Ticket processing flow

**Status:** `DONE`

**Issue:** [#2 — Slice 2: Ticket processing flow](https://github.com/sarrumkin/ai-hub-support-poc/issues/2)

**Goal:** определить end-to-end flow обработки тикета от ingress до ответа пользователю или передачи
оператору.

**Included:** sync/async boundaries, outcomes и пользовательские статусы, KB-first resolution,
generation и human fallbacks, минимальные response contracts и Mermaid pipeline.

**Not included:** реализация PoC, полная risk taxonomy, полный input/audit contract, выбор ML/LLM
baseline и production infrastructure.

**Verification:** непротиворечивый Mermaid flow, явные policy boundaries, корректные пользовательские
статусы, fallback для каждого отказа и согласованность связанных документов.

**Checkpoint:** processing contract прошёл review. Неоднозначности lifecycle, delivery semantics,
audit ordering и outage branches вынесены в явно согласованный Slice 3, а не скрыты как завершённые
production-решения.

## Slice 3: Architecture, capacity and latency

**Status:** `DONE`

**Issue:** [#3 — Slice 3: Architecture, capacity and latency](https://github.com/sarrumkin/ai-hub-support-poc/issues/3)

**Goal:** доработать target architecture на основе processing contract, определить lifecycle и
delivery semantics, рассчитать capacity/latency и получить честный локальный microbenchmark.

**Included:** отдельная lifecycle-диаграмма, input/routing/state/audit contracts, component boundaries,
надёжность доставки событий, capacity model, latency budget и synthetic hot-path microbenchmark.

**Not included:** production deployment, реальные ML/LLM, внешняя очередь или vector DB, а также
реализация risky/happy tracer paths.

**Verification:** Mermaid-диаграммы, consistency contracts, failure scenarios, capacity arithmetic и
stdlib benchmark с сохранёнными командами и результатами.

**Checkpoint:** product-level processing diagram возвращена к исходному простому flow; workers,
outbox и provider delivery оставлены только в отдельной reference implementation diagram. Обе схемы
прошли Mermaid rendering; следующий слайс не определяется автоматически.

## Slice 4: Minimal PoC ML baseline

**Status:** `DONE`

**Issue:** [#4 — Slice 4: Minimal PoC ML baseline](https://github.com/sarrumkin/ai-hub-support-poc/issues/4)

**Goal:** собрать минимальный сквозной ML PoC преимущественно из готовых библиотек, сохранив
заменяемые component contracts и честную evidence boundary.

**Included:** Pydantic contracts и Protocol interfaces, локальные PII/risk/intent adapters,
exact/semantic resolution, Groq/Qwen и offline fixture generators, fail-closed routing, audit, CLI,
smoke tests и документация упрощений.

**Not included:** production infrastructure, реальные данные, fine-tuning, calibrated thresholds,
полноценная RU PII NER, внешний broker/vector DB service и auto-send generated reply.

**Verification:** offline tests без API key, CLI paths exact/risky/generated, optional Groq integration
check, проверка заменяемости adapters и согласованности ML/risk/self-review документов.

**Checkpoint:** offline suite прошёл (`12 passed`, два explicit optional checks skipped), реальный
FastEmbed/Qdrant semantic check прошёл отдельно, CLI подтвердил exact/risky/generated outcomes.
Groq network check не запускался без API key и не входит в обязательный suite. Contracts и adapters
заменяемы, shortcuts/alternatives/Prod blockers записаны; следующий слайс не начинается автоматически.

## Slice 5: Async FastAPI PoC

**Status:** `DONE`

**Issue:** [#5 — Slice 5: Async FastAPI PoC](https://github.com/sarrumkin/ai-hub-support-poc/issues/5)

**Goal:** обернуть ML pipeline в минимальный HTTP PoC с быстрым `202`, background processing,
in-memory state, polling и Docker.

**Included:** FastAPI contracts, typed status history, `BackgroundTasks`, tests, readable API contract
и Docker packaging.

**Not included:** durable queue/database, SSE/WebSocket, реальные channel providers и production SLA.

**Verification:** offline pytest, API contract tests, Docker build и polling smoke-test.

**Checkpoint:** реализация, Docker polling smoke и полный suite завершены: `18 passed` с включёнными
local semantic и external Groq checks. Synthetic Groq probe вернул grounded operator-review draft за
`6.081s`; результаты и evidence boundary записаны в monitoring. Следующий слайс не начинается
автоматически.
