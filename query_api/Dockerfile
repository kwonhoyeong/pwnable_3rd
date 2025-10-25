# QueryAPI Dockerfile
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY common_lib /app/common_lib
COPY query_api /app/query_api

RUN pip install --no-cache-dir fastapi uvicorn[standard] sqlalchemy asyncpg aioredis

CMD ["uvicorn", "query_api.app.main:app", "--host", "0.0.0.0", "--port", "8004"]

