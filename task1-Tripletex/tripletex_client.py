import asyncio
import time
import httpx


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
        """Seconds since client was created."""
        return round(time.monotonic() - self.start_time, 1)

    def time_left(self, budget: float = 240.0) -> float:
        """Seconds remaining from budget (default 4 minutes)."""
        return round(budget - self.elapsed(), 1)

    async def call(self, method: str, path: str, json=None, params=None, retries: int | None = None) -> dict:
        """Make an API call with retry logic. Returns {"status": int, "data": dict}.
        Retries default to 2 for GET/DELETE, 0 for POST/PUT (to avoid duplicates).
        """
        if retries is None:
            retries = 0 if method.upper() in ("POST", "PUT") else 2
        last_result: dict = {"status": 0, "data": {"error": "no_attempts"}}
        for attempt in range(1 + retries):
            t0 = time.monotonic()
            try:
                resp = await self.client.request(method, path, json=json, params=params)
                duration = time.monotonic() - t0
                self.call_count += 1
                self.call_log.append({
                    "method": method,
                    "path": path,
                    "status": resp.status_code,
                    "duration_s": round(duration, 3),
                    "attempt": attempt + 1,
                })

                try:
                    body = resp.json() if resp.content else {}
                except Exception:
                    body = {"raw": resp.text[:500]}
                last_result = {"status": resp.status_code, "data": body}

                if resp.status_code < 400:
                    return last_result

                # Error path
                self.error_count += 1

                # 4xx = bad request → return immediately so LLM can read the error and fix it
                if resp.status_code < 500:
                    return last_result

                # 5xx = server error → retry if we have attempts left
                if attempt < retries:
                    await asyncio.sleep(1)
                    continue
                return last_result

            except httpx.HTTPError:
                duration = time.monotonic() - t0
                self.call_count += 1
                self.error_count += 1
                self.call_log.append({
                    "method": method,
                    "path": path,
                    "status": 0,
                    "duration_s": round(duration, 3),
                    "attempt": attempt + 1,
                    "error": "connection_error",
                })
                last_result = {"status": 0, "data": {"error": "connection_error"}}
                if attempt < retries:
                    await asyncio.sleep(1)
                    continue

        return last_result

    def store(self, alias: str, response_data: dict):
        """Flatten response fields into state dict with alias prefix.

        - Simple values (str, int, float, bool) stored directly
        - Nested objects: extracts 'id' if present (e.g. customer.currency.id → alias_currency_id)
        - Auto-indexes: if alias already exists, appends _1, _2, etc.

        e.g. store("customer", {"id": 42, "name": "Acme", "currency": {"id": 1}})
        → state = {"customer_0_id": 42, "customer_0_name": "Acme", "customer_0_currency_id": 1}

        Second call: store("customer", {"id": 55, "name": "Other"})
        → adds: {"customer_1_id": 55, "customer_1_name": "Other"}
        """
        # Auto-index: find next available index for this alias
        idx = 0
        prefix_pattern = f"{alias}_{idx}_"
        while any(k.startswith(prefix_pattern) for k in self.state):
            idx += 1
            prefix_pattern = f"{alias}_{idx}_"
        actual_alias = f"{alias}_{idx}"

        for key, value in response_data.items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                self.state[f"{actual_alias}_{key}"] = value
                # Also store without index for first item (so $customer_id works too)
                if idx == 0:
                    self.state[f"{alias}_{key}"] = value
            elif isinstance(value, dict) and "id" in value:
                self.state[f"{actual_alias}_{key}_id"] = value["id"]
                if idx == 0:
                    self.state[f"{alias}_{key}_id"] = value["id"]

    def resolve(self, payload) -> dict | list | str | int | float | bool | None:
        """Replace $placeholder strings in a nested structure with state values.

        - Exact match: "$customer_0_id" → 42 (returns the actual type)
        - Inline match: "/customer/$customer_0_id" → "/customer/42" (returns string)
        """
        if isinstance(payload, str):
            # Exact match — return the actual value (preserves type)
            if payload.startswith("$") and payload[1:] in self.state:
                return self.state[payload[1:]]
            # Inline replacement — replace all $placeholders within the string
            # Sort by key length descending so $customer_0_id is replaced before $customer_0
            if "$" in payload:
                result = payload
                for key in sorted(self.state, key=len, reverse=True):
                    placeholder = f"${key}"
                    if placeholder in result:
                        result = result.replace(placeholder, str(self.state[key]))
                return result
            return payload
        if isinstance(payload, dict):
            return {k: self.resolve(v) for k, v in payload.items()}
        if isinstance(payload, list):
            return [self.resolve(item) for item in payload]
        return payload

    async def close(self):
        await self.client.aclose()
