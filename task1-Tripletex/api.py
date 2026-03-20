import json
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# TODO: import agent entry point once built, e.g.:
# from agent import run

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tripletex-agent")

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/solve")
async def solve(request: Request):
    body = await request.json()
    prompt = body["prompt"]
    files = body.get("files", [])

    # Log the incoming task for analysis
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt": prompt,
        "files": [{"filename": f["filename"], "mime_type": f["mime_type"]} for f in files] if files else [],
    }
    logger.info(f"TASK_RECEIVED: {json.dumps(log_entry, ensure_ascii=False)}")

    try:
        await run(
            prompt=prompt,
            base_url=body["tripletex_credentials"]["base_url"],
            session_token=body["tripletex_credentials"]["session_token"],
            files=files,
        )
        logger.info(f"TASK_COMPLETED: {prompt[:100]}")
    except Exception as e:
        logger.error(f"TASK_FAILED: {prompt[:100]} — {e}")

    return JSONResponse({"status": "completed"})
