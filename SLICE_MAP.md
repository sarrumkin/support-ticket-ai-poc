# Slice Map

## Правила статусов

- `PLANNED` — граница обозначена, но реализация и отдельный issue ещё не начаты.
- `IN_PROGRESS` — текущий слайс; для него существует issue в GitHub Project.
- `BLOCKED` — продолжение невозможно без решения или внешнего изменения.
- `DONE` — результат проверен, checkpoint записан, следующий слайс не начат автоматически.

Статус меняется прямо в этом файле. Issue создаётся по мере необходимости только при старте слайса.

## Slice 1: Repository bootstrap

**Status:** `IN_PROGRESS`

**Goal:** создать управляемую структуру репозитория, правила работы, живой журнал решений и связь с
GitHub Project.

**Included:** обязательные AI-документы с содержательными skeleton-разделами, private GitHub repo,
repository-level Project link и один issue Slice 1.

**Not included:** код PoC, зависимости, Docker и issues для будущих слайсов.

**Verification:** проверить файлы и ссылки, Owner Context, Git history, private remote, Project link и
единственный slice issue.

**Checkpoint:** остановиться после bootstrap; Slice 2 остаётся `PLANNED`.

## Slice 2: Thin system design contract

**Status:** `PLANNED`

**Goal:** определить минимальные архитектурные, API, data и ML-контракты перед реализацией.

**Open questions:** risk taxonomy, входные/выходные схемы, audit record, PoC ML/LLM baseline,
confidence policy, persistence и способ моделирования async path.

**Verification:** непротиворечивые контракты, Mermaid data flow и явно закрытые decision gates.

**Checkpoint:** risky tracer path не начинается до согласования контрактов.

## Slice 3: Risky ticket tracer path

**Status:** `PLANNED`

**Goal:** провести risky или low-confidence mock-ticket от API/CLI до human review и audit log.

**Open questions:** конкретные rules/ML-компоненты, формат локального audit storage и fixture taxonomy.

**Verification:** unit/integration tests и воспроизводимый risky demo без автоматического ответа.

**Checkpoint:** согласовать audit evidence перед happy path.

## Slice 4: Happy ticket tracer path

**Status:** `PLANNED`

**Goal:** провести безопасный тикет через classification, retrieval и draft generation до audit log.

**Open questions:** retrieval baseline, knowledge base format, mock или реальный model adapter, пороги
confidence и способ показать асинхронную генерацию.

**Verification:** happy-path test, retrieval check, fallback test и demo обоих обязательных путей.

**Checkpoint:** подтвердить, что PoC доказывает архитектурную идею без production theater.

## Slice 5: Reliability, monitoring and economics

**Status:** `PLANNED`

**Goal:** закрыть highload, degradation, monitoring, model/input drift и cost-control решения.

**Open questions:** headroom для всплесков, стартовые alert thresholds, модель стоимости LLM и
минимальная latency/load verification для PoC.

**Verification:** проверенная арифметика assumptions и traceability метрик к исходной задаче.

**Checkpoint:** все эксплуатационные требования покрыты решением или явно записанным residual risk.

## Slice 6: Submission hardening

**Status:** `PLANNED`

**Goal:** сделать сдачу воспроизводимой и честно завершить документацию.

**Open questions:** способ финальной container-проверки и порядок выдачи проверяющему доступа к private
репозиторию.

**Verification:** чистый local/container run, smoke-test, два demo paths, diagram/link check, полный
`AI_USAGE.md` и финальный `SELF_REVIEW.md`.

**Checkpoint:** сдача готова только после воспроизведения инструкции из README с чистого окружения.
