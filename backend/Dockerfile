FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

# LOCAL_EMBED=true adds fastembed for local Qdrant (no cloud inference). Production leaves it off.
ARG LOCAL_EMBED=false
COPY requirements.txt .
RUN pip install -r requirements.txt && \
    if [ "$LOCAL_EMBED" = "true" ]; then pip install "fastembed>=0.7"; fi

COPY app ./app
RUN useradd --create-home appuser && mkdir -p /app/.cache && chown appuser /app/.cache
USER appuser

# Render sets $PORT; default 8000 elsewhere.
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
