# Сторонние компоненты

Python-зависимости устанавливаются из PyPI и остаются под собственными лицензиями. Основные прямые
зависимости используют разрешительные лицензии MIT, Apache-2.0 или BSD-3-Clause; точные версии
определяются ограничениями в `pyproject.toml`.

Embedding model
[`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2)
скачивается при первом запуске semantic path и распространяется авторами под Apache-2.0. Модель не
включена в этот репозиторий. Groq используется только как опциональный внешний API provider; его
SDK и сервисные условия применяются отдельно.
