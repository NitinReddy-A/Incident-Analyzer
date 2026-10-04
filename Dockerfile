FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    INCIDENT_ANALYZER_DATA_DIR=/app/data/sample

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY incident_analyzer ./incident_analyzer
RUN pip install ".[llm,server]"

COPY data ./data

RUN useradd --create-home --uid 10001 analyzer && chown -R analyzer /app
USER analyzer

EXPOSE 8050
CMD ["gunicorn", "--bind", "0.0.0.0:8050", "--workers", "2", "incident_analyzer.dashboard.app:create_server()"]
