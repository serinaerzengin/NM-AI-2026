FROM python:3.13-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    httpx \
    python-dotenv \
    openai \
    openai-agents \
    openpyxl \
    pdfplumber \
    google-cloud-storage

COPY *.py ./
COPY *.json ./
COPY skills/ ./skills/

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8080"]
