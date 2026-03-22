import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field

from openai import AsyncOpenAI
from agents import (
    Agent,
    OpenAIChatCompletionsModel,
    RunContextWrapper,
    Runner,
    RunHooks,
    ModelSettings,
    function_tool,
    set_tracing_disabled,
)
from agents.items import ModelResponse

from apply_fixes import apply_fixes, ensure_bank_account, create_employment
from system_prompt import build_system_prompt
from tripletex_client import TripletexClient, ProxyTokenExpiredError


# Disable tracing (we're not using OpenAI's tracing infrastructure)
set_tracing_disabled(True)

# Suppress noisy httpx/openai INFO logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

# === STYRK occupation code lookup (static, since Tripletex endpoint is [BETA]/403) ===

_styrk_codes: dict[str, str] | None = None


def _load_styrk_codes() -> dict[str, str]:
    global _styrk_codes
    if _styrk_codes is None:
        path = os.path.join(os.path.dirname(__file__), "styrk_codes.json")
        with open(path) as f:
            _styrk_codes = json.load(f)
    return _styrk_codes


def styrk_lookup(query: str) -> list[dict]:
    """Search STYRK-08 codes by code number or Norwegian name. Returns top matches."""
    codes = _load_styrk_codes()
    query_lower = query.lower()
    results = []
    # Exact code match
    if query in codes:
        results.append({"code": query, "name": codes[query]})
    # Partial code or name match
    for code, name in codes.items():
        if code == query:
            continue
        if query_lower in name.lower() or query_lower in code:
            results.append({"code": code, "name": name})
        if len(results) >= 10:
            break
    return results


# === Skills: load on-demand guidance from markdown files ===

_skills_cache: dict[str, str] = {}
_SKILLS_DIR = os.path.join(os.path.dirname(__file__), "skills")


def _load_skill(name: str) -> str:
    """Load a skill file once, cache for subsequent calls."""
    if name not in _skills_cache:
        path = os.path.join(_SKILLS_DIR, f"{name}.md")
        try:
            with open(path) as f:
                _skills_cache[name] = f.read()
        except FileNotFoundError:
            _skills_cache[name] = ""
    return _skills_cache[name]


# === Run Logger: buffers all logs per request, flushes as ONE structured entry ===

class RunLogger:
    def __init__(self, req_id: str):
        self.req_id = req_id
        self.lines: list[str] = []
        self.start_time = 0.0

    def _elapsed(self) -> str:
        if not self.start_time:
            return "0.0s"
        return f"{time.time() - self.start_time:.1f}s"

    def log(self, msg: str):
        self.lines.append(f"[{self._elapsed()}] {msg}")

    def flush(self, summary: str):
        """Emit entire run trace as a single multi-line log entry to stderr."""
        header = f"[{self.req_id}] {summary}"
        trace = "\n".join(self.lines)
        # Print as ONE multi-line block to stderr — Cloud Run groups by write call
        print(f"\n{'='*60}\n{header}\n{'='*60}\n{trace}\n{'='*60}\n", file=sys.stderr, flush=True)


# === Context: shared state for the entire task run ===

@dataclass
class TaskContext:
    client: TripletexClient
    req_id: str = "????"
    get_cache: dict = field(default_factory=dict)
    skills_shown: set = field(default_factory=set)
    turn_count: int = 0
    start_time: float = 0.0
    logger: RunLogger = field(default=None)
    write_lock: asyncio.Lock = field(default_factory=asyncio.Lock)  # Serialize writes — Gemini ignores parallel_tool_calls=False


# === Logging Hooks ===

class LoggingHooks(RunHooks[TaskContext]):
    async def on_llm_start(self, context, agent, system_prompt, input_items):
        c = context.context
        turn = c.turn_count
        c.turn_count += 1
        c.logger.log(f"--- TURN {turn} ---")

    async def on_llm_end(self, context, agent, response: ModelResponse):
        c = context.context
        for item in response.output:
            typ = getattr(item, 'type', '?')
            if typ == 'message':
                texts = [ct.text for ct in item.content if hasattr(ct, 'text')]
                if texts:
                    c.logger.log(f"  LLM: {' '.join(texts)[:400]}")
            elif typ == 'reasoning':
                summaries = getattr(item, 'summary', [])
                for s in summaries:
                    c.logger.log(f"  THINK: {getattr(s, 'text', str(s))[:300]}")
            elif typ == 'function_call':
                c.logger.log(f"  CALL: {item.name}({item.arguments[:400]})")

    async def on_tool_end(self, context, agent, tool, result):
        c = context.context
        snippet = result[:80] if result else ""
        if '"status": 4' in snippet or '"status": 5' in snippet or "VALIDATION ERROR" in snippet:
            status = "ERR"
        elif '"status": 2' in snippet:
            status = "OK"
        else:
            status = "ok"
        c.logger.log(f"  => {tool.name} {status} ({len(result)} chars)")


# === Cache invalidation ===

def _invalidate_cache(cache: dict, mutated_path: str):
    """Clear GET cache entries related to a mutated resource path."""
    parts = mutated_path.strip("/").split("/")
    # Use first TWO segments for precise invalidation (e.g. /ledger/voucher not /ledger/*)
    if len(parts) >= 2:
        prefix = "/" + parts[0] + "/" + parts[1]
    else:
        prefix = "/" + parts[0] if parts else ""
    to_remove = [k for k in cache if k.startswith(prefix)]
    for k in to_remove:
        del cache[k]


# === Response helpers ===

def _slim_account(acct: dict) -> dict:
    return {k: acct[k] for k in ("id", "number", "name") if k in acct}


_POSTING_FIELDS = ("id", "row", "account", "amountGross", "amountGrossCurrency",
                   "description", "vatType", "currency", "supplier", "customer")


# IMPORTANT: Order matters — more-specific patterns MUST come first
# because matching uses `pattern in path` (substring match)
_SLIM_FIELDS = [
    ("salary/type", ("id", "number", "name")),
    ("travelExpense/costCategory", ("id", "name", "description", "amountNOK")),
    ("travelExpense/rateCategory", ("id", "name", "type", "amountDomestic")),
    ("travelExpense/paymentType", ("id", "description")),
    ("/supplierInvoice", ("id", "invoiceNumber", "amount", "amountOutstanding", "invoiceDate", "supplier")),
    ("/employee", ("id", "firstName", "lastName", "email", "dateOfBirth", "department", "companyId")),
    ("/invoice", ("id", "invoiceNumber", "amount", "amountOutstanding", "amountCurrency", "invoiceDate", "dueDate", "customer", "isCreditNote")),
    ("/customer", ("id", "name", "organizationNumber", "email", "isCustomer")),
    ("/supplier", ("id", "name", "organizationNumber", "email", "isSupplier")),
]


def _slim_values(values: list, path: str) -> list:
    if "/ledger/account" in path:
        return [_slim_account(v) for v in values]
    if "/ledger/posting" in path:
        return [
            {k: (_slim_account(v[k]) if k == "account" and isinstance(v.get(k), dict) else v[k])
             for k in _POSTING_FIELDS if k in v}
            for v in values
        ]
    # Slim large reference data responses to just the fields the LLM needs
    for pattern, fields in _SLIM_FIELDS:
        if pattern in path:
            return [{k: v.get(k) for k in fields if v.get(k) is not None} for v in values]
    return values


def _truncate_response(data, path="") -> str:
    if isinstance(data, dict):
        inner = data.get("data", data)
        if isinstance(inner, dict):
            values = inner.get("values")
            if isinstance(values, list):
                inner = dict(inner)
                if "vatType" in path:
                    filtered = [v for v in values if v.get("id", 999) < 100]
                    inner["values"] = filtered
                    inner["_note"] = f"Showing {len(filtered)} standard VAT types (id < 100)"
                else:
                    full_size = inner.get("fullResultSize", len(values))
                    inner["values"] = _slim_values(values, path)
                    if full_size > len(values):
                        inner["_note"] = f"Showing {len(values)} of {full_size} total. Use from=N&count=N for more."
                if "data" in data:
                    data = dict(data)
                    data["data"] = inner
                else:
                    data = inner

            value = inner.get("value")
            if isinstance(value, dict) and "/ledger/account" in path:
                inner = dict(inner)
                inner["value"] = _slim_account(value)
                if "data" in data:
                    data = dict(data)
                    data["data"] = inner
                else:
                    data = inner

    return json.dumps(data, ensure_ascii=False, default=str)


def _extract_employee_id(payload) -> int | None:
    for ps in payload.get("payslips", []):
        emp = ps.get("employee", {})
        if isinstance(emp, dict) and emp.get("id"):
            return emp["id"]
    return None


# === Tools ===

@function_tool
async def tripletex_get(ctx: RunContextWrapper[TaskContext], path: str, params: str = "{}") -> str:
    """GET from Tripletex API. See system prompt for endpoint patterns.
Args: path: API endpoint path. params: Query parameters as JSON string."""
    client = ctx.context.client
    log = ctx.context.logger

    # Cache duplicate GETs
    cache_key = f"{path}:{params}"
    if cache_key in ctx.context.get_cache:
        log.log(f"  GET {path} (CACHED)")
        return ctx.context.get_cache[cache_key]

    parsed_params = None
    if params and params != "{}":
        try:
            parsed_params = json.loads(params) if isinstance(params, str) else params
        except (json.JSONDecodeError, TypeError):
            pass

    # Extract query params from URL — httpx drops them when a params dict is passed
    if "?" in path:
        from urllib.parse import urlparse, parse_qs
        parsed_url = urlparse(path)
        path = parsed_url.path
        url_params = {k: v[0] for k, v in parse_qs(parsed_url.query).items()}
        if parsed_params is None:
            parsed_params = {}
        parsed_params = {**url_params, **parsed_params}

    # Auto-inject params for better responses
    if parsed_params is None:
        parsed_params = {}
    # Ensure reference data endpoints return ALL records (prevents pagination waste)
    _REF_DATA_PATHS = ("/costCategory", "/rateCategory", "/paymentType", "/salary/type", "/voucherType", "/vatType")
    if any(p in path for p in _REF_DATA_PATHS) and "count" not in parsed_params:
        parsed_params["count"] = "1000"
    if "/ledger/posting" in path and "fields" not in parsed_params:
        parsed_params["fields"] = "id,date,description,account(id,number,name),amountGross,amountGrossCurrency,vatType(id),row,supplier(id,name),customer(id,name)"
    if "/balanceSheet" in path and "fields" not in parsed_params:
        parsed_params["fields"] = "account(id,number,name),balanceIn,balanceChange,balanceOut"

    result = await client.call("GET", path, params=parsed_params if parsed_params else None)
    response = _truncate_response(result, path=path)
    ctx.context.get_cache[cache_key] = response

    return response


@function_tool
async def tripletex_post(ctx: RunContextWrapper[TaskContext], path: str, body: str = "{}") -> str:
    """POST to Tripletex API. Creates new resources. See system prompt for workflows and field patterns.
Args: path: API endpoint path. body: Request body as JSON string."""
    client = ctx.context.client
    log = ctx.context.logger

    try:
        payload = json.loads(body) if isinstance(body, str) else body
    except json.JSONDecodeError as e:
        return f"Invalid JSON body: {e}"

    if isinstance(payload, (dict, list)):
        payload = apply_fixes(path, "POST", payload)

    # Serialize writes — Gemini ignores parallel_tool_calls=False
    async with ctx.context.write_lock:
        result = await client.call("POST", path, json_data=payload)
        _invalidate_cache(ctx.context.get_cache, path)

        if result["status"] >= 400:
            error_msg = json.dumps(result.get("data", {}), ensure_ascii=False).lower()
            log.log(f"  POST {path} -> {result['status']} ERR")

            if result["status"] == 422 and ("allerede" in error_msg or "i bruk" in error_msg or "already" in error_msg):
                return f"Entity already exists. Use GET {path} to find it instead. Error: {_truncate_response(result, path=path)}"

            if "department" in error_msg and "fylles ut" in error_msg and path.rstrip("/") == "/employee":
                # Auto-fix: fetch a department and inject it
                dept_result = await client.call("GET", "/department", params={"count": "1"})
                dept_values = dept_result.get("data", {}).get("values", [])
                dept_id = None
                if dept_values:
                    dept_id = dept_values[0].get("id")
                else:
                    create_dept = await client.call("POST", "/department", json_data={"name": "Generell", "departmentNumber": "1"})
                    if create_dept["status"] < 400:
                        dept_id = create_dept.get("data", {}).get("value", {}).get("id")
                if dept_id and isinstance(payload, dict):
                    payload["department"] = {"id": dept_id}
                    log.log(f"  AUTO: injected department {dept_id}, retrying")
                    result = await client.call("POST", path, json_data=payload)
                    if result["status"] < 400:
                        return _truncate_response(result)

            if "ugyldig mva-kode" in error_msg or "låst til mva-kode" in error_msg or ("vattype" in error_msg and "låst" in error_msg):
                # Auto-fix: strip vatType from payload AND postings, then retry
                if isinstance(payload, dict):
                    payload.pop("vatType", None)  # product-level vatType
                    for p in payload.get("postings", []):
                        if isinstance(p, dict):
                            p.pop("vatType", None)
                    voucher = payload.get("voucher")
                    if isinstance(voucher, dict):
                        for p in voucher.get("postings", []):
                            if isinstance(p, dict):
                                p.pop("vatType", None)
                    log.log(f"  AUTO: stripped vatType, retrying")
                    result = await client.call("POST", path, json_data=payload)
                    if result["status"] < 400:
                        return _truncate_response(result)
                return f"VAT type error. OMIT vatType and retry. Error: {_truncate_response(result, path=path)}"

            if "arbeidsforhold" in error_msg and "/salary" in path:
                emp_id = _extract_employee_id(payload) if isinstance(payload, dict) else None
                if emp_id:
                    year = payload.get("year", 2026)
                    month = payload.get("month", 1)
                    salary_start = f"{year}-{month:02d}-01"
                    log.log(f"  AUTO: creating employment for employee {emp_id} from {salary_start}")
                    await create_employment(client, emp_id, start_date=salary_start)
                    result = await client.call("POST", path, json_data=payload)
                    if result["status"] < 400:
                        log.log(f"  AUTO: salary retry succeeded")
                        return f"SUCCESS: Salary transaction created. {_truncate_response(result)}"
                    else:
                        log.log(f"  AUTO: salary retry FAILED ({result['status']})")
                        return f"Salary POST failed even after auto-creating employment (startDate={salary_start}). The employment may need a different startDate. RETRY the POST /salary/transaction call. Error: {_truncate_response(result, path=path)}"

            if "leverandør mangler" in error_msg:
                # Auto-fix: find supplier ID in the payload and inject into postings
                if isinstance(payload, dict):
                    # Try to find supplier from supplierInvoice parent or from postings that have it
                    supplier_ref = payload.get("supplier")
                    if not supplier_ref:
                        voucher = payload.get("voucher", {})
                        for p in voucher.get("postings", []) if isinstance(voucher, dict) else []:
                            if isinstance(p, dict) and p.get("supplier"):
                                supplier_ref = p["supplier"]
                                break
                    if supplier_ref:
                        for p in payload.get("postings", []):
                            if isinstance(p, dict) and "supplier" not in p and p.get("amountGross", 0) < 0:
                                p["supplier"] = supplier_ref
                        voucher = payload.get("voucher")
                        if isinstance(voucher, dict):
                            for p in voucher.get("postings", []):
                                if isinstance(p, dict) and "supplier" not in p and p.get("amountGross", 0) < 0:
                                    p["supplier"] = supplier_ref
                        log.log(f"  AUTO: injected supplier into postings, retrying")
                        result = await client.call("POST", path, json_data=payload)
                        if result["status"] < 400:
                            return _truncate_response(result)

            # Auto-fix "Feltet eksisterer ikke" — strip the unknown field and retry
            if "feltet eksisterer ikke" in error_msg and isinstance(payload, (dict, list)):
                bad_field = None
                for vm in result.get("data", {}).get("validationMessages", []):
                    if "eksisterer ikke" in (vm.get("message", "") or "").lower():
                        bad_field = vm.get("field")
                        break
                if bad_field and isinstance(payload, dict):
                    removed = False
                    if bad_field in payload:
                        payload.pop(bad_field)
                        removed = True
                    # Also check nested voucher
                    voucher = payload.get("voucher")
                    if isinstance(voucher, dict) and bad_field in voucher:
                        voucher.pop(bad_field)
                        removed = True
                    # Check postings
                    for p in payload.get("postings", []):
                        if isinstance(p, dict) and bad_field in p:
                            p.pop(bad_field)
                            removed = True
                    for p in (payload.get("voucher", {}) or {}).get("postings", []):
                        if isinstance(p, dict) and bad_field in p:
                            p.pop(bad_field)
                            removed = True
                    # Check orderLines
                    for ol in payload.get("orderLines", []):
                        if isinstance(ol, dict) and bad_field in ol:
                            ol.pop(bad_field)
                            removed = True
                    if removed:
                        log.log(f"  AUTO: stripped field '{bad_field}', retrying")
                        result = await client.call("POST", path, json_data=payload)
                        if result["status"] < 400:
                            return _truncate_response(result)

            if "bankkontonummer" in error_msg or "bank account" in error_msg.lower():
                await ensure_bank_account(client)
                return f"Bank account registered. Please retry. Error: {_truncate_response(result)}"

    return _truncate_response(result)


@function_tool
async def tripletex_put(ctx: RunContextWrapper[TaskContext], path: str, body: str = "{}", params: str = "{}") -> str:
    """PUT to Tripletex API. For updates and action endpoints. Action endpoints use query params (not body). Use body="{}" for action endpoints.
Args: path: API endpoint path. body: JSON string. params: Query parameters as JSON string."""
    client = ctx.context.client

    parsed_params = None
    if params and params != "{}":
        try:
            parsed_params = json.loads(params) if isinstance(params, str) else params
        except (json.JSONDecodeError, TypeError):
            pass

    # Extract query params from URL — httpx drops them when a params dict is passed
    if "?" in path:
        from urllib.parse import urlparse, parse_qs
        parsed_url = urlparse(path)
        path = parsed_url.path
        url_params = {k: v[0] for k, v in parse_qs(parsed_url.query).items()}
        if parsed_params is None:
            parsed_params = {}
        parsed_params = {**url_params, **parsed_params}

    payload = None
    if body and body != "{}":
        try:
            payload = json.loads(body) if isinstance(body, str) else body
        except json.JSONDecodeError:
            pass

    if payload and isinstance(payload, dict):
        payload = apply_fixes(path, "PUT", payload)

    if "/:invoice" in path or "/:payment" in path:
        await ensure_bank_account(client)

    # Serialize writes — Gemini ignores parallel_tool_calls=False
    async with ctx.context.write_lock:
        result = await client.call("PUT", path, json_data=payload, params=parsed_params)
        _invalidate_cache(ctx.context.get_cache, path)

        if result["status"] >= 400:
            error_msg = json.dumps(result.get("data", {}), ensure_ascii=False).lower()

            # Auto-fix vatType errors on PUT
            if "ugyldig mva-kode" in error_msg or "låst til mva-kode" in error_msg:
                if payload and isinstance(payload, dict):
                    payload.pop("vatType", None)
                    for p in payload.get("postings", []):
                        if isinstance(p, dict):
                            p.pop("vatType", None)
                    result = await client.call("PUT", path, json_data=payload, params=parsed_params)
                    error_msg = json.dumps(result.get("data", {}), ensure_ascii=False).lower()

            # Auto-fix "Feltet eksisterer ikke" on PUT
            if result["status"] == 422 and "feltet eksisterer ikke" in error_msg and payload and isinstance(payload, dict):
                for vm in result.get("data", {}).get("validationMessages", []):
                    bf = vm.get("field")
                    if bf and "eksisterer ikke" in (vm.get("message", "") or "").lower() and bf in payload:
                        payload.pop(bf)
                result = await client.call("PUT", path, json_data=payload, params=parsed_params)
                error_msg = json.dumps(result.get("data", {}), ensure_ascii=False).lower()

            if "bankkontonummer" in error_msg or "bank account" in error_msg:
                await ensure_bank_account(client)
                result = await client.call("PUT", path, json_data=payload, params=parsed_params)

    response = _truncate_response(result)
    return response


@function_tool
async def tripletex_delete(ctx: RunContextWrapper[TaskContext], path: str) -> str:
    """DELETE from Tripletex API. Args: path: API path with ID, e.g. /travelExpense/123."""
    client = ctx.context.client
    async with ctx.context.write_lock:
        result = await client.call("DELETE", path)
        ctx.context.get_cache.clear()
    return _truncate_response(result)


@function_tool
async def lookup_occupation_code(ctx: RunContextWrapper[TaskContext], query: str) -> str:
    """FALLBACK: Look up Norwegian STYRK-08 occupation codes from local file. Only use this if GET /employee/employment/occupationCode?nameNO=KEYWORD returns 403. Prefer the Tripletex API endpoint first — it returns the correct internal IDs.
Args: query: A STYRK code number (e.g. "2511") or Norwegian job title keyword (e.g. "utvikler", "logistikk")."""
    results = styrk_lookup(query)
    if not results:
        return f"No STYRK codes found for '{query}'. Try a shorter/broader keyword."
    return json.dumps(results, ensure_ascii=False)


# === Dynamic Instructions ===

_system_prompt_cache = None

def _build_full_prompt() -> str:
    """Build system prompt + all skills upfront (not lazy)."""
    base = build_system_prompt()
    for skill_name in ("get", "post", "put", "delete"):
        skill = _load_skill(skill_name)
        if skill:
            base += f"\n\n## {skill_name.upper()} Patterns\n{skill}"
    return base


def dynamic_instructions(ctx: RunContextWrapper[TaskContext], agent: Agent) -> str:
    global _system_prompt_cache
    if _system_prompt_cache is None:
        _system_prompt_cache = _build_full_prompt()
    base = _system_prompt_cache
    c = ctx.context
    calls = c.client.call_count
    errors = c.client.error_count
    elapsed = time.time() - c.start_time if c.start_time else 0
    turns = c.turn_count

    additions = []
    if elapsed > 200:
        additions.append(f"\n\nCRITICAL: {elapsed:.0f}s elapsed of 280s budget. STOP researching. Execute your writes NOW or you will time out and score 0.")
    elif elapsed > 120:
        additions.append(f"\n\nURGENT: {elapsed:.0f}s elapsed of 280s budget. You MUST start writing (POST/PUT) immediately. Do NOT fetch more data.")
    elif elapsed > 60:
        additions.append(f"\n\nNOTE: {elapsed:.0f}s elapsed. Act on the data you already have — do not over-research.")

    if errors > 2:
        additions.append(f"\n\nWARNING: {errors} errors. Change strategy NOW. Do not retry the same failing approach.")

    if calls > 18:
        additions.append(f"\n\nWARNING: {calls} API calls. Wrap up — efficiency score drops with more calls.")

    if turns > 12:
        additions.append(f"\n\nCRITICAL: {turns} turns used. STOP exploring. Finish NOW with what you have.")
    elif turns > 6:
        additions.append(f"\n\nNOTE: {turns} turns used. Finish what you have. If a lookup failed, skip it and proceed.")

    if additions:
        return base + "".join(additions)
    return base


# === Agent creation ===

def create_agent() -> Agent[TaskContext]:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    model_name = os.environ.get("LLM_MODEL", "gemini-3.1-pro-preview")

    gemini_client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        timeout=120.0,  # 120s max per LLM call
    )

    model = OpenAIChatCompletionsModel(
        model=model_name,
        openai_client=gemini_client,
    )

    return Agent[TaskContext](
        name="TripletexAccountant",
        instructions=dynamic_instructions,
        model=model,
        tools=[tripletex_get, tripletex_post, tripletex_put, tripletex_delete, lookup_occupation_code],
        model_settings=ModelSettings(
            temperature=0.0,
            parallel_tool_calls=False,
        ),
    )


# === Run agent ===

async def run_agent(prompt: str, file_contents: list, tripletex_client: TripletexClient, req_id: str = "????", hooks=None) -> dict:
    """Run the agent using OpenAI Agents SDK."""
    global _system_prompt_cache
    _system_prompt_cache = None  # Reset per request so today's date is fresh

    agent = create_agent()
    start_time = time.time()
    logger = RunLogger(req_id)
    logger.start_time = start_time
    task_ctx = TaskContext(client=tripletex_client, req_id=req_id, start_time=start_time, logger=logger)

    logger.log(f"PROMPT: {prompt[:600]}")
    if file_contents:
        logger.log(f"FILES: {len(file_contents)} attachment(s)")

    # Set up bank account proactively only for tasks that need invoices/payments
    # Skip for simple tasks (create product/customer/supplier/employee/department) to save 1 write call
    prompt_lower = prompt.lower()
    # Bank account is ONLY needed for tasks that create CUSTOMER INVOICES
    # (PUT /order/:invoice or PUT /invoice/:payment). NOT needed for vouchers,
    # salary, travel, supplier invoices, monthly closing, receipts.
    # Reactive handler in tripletex_put catches edge cases.
    needs_bank = any(w in prompt_lower for w in [
        "faktura", "invoice", "factura", "rechnung", "fatura", "facture",
        "ordre", "order", "auftrag", "commande", "pedido", "bestilling",
        "betaling", "payment", "paiement", "pago", "zahlung",
        "purregebyr", "rappel", "mahngebühr", "lembrete", "overdue", "forfalt", "überfällig", "vencid",
        "credit note", "kreditnota", "gutschrift",
        "agio", "disagio", "valuta", "currency", "kurs", "wechselkurs", "câmbio",
        "avstem", "reconcil", "kontoauszug", "extrato", "rapproch",
        "syklus", "lifecycle", "ciclo de vida", "cycle de vie", "lebenszyklus",
        "fastpris", "fixed price", "prix forfaitaire", "precio fijo", "preço fixo",
    ])
    if needs_bank:
        try:
            await ensure_bank_account(tripletex_client)
            logger.log("SETUP: bank account OK")
        except ProxyTokenExpiredError:
            logger.log("SETUP: PROXY TOKEN EXPIRED — aborting")
            logger.flush(f"ABORTED proxy token expired | 0 turns | {tripletex_client.call_count} calls")
            return {
                "status": "error",
                "api_calls": tripletex_client.call_count,
                "errors": tripletex_client.error_count,
            }

    # Build input — wrap file content parts in a proper message for the SDK
    if file_contents:
        input_content = [{"role": "user", "content": [{"type": "input_text", "text": prompt}] + file_contents}]
    else:
        input_content = prompt

    try:
        run_result = await asyncio.wait_for(
            Runner.run(
                starting_agent=agent,
                input=input_content,
                context=task_ctx,
                max_turns=25,
                hooks=hooks or LoggingHooks(),
            ),
            timeout=280.0,  # Hard timeout: ~5 min (competition allows 300s)
        )
        elapsed = time.time() - start_time
        logger.log(f"DONE in {elapsed:.1f}s: {str(run_result.final_output)[:300]}")
        logger.flush(f"OK {elapsed:.1f}s | {task_ctx.turn_count} turns | {tripletex_client.call_count} calls | {tripletex_client.error_count} errors")

    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        logger.log(f"TIMEOUT after {elapsed:.1f}s")
        logger.flush(f"TIMEOUT {elapsed:.1f}s | {task_ctx.turn_count} turns | {tripletex_client.call_count} calls")

    except ProxyTokenExpiredError:
        elapsed = time.time() - start_time
        logger.log(f"PROXY TOKEN EXPIRED after {elapsed:.1f}s")
        logger.flush(f"PROXY_EXPIRED {elapsed:.1f}s | {task_ctx.turn_count} turns | {tripletex_client.call_count} calls")

    except Exception as e:
        elapsed = time.time() - start_time
        logger.log(f"ERROR after {elapsed:.1f}s: {e}")
        logger.flush(f"ERROR {elapsed:.1f}s | {task_ctx.turn_count} turns | {tripletex_client.call_count} calls | {e}")

    return {
        "status": "completed",
        "api_calls": tripletex_client.call_count,
        "errors": tripletex_client.error_count,
    }
