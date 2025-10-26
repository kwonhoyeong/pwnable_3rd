# MappingCollector 개발용 Dockerfile(Development Dockerfile)
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 의존성 선행 설치(Preinstall shared dependencies)
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# 소스코드는 docker-compose 볼륨으로 마운트됩니다(Source code is mounted via docker-compose volume)

CMD ["uvicorn", "mapping_collector.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
