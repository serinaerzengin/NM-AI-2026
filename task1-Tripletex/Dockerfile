FROM python:3.13-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    openai-agents \
    httpx \
    python-dotenv \
    litellm

COPY core/ core/
COPY thomas/ thomas/
COPY docs/openapi.json docs/openapi.json
COPY api.py .

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8080"]
