FROM node:22-bookworm-slim AS frontend

WORKDIR /build

COPY package.json package-lock.json ./
COPY app/static ./app/static

RUN mkdir -p app/static/vendor && npm ci


FROM python:3.12-slim-trixie

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client-17 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY worker ./worker
COPY alembic ./alembic
COPY alembic.ini ./

COPY --from=frontend /build/app/static/vendor ./app/static/vendor

RUN mkdir -p uploads logs

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
