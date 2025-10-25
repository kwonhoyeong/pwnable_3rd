# EPSSFetcher Dockerfile
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY common_lib /app/common_lib
COPY epss_fetcher /app/epss_fetcher

RUN pip install --no-cache-dir fastapi uvicorn[standard] httpx sqlalchemy asyncpg

CMD ["uvicorn", "epss_fetcher.app.main:app", "--host", "0.0.0.0", "--port", "8001"]

