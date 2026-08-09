# Slice Map

## Правила статусов

- `IN_PROGRESS` — текущий слайс; для него существует issue в GitHub Project.
- `BLOCKED` — продолжение невозможно без решения или внешнего изменения.
- `DONE` — результат проверен, checkpoint записан, следующий слайс не начат автоматически.

Карта содержит только фактически начатые или завершённые слайсы. Будущие слайсы заранее не
планируются и не добавляются как placeholders. Новый слайс появляется сразу со статусом
`IN_PROGRESS` после явного checkpoint владельца; одновременно для него создаётся issue. В каждый
момент активен не более чем один слайс.

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
