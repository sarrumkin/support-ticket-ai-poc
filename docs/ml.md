# ML/LLM design

**Статус:** skeleton; выбор PoC baseline намеренно открыт до Slice 2.

## Задачи, которые нужно разделить

- Normalization, PII detection, safety/risk rules и incident deduplication.
- Topic/intent classification и routing.
- Embeddings/retrieval по базе знаний и историческим решениям.
- Summarization или generation черновика ответа.
- Confidence estimation, abstention и передача оператору.

## Открытые решения

- Что в PoC реализовать правилами, classic ML, embeddings и LLM.
- Использовать offline TF-IDF baseline, local embedding model или optional external LLM adapter.
- Источники моделей и данных, схема разметки исторических тикетов и защита от leakage.
- Offline metrics, slice-based evaluation, thresholds и calibration low-confidence.
- Где LLM запрещён из-за latency, PII, nondeterminism или стоимости.

## Критерий готовности

Для каждой задачи должны быть обоснованы baseline, данные, технические метрики, failure mode и путь
низкой уверенности. Нельзя описывать LLM как универсальный компонент без сравнения с более простым
подходом.
