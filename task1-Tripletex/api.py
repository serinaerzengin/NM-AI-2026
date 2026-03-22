import sys
import traceback
import os
import uuid

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from tripletex_client import TripletexClient
from file_handler import process_files
from apply_fixes import reset_bank_account_cache
from agent import run_agent

app = FastAPI()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/solve")
async def solve(request: Request):
    client = None
    req_id = uuid.uuid4().hex[:8]
    try:
        body = await request.json()

        prompt = body.get("prompt", "")
        files = body.get("files", [])

        # Log prompt for task identification
        prompt_preview = prompt[:800].replace('\n', ' ')
        print(f"[{req_id}][SOLVE] START prompt={prompt_preview}", file=sys.stderr)

        # Handle both credential formats
        creds = body.get("tripletex_credentials") or body.get("tripletex_api") or {}
        base_url = creds.get("base_url", "")
        session_token = creds.get("session_token", "") or creds.get("token", "")

        if not base_url or not session_token:
            print(f"[{req_id}][SOLVE] Missing credentials", file=sys.stderr)
            return JSONResponse({"status": "completed"})

        # Reset per-request state
        reset_bank_account_cache()

        # Create client
        client = TripletexClient(base_url, session_token, req_id)

        # Process files
        file_contents = await process_files(files) if files else []

        # Run agent
        result = await run_agent(prompt, file_contents, client, req_id)

        print(
            f"[{req_id}][SOLVE] Done: {result.get('api_calls', 0)} calls, "
            f"{result.get('errors', 0)} errors",
            file=sys.stderr,
        )

        return JSONResponse({"status": "completed"})

    except Exception as e:
        print(f"[{req_id}][SOLVE ERROR] {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return JSONResponse({"status": "completed"})

    finally:
        if client:
            try:
                await client.close()
            except Exception:
                pass
