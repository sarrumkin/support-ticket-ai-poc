# ML/LLM design

**Статус:** Slice 4 реализует минимальный PoC baseline. Он доказывает связность flow и заменяемость
адаптеров, но не production ML quality.

## Реализованный baseline и путь замены

| Этап | PoC baseline | Упрощение и ограничение | Готовая альтернатива | Trigger замены |
|---|---|---|---|---|
| Contracts | Pydantic 2 + `typing.Protocol` | Один внутренний набор DTO, без wire compatibility | OpenAPI/JSON Schema или protobuf | Появление отдельных deployable services или внешних consumers |
| Normalization | `unicodedata.normalize`, `casefold`, whitespace cleanup | Нет typo correction и language detection | `ftfy` + language detector | Ошибки маршрутизации из-за encoding, опечаток или mixed-language input |
| PII | `scrubadub.Scrubber` | Форматные email/phone/card и подобные detectors; RU names/addresses не обещаются | Microsoft Presidio + custom RU recognizers/NER | Реальные данные, внешний provider или PII recall ниже утверждённого порога |
| Risk | Versioned keyword rules из JSON | Нет multi-label model; rules дают false positive/negative | Guardrails validators или fine-tuned classifier | Рост rule set, пропуски risky classes или неприемлемая ручная нагрузка |
| Intent | scikit-learn char TF-IDF + Logistic Regression | Только synthetic RU examples; probability не calibrated | SetFit/Transformers или domain fine-tuning | Размеченный dataset и per-intent quality target |
| Exact lookup | Versioned JSON → in-memory `dict` | Только точное совпадение нормализованной фразы, нет lifecycle/DB | SQLite, затем PostgreSQL | Редакторский workflow, concurrent updates или несколько replicas |
| Semantic search | `QdrantClient(":memory:")` + FastEmbed | Один процесс, без persistence, filters lifecycle и reranker | Qdrant service/pgvector + hybrid retrieval + reranker | KB перестаёт помещаться в процесс, нужны updates/HA или relevance target |
| Embeddings | multilingual MiniLM через FastEmbed/ONNX Runtime | Готовая multilingual model без domain tuning | Multilingual E5/BGE + offline evaluation/fine-tuning | Недостаточная retrieval quality или смена FastEmbed/model behavior |
| Generation | Groq SDK + `qwen/qwen3.6-27b`, JSON Object Mode, `temperature=0` | Preview provider model, один вызов без retry, нет strict JSON Schema | Self-hosted Qwen через vLLM или Groq GPT-OSS со strict schema | Privacy policy запрещает SaaS, model retirement, outage/cost/SLA |
| Validation | Pydantic + evidence subset + повторный PII scan | Нет semantic factuality/provenance model | Guardrails `DetectPII`/provenance validators | Generated drafts показывают unsupported claims или PII leakage |
| Dedup | SHA-256 нормализованного redacted text | Нет TTL/persistence и semantic clustering | Redis TTL cache или incident clustering | Несколько процессов, incident bursts или полезность fuzzy dedup доказана |
| Tests | pytest + injected fixture generator | Обязательный suite не проверяет сеть и production quality | Marked integration/evaluation suites | CI с secrets и стабильным evaluation dataset |

FastEmbed работает через ONNX Runtime и не требует PyTorch; выбранная multilingual MiniLM-модель
занимает порядка 220 MB. В проверенной версии FastEmbed используется mean pooling, и библиотека
предупреждает об изменении поведения относительно старых версий. Поэтому similarity threshold
`0.82` является demo constant: любое обновление FastEmbed/модели требует повторной оценки.

Qwen на Groq выбран владельцем вместо первоначально предложенного OpenAI provider. Для
`qwen/qwen3.6-27b` используется JSON Object Mode и локальная Pydantic-валидация: strict Structured
Outputs не предполагаются, а некорректный JSON немедленно даёт human fallback. Статус preview и
возможности модели нужно перепроверять перед каждым внешним pilot:
[Groq models](https://console.groq.com/docs/models),
[Structured Outputs](https://console.groq.com/docs/structured-outputs),
[FastEmbed](https://qdrant.tech/documentation/fastembed/).

## Replaceability contract

`TicketProcessor` импортирует только DTO и следующие interfaces:

- `PIIRedactor.redact(text) -> PIIRedactionResult`
- `RiskDetector.assess(text) -> RiskAssessment`
- `IntentClassifier.classify(text) -> IntentPrediction`
- `AnswerResolver.resolve(intent, text, locale) -> ResolutionResult`
- `TextGenerator.generate(request) -> GeneratedDraft`
- `DraftValidator.validate(draft, request) -> ValidationResult`

Concrete providers создаются в composition root `build_processor()`. Thresholds, embedding/model IDs
и generation provider приходят из `Settings`, а не из orchestration. Каждый результат несёт
`ComponentRef(provider, implementation, model, version)`, который попадает в audit. Поэтому
`FixtureGenerator` и `GroqQwenGenerator`, local Qdrant и будущий external vector store, Scrubadub и
будущий Presidio меняются без изменения ticket flow.

Через границы adapters проходят typed причины: `pii_uncertain`, `low_confidence`, `retrieval_miss`,
`provider_unavailable`, `invalid_output`, `safety_failed`. Для каждой причины существует
`human_review_without_draft`; generated text никогда не отправляется пользователю автоматически.

## Runtime flow

1. Pydantic валидирует вход; stdlib нормализует текст.
2. Scrubadub редактирует PII. Residual risk запрещает продолжение автоматического пути.
3. Versioned rules немедленно отправляют risky ticket оператору.
4. Synthetic scikit-learn classifier возвращает intent или abstains ниже demo threshold.
5. Resolver сначала делает exact lookup без embeddings, затем semantic lookup.
6. Approved exact/semantic answer может вернуть `auto_reply`; этот PoC только возвращает decision и
   не выполняет внешнюю отправку.
7. При miss generator получает только redacted ticket и retrieved evidence.
8. Pydantic, evidence allowlist и повторный PII scan проверяют draft.
9. Валидный draft получает `operator_review_with_draft`; любой отказ — human fallback без draft.

## Data, quality и честная граница

Все fixtures синтетические и русскоязычные. Intent confidence, semantic similarity и набор risk
keywords нужны только для демонстрации ветвления. Они не измеряют precision/recall, calibration,
robustness, fairness или production relevance. До pilot нужны versioned train/validation/test splits,
per-intent metrics, retrieval Recall@K/MRR, slice-based PII/risk evaluation и утверждённая стоимость
ошибок. Исторические ответы нельзя считать ground truth без редакторской проверки и защиты от leakage.
