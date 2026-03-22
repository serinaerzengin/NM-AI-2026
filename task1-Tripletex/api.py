import base64
import json
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

_GCS_BUCKET = "tripletex-task-files-1813"


def _upload_to_gcs(req_id: str, prompt: str, files: list):
    """Upload task prompt + files to GCS. Non-blocking, non-fatal."""
    try:
        from google.cloud import storage
        client = storage.Client()
        bucket = client.bucket(_GCS_BUCKET)

        # Upload prompt
        bucket.blob(f"{req_id}/prompt.txt").upload_from_string(prompt)

        # Upload each file (decoded from base64)
        for f in files:
            fname = f.get("filename", "unknown")
            content_b64 = f.get("content_base64", "")
            mime = f.get("mime_type", "application/octet-stream")
            if content_b64:
                raw = base64.b64decode(content_b64)
                blob = bucket.blob(f"{req_id}/{fname}")
                blob.upload_from_string(raw, content_type=mime)

        print(f"[{req_id}][GCS] Uploaded {len(files)} file(s) to gs://{_GCS_BUCKET}/{req_id}/", file=sys.stderr)
    except Exception as e:
        print(f"[{req_id}][GCS] Upload error (non-fatal): {e}", file=sys.stderr)


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

        # Save incoming files locally + upload to GCS for persistent access
        if files:
            save_dir = os.path.join(os.path.dirname(__file__), "received_tasks", req_id)
            try:
                os.makedirs(save_dir, exist_ok=True)
                with open(os.path.join(save_dir, "prompt.txt"), "w") as pf:
                    pf.write(prompt)
                file_meta = []
                for f in files:
                    fname = f.get("filename", "unknown")
                    content_b64 = f.get("content_base64", "")
                    mime = f.get("mime_type", "unknown")
                    if content_b64:
                        raw = base64.b64decode(content_b64)
                        file_path = os.path.join(save_dir, fname)
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)
                        with open(file_path, "wb") as out:
                            out.write(raw)
                        file_meta.append({"filename": fname, "mime_type": mime, "size_bytes": len(raw)})
                        print(f"[{req_id}][FILES] Saved {fname} ({mime}, {len(raw)} bytes)", file=sys.stderr)
                with open(os.path.join(save_dir, "metadata.json"), "w") as mf:
                    json.dump({"req_id": req_id, "files": file_meta}, mf, indent=2)
            except Exception as e:
                print(f"[{req_id}][FILES] Local save error (non-fatal): {e}", file=sys.stderr)

            # Upload to GCS for persistent access
            _upload_to_gcs(req_id, prompt, files)

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
