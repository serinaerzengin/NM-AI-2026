FROM python:3.13-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    httpx \
    python-dotenv \
    openai

COPY api.py agent.py llm.py tripletex_client.py context.py validator.py file_handler.py ./
COPY specs/ specs/

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8080"]
