FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen

COPY src ./src
COPY templates ./templates

ENV PYTHONPATH=/app/src

CMD ["uv", "run", "uvicorn", "provisioning.main:app", "--host", "0.0.0.0", "--port", "8000"]