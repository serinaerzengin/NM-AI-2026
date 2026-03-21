FROM python:3.13-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    httpx \
    python-dotenv \
    openai \
    openpyxl

COPY *.py ./

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8080"]
