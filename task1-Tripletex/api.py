import json
import logging
from datetime import datetime, timezone
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from agent import run
from agent.logging_config import setup_logging, write_trace_json

setup_logging()
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
    run_id = uuid4().hex

    # Log the incoming task for analysis
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prompt": prompt,
        "files": [{"filename": f["filename"], "mime_type": f["mime_type"]} for f in files] if files else [],
    }
    logger.info(f"TASK_RECEIVED: {json.dumps(log_entry, ensure_ascii=False)}")
    write_trace_json(run_id, "TASK_RECEIVED", {
        "prompt": prompt,
        "files": log_entry["files"],
    })

    try:
        await run(
            prompt=prompt,
            base_url=body["tripletex_credentials"]["base_url"],
            session_token=body["tripletex_credentials"]["session_token"],
            files=files,
            run_id=run_id,
        )
        logger.info(f"TASK_COMPLETED: {prompt[:100]}")
        write_trace_json(run_id, "TASK_COMPLETED", {"prompt": prompt[:100]})
    except Exception as e:
        logger.error(f"TASK_FAILED: {prompt[:100]} — {e}")
        write_trace_json(run_id, "TASK_FAILED", {
            "prompt": prompt[:100],
            "error": str(e),
        })

    return JSONResponse({"status": "completed"})
