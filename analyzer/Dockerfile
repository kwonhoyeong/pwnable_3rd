# Analyzer Dockerfile
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY common_lib /app/common_lib
COPY analyzer /app/analyzer

RUN pip install --no-cache-dir fastapi uvicorn[standard] httpx sqlalchemy asyncpg

CMD ["uvicorn", "analyzer.app.main:app", "--host", "0.0.0.0", "--port", "8003"]

