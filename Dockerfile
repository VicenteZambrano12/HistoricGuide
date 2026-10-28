FROM node:24-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.14-slim AS backend-build
COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --locked --no-dev --no-install-project --python /usr/local/bin/python

FROM python:3.14-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/backend/.venv/bin:$PATH" \
    ENV=GCP \
    PORT=8080
WORKDIR /app/backend
RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app
COPY --from=backend-build /app/backend/.venv ./.venv
COPY backend/src/ ./src/
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist
USER 10001:10001
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn src.container:create_app --factory --host 0.0.0.0 --port \"${PORT:-8080}\" --workers 1 --no-access-log"]
