# ThreatAgent Dockerfile
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY common_lib /app/common_lib
COPY threat_agent /app/threat_agent

RUN pip install --no-cache-dir fastapi uvicorn[standard] httpx sqlalchemy asyncpg

CMD ["uvicorn", "threat_agent.app.main:app", "--host", "0.0.0.0", "--port", "8002"]

