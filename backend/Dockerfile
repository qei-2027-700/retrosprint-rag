# Development only. Keep Python/uv aligned with mise.toml and uv_build.
FROM python:3.13.5-slim-bookworm@sha256:4c2cf9917bd1cbacc5e9b07320025bdb7cdf2df7b0ceaccb55e9dd7e30987419
COPY --from=ghcr.io/astral-sh/uv:0.8.15@sha256:a5727064a0de127bdb7c9d3c1383f3a9ac307d9f2d8a391edc7896c54289ced0 /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /app/backend

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project
COPY src ./src
COPY scripts ./scripts
COPY tests ./tests
RUN uv sync --locked

EXPOSE 8000
CMD ["uvicorn", "retrosprint_rag.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "src", "--reload-dir", "scripts"]
