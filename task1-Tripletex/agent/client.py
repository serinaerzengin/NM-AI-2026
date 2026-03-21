"""HTTP client for Tripletex API with time budget, state management, and placeholder resolution."""

import asyncio
import logging
import time

import httpx

logger = logging.getLogger("tripletex-agent.client")


class TripletexClient:
    def __init__(self, base_url: str, session_token: str):
        self.client = httpx.AsyncClient(
            base_url=base_url,
            auth=("0", session_token),
            timeout=30.0,
        )
        self.call_count = 0
        self.error_count = 0
        self.state: dict = {}
        self.call_log: list[dict] = []
        self.start_time = time.monotonic()

    def elapsed(self) -> float:
        return round(time.monotonic() - self.start_time, 1)

    def time_left(self, budget: float = 240.0) -> float:
        return round(budget - self.elapsed(), 1)

    async def call(self, method: str, path: str, json=None, params=None) -> dict:
        """Make an API call. Returns {"status": int, "data": dict}.
        Retries 5xx for GET/DELETE only (to avoid duplicate POST/PUT).
        """
        retries = 0 if method.upper() in ("POST", "PUT") else 2
        last_result: dict = {"status": 0, "data": {"error": "no_attempts"}}

        for attempt in range(1 + retries):
            t0 = time.monotonic()
            try:
                resp = await self.client.request(method, path, json=json, params=params)
                duration = time.monotonic() - t0
                self.call_count += 1
                self.call_log.append({
                    "method": method, "path": path,
                    "status": resp.status_code,
                    "duration_s": round(duration, 3),
                })

                try:
                    body = resp.json() if resp.content else {}
                except Exception:
                    body = {"raw": resp.text[:500]}

                last_result = {"status": resp.status_code, "data": body}

                if resp.status_code < 400:
                    return last_result

                self.error_count += 1
                if resp.status_code < 500:
                    return last_result  # 4xx → return so LLM can fix

                if attempt < retries:
                    await asyncio.sleep(1)
                    continue
                return last_result

            except httpx.HTTPError:
                self.call_count += 1
                self.error_count += 1
                self.call_log.append({
                    "method": method, "path": path,
                    "status": 0, "duration_s": round(time.monotonic() - t0, 3),
                    "error": "connection_error",
                })
                last_result = {"status": 0, "data": {"error": "connection_error"}}
                if attempt < retries:
                    await asyncio.sleep(1)

        return last_result

    def store(self, alias: str, response_data: dict):
        """Flatten response into state dict with auto-indexing.

        store("customer", {"id": 42, "name": "Acme"})
        → state = {"customer_0_id": 42, "customer_0_name": "Acme",
                    "customer_id": 42, "customer_name": "Acme"}
        """
        idx = 0
        while any(k.startswith(f"{alias}_{idx}_") for k in self.state):
            idx += 1
        actual = f"{alias}_{idx}"

        # Also register under normalized alias (strip _create, _post, _get suffixes)
        # so both $customer_create_id and $customer_id resolve
        short = alias
        for suffix in ("_create", "_post", "_search", "_get"):
            if short.endswith(suffix):
                short = short[:-len(suffix)]
                break

        for key, value in response_data.items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                self.state[f"{actual}_{key}"] = value
                if idx == 0:
                    self.state[f"{alias}_{key}"] = value
                    if short != alias:
                        self.state[f"{short}_{key}"] = value
            elif isinstance(value, dict) and "id" in value:
                self.state[f"{actual}_{key}_id"] = value["id"]
                if idx == 0:
                    self.state[f"{alias}_{key}_id"] = value["id"]
                    if short != alias:
                        self.state[f"{short}_{key}_id"] = value["id"]

    def resolve(self, payload):
        """Replace $placeholder strings with state values, preserving types."""
        if isinstance(payload, str):
            # Exact match → return actual type
            if payload.startswith("$") and payload[1:] in self.state:
                return self.state[payload[1:]]
            # Inline replacement
            if "$" in payload:
                result = payload
                for key in sorted(self.state, key=len, reverse=True):
                    ph = f"${key}"
                    if ph in result:
                        result = result.replace(ph, str(self.state[key]))
                return result
            return payload
        if isinstance(payload, dict):
            return {k: self.resolve(v) for k, v in payload.items()}
        if isinstance(payload, list):
            return [self.resolve(item) for item in payload]
        return payload

    async def close(self):
        await self.client.aclose()
