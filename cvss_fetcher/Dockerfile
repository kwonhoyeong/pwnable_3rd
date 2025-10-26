# CVSSFetcher 개발용 Dockerfile(Development Dockerfile)
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# 소스코드는 개발 시 볼륨으로 마운트됨(Source code mounted as volume during development)

CMD ["uvicorn", "cvss_fetcher.app.main:app", "--host", "0.0.0.0", "--port", "8005"]
