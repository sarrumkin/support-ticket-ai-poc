# Self-review

> Живой документ. Slice 4 добавил работающий ML tracer, но его evidence нельзя переносить на
> production quality.

## Самая слабая часть сейчас

PoC доказывает end-to-end flow, fail-closed routing и заменяемость adapters, но использует synthetic
данные и demo thresholds. Самая слабая часть — отсутствие offline evaluation на представительной
разметке: scenario catalog расширяет покрытие outcomes и audit-инвариантов, но его control adapters
детерминированно задают dependency results. Эти tests проверяют contracts и ветвление, а не качество
ML или semantic relevance.

## Сделанные assumptions

- Общий timebox — 6–8 часов.
- Реализация минимальна и локально воспроизводима без API key.
- Production queues, vector DB, feature store и MLOps останутся target design.
- Синтетические fixtures достаточны для проверки связности PoC, но не для вывода о production quality.

## Нерешённые риски

- Scrubadub может пропускать RU names/addresses и контекстный PII.
- Intent/semantic thresholds не calibrated, а FastEmbed pooling behavior зависит от версии.
- Preview Qwen/Groq не прошёл privacy, outage, cost и SLA review для реальных данных.
- Нет end-to-end load evidence для реального ML path и operator feedback loop.

## Вопросы финального self-review

- Что можно улучшить за два дополнительных дня?
- Что необходимо перед production-запуском?
- Какие категории нельзя автоматизировать полностью?
- Какие данные пилота заставят остановить проект?

Stop condition: проект нельзя расширять до generated auto-reply или реальных внешних вызовов, пока
не завершены privacy review и quality calibration. Pilot нужно остановить, если он показывает
статистически или операционно значимое ухудшение CSAT, reopen rate, SLA breach rate либо safety
incidents относительно контрольного процесса. Конкретные пороги должны быть обоснованы в следующих
слайсах.
