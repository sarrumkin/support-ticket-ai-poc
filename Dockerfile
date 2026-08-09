FROM python:3.13-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install --no-cache-dir . && useradd --create-home appuser

USER appuser
EXPOSE 8000
CMD ["sh", "-c", "uvicorn support_poc.api:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
