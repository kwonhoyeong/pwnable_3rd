# MappingCollector Dockerfile
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY common_lib /app/common_lib
COPY mapping_collector /app/mapping_collector

RUN pip install --no-cache-dir fastapi uvicorn[standard] httpx sqlalchemy asyncpg aioredis

CMD ["uvicorn", "mapping_collector.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

