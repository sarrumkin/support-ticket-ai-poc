# Risks and operations

## Реализованные PoC controls

- До generation выполняются normalization, PII redaction, risk rules и confidence abstention.
- Risky, residual-PII и low-confidence tickets fail closed в `human_review_without_draft`.
- External generator получает только redacted synthetic text и allowlisted retrieved evidence.
- Generated evidence refs проверяются как subset входного evidence; draft повторно сканируется на PII.
- Каждый вызванный adapter оставляет `ComponentRef` и route reason в audit.
- Provider/contract/validation failure не возвращает draft и не блокирует приём тикета.
- Generated draft никогда не auto-send; PoC вообще не выполняет user-visible delivery.

## Известные упрощения и Prod blockers

| Риск | Текущее ограничение | Необходимое Prod-действие |
|---|---|---|
| RU PII leakage | Scrubadub не обещает распознавание русских имён, адресов и контекстных идентификаторов | Presidio/custom RU NER, adversarial evaluation, retention/access policy |
| Intent error | Synthetic examples и demo threshold `0.45`, confidence не calibrated | Размеченные реальные данные, temporal split, per-intent calibration/abstention |
| Risk miss | Небольшой keyword denylist, без taxonomy/evaluation | Утвердить taxonomy и cost matrix, добавить classifier/validators и human QA |
| Semantic false match | Threshold `0.82` не калиброван; FastEmbed pooling behavior зависит от версии | Зафиксировать model artifact, собрать relevance set, оценить Recall@K/precision и reranker |
| Stale/conflicting KB | JSON загружается при старте, нет lifecycle и редакторских статусов | Versioned KB store, owner/expiry, conflict checks и rollout/rollback |
| External provider privacy | Groq SaaS разрешён только для synthetic redacted PoC; policy/retention не проверены для реальных данных | DPA/privacy review либо self-hosted Qwen; network egress allowlist и audit |
| Provider/model instability | Qwen model отмечен preview, нет retry/circuit breaker/cost cap | Проверка availability/SLA, bounded retries, circuit breaker, budget и fallback model |
| Invalid/unsupported draft | JSON/evidence allowlist не доказывают factuality | Provenance/factuality evaluation, operator feedback loop, prompt-injection tests |
| In-memory state | Qdrant index и dedup key не persistent и не shared | External vector store, Redis/DB, backups, HA и consistency policy |
| Auto-reply quality | Exact/semantic decision реализован, но production error budget отсутствует | Pilot с approved candidate set, CSAT/reopen/safety guardrails и rollback switch |

## Надёжность и target design

- Sync classification/routing проектируется на `p95 <= 500 ms` и target `66.7 ticket/s` (`2x`
  observed peak). Реальный ML path этим слайсом под load не проверялся.
- Retrieval/generation остаются async target path. При LLM outage сохраняются deterministic routing и
  human fallback; generation retries не должны задерживать acknowledgement.
- Target implementation создаёт state transition, audit и outbox атомарно. Events обрабатываются
  `at-least-once` со стабильным `event_id`, delivery ledger и provider idempotency key, где доступен.
- Lookup miss нельзя смешивать с dependency outage. В PoC adapter failures типизированы, но circuit
  breaker, retry budget и dependency health остаются target design.
- Knowledge и пользовательский текст считаются недоверенными относительно prompt injection.
  Provider prompt отдельно говорит, что evidence — данные, а не инструкции; полноценной защиты это не
  доказывает.

## Operational stop conditions

До работы с реальными ticket data запрещены внешний LLM и auto-send, пока не утверждены data policy,
quality thresholds и rollback. Pilot нужно остановить или сузить, если растут safety incidents,
PII leakage, reopen/SLA breach или operator correction rate относительно контроля. Конкретные пороги
должны быть определены на pilot data, а не выбраны из PoC fixtures.

## Ограничение evidence

Slice 3 benchmark измеряет только deterministic orchestration ceiling. Slice 4 smoke tests доказывают
ветвление, fail-closed behavior и совместимость локального semantic stack. Ни один результат не
подтверждает production throughput, replica count или ML quality.
