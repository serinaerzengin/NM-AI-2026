import httpx
import sys
import json


class TripletexClient:
    def __init__(self, base_url: str, session_token: str, req_id: str = "????"):
        # Strip trailing /v2 if present — we add it in call()
        self.base_url = base_url.rstrip("/")
        if self.base_url.endswith("/v2"):
            self.base_url = self.base_url[:-3]

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            auth=("0", session_token),
            timeout=25.0,
        )
        self.call_count = 0
        self.error_count = 0
        self.req_id = req_id

    async def call(self, method: str, path: str, json_data=None, params=None) -> dict:
        self.call_count += 1
        url = f"/v2{path}" if not path.startswith("/v2") else path
        try:
            response = await self.client.request(
                method, url, json=json_data, params=params
            )
            if response.status_code >= 400:
                self.error_count += 1
                print(
                    f"[{self.req_id}][API {response.status_code}] {method} {path}: {response.text[:500]}",
                    file=sys.stderr,
                )
            try:
                data = response.json()
            except Exception:
                data = {"raw": response.text[:2000]}
            return {"status": response.status_code, "data": data}
        except httpx.TimeoutException:
            self.error_count += 1
            print(f"[{self.req_id}][TIMEOUT] {method} {path}", file=sys.stderr)
            return {"status": 504, "data": {"error": "Request timed out after 25s"}}
        except Exception as e:
            self.error_count += 1
            print(f"[{self.req_id}][ERROR] {method} {path}: {e}", file=sys.stderr)
            return {"status": 500, "data": {"error": str(e)}}

    async def close(self):
        await self.client.aclose()
