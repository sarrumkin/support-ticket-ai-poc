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

**Status:** `IN_PROGRESS`

**Issue:** [#2 — Slice 2: Ticket processing flow](https://github.com/sarrumkin/ai-hub-support-poc/issues/2)

**Goal:** определить end-to-end flow обработки тикета от ingress до ответа пользователю или передачи
оператору.

**Included:** sync/async boundaries, outcomes и пользовательские статусы, KB-first resolution,
generation и human fallbacks, минимальные response contracts и Mermaid pipeline.

**Not included:** реализация PoC, полная risk taxonomy, полный input/audit contract, выбор ML/LLM
baseline и production infrastructure.

**Verification:** непротиворечивый Mermaid flow, явные policy boundaries, корректные пользовательские
статусы, fallback для каждого отказа и согласованность связанных документов.

**Checkpoint:** слайс находится в работе; следующий слайс будет определён только при фактической
необходимости после завершения или остановки этого scope.
