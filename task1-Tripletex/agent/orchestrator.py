"""Orchestrator — Plan-then-Execute agent for Tripletex.

Architecture:
  1. [LLM] Generate execution plan (1-2 calls via Agents SDK / litellm)
  2. [Code] Execute steps: resolve → sanitize → validate → call → fix → store
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from datetime import date
from pathlib import Path

import litellm
from agents import Agent, Runner
from agents.extensions.models.litellm_model import LitellmModel

from agent.config import MODEL_ID
from agent.logging_config import setup_logging, write_trace
from agent.client import TripletexClient
from agent.context import load_registry, get_endpoint, schema_for_prompt
from agent.validator import validate_payload
from agent.file_handler import decode_files, files_for_llm

setup_logging()
logger = logging.getLogger("tripletex-agent")

model = LitellmModel(model=MODEL_ID)
TODAY = date.today().isoformat()
TIME_BUDGET = 280.0  # seconds — stop before 5-min competition timeout
MAX_RETRIES = 3
UNRECOVERABLE = ["bankkontonummer", "proxy token", "bank account"]

# ── Static resources ──────────────────────────────────────────────────────────

SPECS_DIR = Path(__file__).parent.parent / "specs"
KNOWLEDGE_BASE = (Path(__file__).parent / "knowledgebase.md").read_text()
INDEX_MD = (SPECS_DIR / "index_slim.md").read_text()


# ── System prompts ────────────────────────────────────────────────────────────

PLAN_SYSTEM = f"""You are an expert accounting agent for Tripletex.
You receive a task prompt (possibly in Norwegian, English, Spanish, Portuguese, Nynorsk, German, or French) and must plan which Tripletex API calls to make.

Today's date: {TODAY}

<knowledge_base>
{KNOWLEDGE_BASE}
</knowledge_base>

<endpoint_index>
{INDEX_MD}
</endpoint_index>

RULES:
- Output a JSON object with a "steps" array.
- Each step: {{"method": "...", "path": "...", "alias": "...", "payload": {{...}} or null, "params": {{...}} or null}}
- For GET requests, use "params" for query parameters.
- Action endpoints (/:invoice, /:payment, /:createCreditNote) take query "params", NOT "payload".
- Use $alias_field placeholders for IDs from prior steps (e.g. "$customer_id", "$department_0_id").
- Path should NOT include /v2 prefix.
- For PUT/DELETE with IDs, use placeholders: "/customer/$customer_id".
- CRITICAL — GET vs POST decision:
  * If the task says "Register hours for X" / "Run payroll for X" / "X has an invoice" / "payment from X" → X ALREADY EXISTS. Use ONLY GET to find them. Do NOT plan a POST step.
  * Only POST to create entities the task explicitly asks to CREATE (e.g. "Create employee", "Opprett kunde").
  * When in doubt, use GET only. The sandbox has the entities pre-created.
- FOLLOW knowledge base workflows when they match.
- Minimize API calls — fewer = higher score. Every unnecessary POST wastes time and may fail.

Respond with valid JSON only. No markdown, no explanation."""


FIX_SYSTEM = """You are fixing a failed Tripletex API call.
Fix the payload based on the error message.

Original task: {prompt}
Today's date: {today}

Agent state (available $placeholders): {state}

{schema_section}

Return JSON: {{"payload": {{...}}}} with corrected body.
For action endpoints (/:invoice, /:payment, /:createCreditNote), return {{"params": {{...}}}} instead.
If unfixable, return {{"skip": true}}.

Respond with valid JSON only."""


# ── Planning agent (Agents SDK) ──────────────────────────────────────────────

planning_agent = Agent(
    name="Planner",
    model=model,
    instructions=PLAN_SYSTEM,
)


# ── LLM helpers ───────────────────────────────────────────────────────────────

async def _ask_json(system: str, user_msg: str) -> dict:
    """Direct litellm call for JSON responses."""
    try:
        resp = await asyncio.wait_for(
            litellm.acompletion(
                model=MODEL_ID,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_msg},
                ],
                temperature=1.0,
                response_format={"type": "json_object"},
            ),
            timeout=60.0,
        )
        return json.loads(resp.choices[0].message.content or "{}")
    except Exception as e:
        logger.error(f"LLM error: {e}")
        return {"error": str(e)}


async def _ask_json_multimodal(system: str, content: list[dict]) -> dict:
    """Direct litellm call with multimodal content (text + images)."""
    try:
        resp = await asyncio.wait_for(
            litellm.acompletion(
                model=MODEL_ID,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": content},
                ],
                temperature=1.0,
                response_format={"type": "json_object"},
            ),
            timeout=90.0,
        )
        return json.loads(resp.choices[0].message.content or "{}")
    except Exception as e:
        logger.error(f"LLM multimodal error: {e}")
        return {"error": str(e)}


def _parse_json(text: str) -> dict:
    """Parse JSON from agent output, handling markdown code blocks."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        logger.error(f"JSON parse failed: {text[:500]}")
        return {"steps": []}


# ── Planning ──────────────────────────────────────────────────────────────────

async def _plan(prompt: str, file_parts: list[dict], registry: dict) -> dict:
    """Generate execution plan. Uses Agents SDK for text, litellm for multimodal."""
    t0 = time.monotonic()

    # Phase 1: Initial plan
    if file_parts:
        # Multimodal (files attached) → use litellm directly
        content = [{"type": "text", "text": f"Task: {prompt}"}] + file_parts
        plan_data = await _ask_json_multimodal(PLAN_SYSTEM, content)
    else:
        # Text-only → use Agents SDK
        try:
            result = await Runner.run(planning_agent, input=f"Task: {prompt}", max_turns=1)
            plan_data = _parse_json(result.final_output)
        except Exception as e:
            logger.warning(f"Agents SDK failed, falling back to litellm: {e}")
            plan_data = await _ask_json(PLAN_SYSTEM, f"Task: {prompt}")

    if "error" in plan_data:
        logger.warning(f"Plan attempt 1 failed: {plan_data}")
        plan_data = await _ask_json(PLAN_SYSTEM, f"Task: {prompt}")
        if "error" in plan_data:
            logger.error(f"Plan failed after retry: {plan_data}")
            return {"steps": []}

    steps = plan_data.get("steps", [])

    # Phase 2: Schema enrichment disabled — causes alias mismatches and wastes 20-30s
    # The knowledgebase has detailed workflows, so the initial plan is usually correct
    if False and len(steps) > 5:
        schemas = _collect_schemas(steps, registry)
        if schemas:
            schema_text = "\n\n".join(schemas)
            enriched = f"Task: {prompt}\n\nDETAILED SCHEMAS for endpoints you'll use:\n{schema_text}"

            if file_parts:
                content = [{"type": "text", "text": enriched}] + file_parts
                refined = await _ask_json_multimodal(PLAN_SYSTEM, content)
            else:
                refined = await _ask_json(PLAN_SYSTEM, enriched)

            if "error" not in refined and "steps" in refined:
                steps = refined["steps"]

    duration = (time.monotonic() - t0) * 1000
    logger.info(f"PLAN | {len(steps)} steps | {duration:.0f}ms")
    write_trace(1, "PLAN", prompt[:500],
                json.dumps(steps, ensure_ascii=False)[:1000], duration)

    return {"steps": steps}


def _collect_schemas(steps: list[dict], registry: dict) -> list[str]:
    """Get schemas for endpoints referenced in a plan."""
    schemas: list[str] = []
    seen: set[str] = set()
    for step in steps:
        if "method" not in step or "path" not in step:
            continue
        lookup = re.sub(r'/\$[a-zA-Z0-9_]+', '/{id}', step['path'])
        key = f"{step['method']} {lookup}"
        if key not in seen:
            ep = get_endpoint(registry, step["method"], lookup)
            if ep:
                schemas.append(schema_for_prompt(ep))
            seen.add(key)
    return schemas


# ── Sanitization ──────────────────────────────────────────────────────────────

_VOUCHER_POSTING_FIELDS = {
    "account", "amount", "amountCurrency", "amountGross", "amountGrossCurrency",
    "description", "date", "customer", "supplier", "employee", "project", "product",
    "department", "vatType", "currency", "invoiceNumber", "termOfPayment",
    "freeAccountingDimension1", "freeAccountingDimension2", "freeAccountingDimension3",
    "closeGroup", "amortizationAccount", "amortizationStartDate", "amortizationEndDate",
}


def _sanitize_step(path: str, method: str, payload: dict | None,
                   params: dict | None) -> tuple[dict | None, dict | None]:
    """Apply endpoint-specific payload fixes. Returns (payload, params)."""

    # ── /:payment — move body fields to query params ──
    if "/:payment" in path:
        if payload and isinstance(payload, dict):
            if not params:
                params = {}
            for key in ("paymentDate", "paymentTypeId", "paidAmount", "paidAmountCurrency"):
                if key in payload:
                    params[key] = payload.pop(key)
            if not payload:
                payload = None

    # ── /:createCreditNote — move body to params ──
    elif "/:createCreditNote" in path:
        if payload and isinstance(payload, dict):
            if not params:
                params = {}
            for key in ("date", "comment", "sendToCustomer"):
                if key in payload:
                    params[key] = payload.pop(key)
            if not payload:
                payload = None
        if not params:
            params = {"date": TODAY}
        elif "date" not in params:
            params["date"] = TODAY

    # ── /:invoice — query-param-only endpoint, NO body ──
    elif "/:invoice" in path:
        if payload and isinstance(payload, dict):
            if not params:
                params = {}
            for key in ("invoiceDate", "sendToCustomer", "sendType", "paymentTypeId",
                        "paidAmount", "paidAmountAccountCurrency", "createOnAccount",
                        "createBackorder", "overrideEmailAddress"):
                if key in payload:
                    params[key] = payload.pop(key)
        if not params:
            params = {"invoiceDate": TODAY}
        elif "invoiceDate" not in params:
            params["invoiceDate"] = TODAY
        payload = None  # Never takes a body

    # ── Voucher: whitelist posting fields, assign row numbers, ensure date ──
    elif "/voucher" in path and method == "POST" and payload and isinstance(payload, dict):
        postings = payload.get("postings")
        if postings and isinstance(postings, list):
            clean = []
            for p in postings:
                if isinstance(p, dict):
                    filtered = {k: v for k, v in p.items() if k in _VOUCHER_POSTING_FIELDS}
                    if filtered.get("account") and filtered.get("amount") is not None:
                        clean.append(filtered)
            # CRITICAL: Assign row numbers starting at 1 (row 0 is reserved for system-generated)
            for idx, posting in enumerate(clean):
                posting["row"] = idx + 1
            payload["postings"] = clean
        if "date" not in payload:
            payload["date"] = TODAY

    # ── accountingDimensionName: remap fields ──
    elif "/accountingDimensionName" in path and method == "POST" and payload and isinstance(payload, dict):
        if "name" in payload and "dimensionName" not in payload:
            payload["dimensionName"] = payload.pop("name")
        if "active" not in payload:
            payload["active"] = True
        if "description" not in payload:
            payload["description"] = payload.get("dimensionName", "")

    # ── accountingDimensionValue: remap fields ──
    elif "/accountingDimensionValue" in path and method == "POST" and payload and isinstance(payload, dict):
        if "name" in payload and "displayName" not in payload:
            payload["displayName"] = payload.pop("name")
        payload.pop("accountingDimensionName", None)
        if "active" not in payload:
            payload["active"] = True

    # ── Order: ensure deliveryDate ──
    elif path.rstrip("/") == "/order" and method == "POST" and payload and isinstance(payload, dict):
        if "deliveryDate" not in payload:
            payload["deliveryDate"] = payload.get("orderDate", TODAY)
        if "orderDate" not in payload:
            payload["orderDate"] = TODAY

    # ── Salary transaction: ensure date/year/month at all levels ──
    elif "/salary/transaction" in path and method == "POST" and payload and isinstance(payload, dict):
        if "date" not in payload:
            payload["date"] = TODAY
        if "year" not in payload:
            payload["year"] = int(TODAY[:4])
        if "month" not in payload:
            payload["month"] = int(TODAY[5:7])
        payslips = payload.get("payslips")
        if payslips and isinstance(payslips, list):
            for ps in payslips:
                if isinstance(ps, dict):
                    for k in ("date", "year", "month"):
                        if k not in ps:
                            ps[k] = payload[k]
                    # Fix specs: rate is REQUIRED, amount is not
                    specs = ps.get("specifications")
                    if specs and isinstance(specs, list):
                        for spec in specs:
                            if isinstance(spec, dict):
                                if "rate" not in spec and "amount" in spec:
                                    spec["rate"] = spec.pop("amount")
                                if "count" not in spec:
                                    spec["count"] = 1

    # ── Travel expense cost: ensure date ──
    elif "/travelExpense/cost" in path and method == "POST" and payload and isinstance(payload, dict):
        if "date" not in payload:
            payload["date"] = TODAY

    # ── Employee: ensure employment fields ──
    elif path.rstrip("/") == "/employee" and method == "POST" and payload and isinstance(payload, dict):
        employments = payload.get("employments")
        if employments and isinstance(employments, list):
            for emp in employments:
                if isinstance(emp, dict):
                    if "isMainEmployer" not in emp:
                        emp["isMainEmployer"] = True
                    if "startDate" not in emp:
                        emp["startDate"] = TODAY

    # ── Activity: ensure type ──
    elif "/activity" in path and method == "POST" and payload and isinstance(payload, dict):
        if "activityType" not in payload:
            payload["activityType"] = "PROJECT_SPECIFIC"

    # ── GET /invoice: ensure date range ──
    elif "/invoice" in path and method == "GET" and "/:send" not in path and "/paymentType" not in path:
        if not params:
            params = {}
        if "invoiceDateFrom" not in params:
            params["invoiceDateFrom"] = "2020-01-01"
        if "invoiceDateTo" not in params:
            params["invoiceDateTo"] = "2030-01-01"

    # ── GET /ledger/account: warn if no range ──
    elif "/ledger/account" in path and method == "GET" and "/account/" not in path:
        if params and not any(k in params for k in ("numberFrom", "numberTo", "id", "number")):
            logger.warning("GET /ledger/account without number range — may be slow")

    # ── Global: clean numeric strings in params ──
    if params and isinstance(params, dict):
        for key, val in params.items():
            if isinstance(val, str) and any(c.isdigit() for c in val):
                cleaned = re.sub(r'[^0-9.\-]', '', val)
                if cleaned and cleaned != val:
                    try:
                        params[key] = float(cleaned) if '.' in cleaned else int(cleaned)
                        logger.info(f"Cleaned param {key}: '{val}' → {params[key]}")
                    except (ValueError, TypeError):
                        pass

    return payload, params


# ── Execution helpers ─────────────────────────────────────────────────────────

_PLACEHOLDER_RE = re.compile(r'\$[a-zA-Z][a-zA-Z0-9]*_[a-zA-Z0-9_]+')


def _has_unresolved(value) -> bool:
    """Check for unresolved $placeholders (not literal dollar amounts)."""
    if isinstance(value, str):
        return bool(_PLACEHOLDER_RE.search(value))
    if isinstance(value, dict):
        return any(_has_unresolved(v) for v in value.values())
    if isinstance(value, list):
        return any(_has_unresolved(v) for v in value)
    return False


def _is_unrecoverable(error_data) -> bool:
    error_str = str(error_data).lower()
    return any(phrase in error_str for phrase in UNRECOVERABLE)


def _store_response(client: TripletexClient, alias: str, data):
    """Store API response data in client state for placeholder resolution."""
    if not isinstance(data, dict):
        return
    if "value" in data and isinstance(data["value"], dict):
        client.store(alias, data["value"])
    elif "values" in data and isinstance(data["values"], list):
        for item in data["values"]:
            if isinstance(item, dict):
                client.store(alias, item)


async def _fix_payload(step: dict, errors: list[str], state: dict,
                       payload: dict | None, registry: dict,
                       prompt: str, params: dict | None) -> dict | None:
    """Ask LLM to fix a failed payload based on error messages."""
    state_summary = ", ".join(f"{k}={v}" for k, v in state.items()
                              if isinstance(v, (int, str)))

    schema_section = ""
    if registry:
        lookup = re.sub(r'/\d+', '/{id}', step.get("path", ""))
        ep = get_endpoint(registry, step.get("method", ""), lookup)
        if ep:
            schema_section = f"Endpoint schema:\n{schema_for_prompt(ep)}"

    system = (FIX_SYSTEM
              .replace("{state}", state_summary or "(empty)")
              .replace("{schema_section}", schema_section)
              .replace("{today}", TODAY)
              .replace("{prompt}", prompt[:500] if prompt else ""))

    user_msg = (f"Step: {step['method']} {step['path']}\n"
                f"Payload: {payload}\nParams: {params}\nErrors: {errors}")

    result = await _ask_json(system, user_msg)
    if result.get("skip") or "error" in result:
        return None
    return result.get("payload", result)


async def _get_existing(client: TripletexClient, path: str,
                        payload: dict | None) -> dict | None:
    """When POST returns 'already exists', GET the entity to store its ID."""
    get_params: dict = {"count": 10}
    if payload and isinstance(payload, dict):
        # Try common identifier fields for the GET search
        for field in ("email", "organizationNumber", "number", "name"):
            val = payload.get(field)
            if val and isinstance(val, (str, int)):
                get_params[field] = val
                break
    if len(get_params) <= 1:
        return None  # No searchable field found

    result = await client.call("GET", path, params=get_params)
    if result["status"] < 400:
        return result["data"]
    return None


# ── Execute ───────────────────────────────────────────────────────────────────

async def _execute(client: TripletexClient, steps: list[dict],
                   registry: dict, prompt: str):
    """Execute plan steps in order with validation, retries, and time budget."""
    failed: set[str] = set()
    abort = False

    for i, step in enumerate(steps):
        if client.time_left(TIME_BUDGET) < 10:
            logger.warning(f"Time budget exhausted at step {i}")
            break

        if abort:
            logger.warning(f"Step {i}: skipping (session expired)")
            continue

        if "method" not in step or "path" not in step:
            logger.warning(f"Step {i}: malformed, skip")
            continue

        method = step["method"].upper()
        path = step["path"]
        alias = step.get("alias", f"step_{i}")
        payload = step.get("payload")
        params = step.get("params")

        # Resolve placeholders
        path = client.resolve(path)
        if payload is not None:
            payload = client.resolve(payload)
        if params is not None:
            params = client.resolve(params)

        # Check for unresolved placeholders
        if _has_unresolved(path):
            logger.warning(f"Step {i}: unresolved placeholder in path '{path}', skip")
            failed.add(alias)
            continue
        if payload is not None and _has_unresolved(payload):
            logger.warning(f"Step {i}: unresolved placeholder in payload, skip")
            failed.add(alias)
            continue
        if params is not None and _has_unresolved(params):
            logger.warning(f"Step {i}: unresolved placeholder in params, skip")
            failed.add(alias)
            continue

        # Sanitize
        payload, params = _sanitize_step(path, method, payload, params)

        # Validate payload before sending
        if payload is not None and method in ("POST", "PUT"):
            lookup = re.sub(r'/\d+', '/{id}', path)
            vresult = validate_payload(registry, method, lookup, payload)
            if vresult["errors"]:
                logger.warning(f"Step {i} validation: {vresult['errors']}")
                payload = await _fix_payload(step, vresult["errors"], client.state,
                                             payload, registry, prompt, params)
                if payload is None:
                    logger.error(f"Step {i}: skipped after validation failure")
                    failed.add(alias)
                    continue
                payload = client.resolve(payload)
                payload, params = _sanitize_step(path, method, payload, params)
            if vresult["warnings"]:
                logger.info(f"Step {i} warnings: {vresult['warnings']}")

        # Log and execute
        logger.info(f"Step {i}: {method} {path}")
        if payload:
            logger.info(f"  payload: {str(payload)[:300]}")
        if params:
            logger.info(f"  params: {params}")

        api_result = await client.call(method, path, json=payload, params=params)

        if api_result["status"] < 400:
            _store_response(client, alias, api_result["data"])
            logger.info(f"Step {i} OK: {api_result['status']}")
            write_trace(2 + i, f"EXEC_OK", f"{method} {path}",
                        str(api_result["data"])[:500], 0)
            continue

        # Error handling
        logger.warning(f"Step {i} FAIL: {api_result['status']} — {str(api_result['data'])[:300]}")

        # Handle "already exists" / "in use" — GET the existing entity instead
        if api_result["status"] == 422 and method == "POST":
            error_str = str(api_result["data"]).lower()
            if any(phrase in error_str for phrase in
                   ("allerede", "already exists", "i bruk", "er i bruk", "in use")):
                existing = await _get_existing(client, path, payload)
                if existing:
                    _store_response(client, alias, existing)
                    logger.info(f"Step {i}: entity already exists, stored from GET")
                    continue

        # Handle bank account error on POST /invoice → try PUT /order/:invoice fallback
        if api_result["status"] == 422 and method == "POST" and path.rstrip("/") == "/invoice":
            error_str = str(api_result["data"]).lower()
            if "bankkontonummer" in error_str or "bank account" in error_str:
                # Try to find the order ID from the payload and use /:invoice action
                order_id = None
                if payload and isinstance(payload, dict):
                    orders = payload.get("orders", [])
                    if orders and isinstance(orders, list) and isinstance(orders[0], dict):
                        order_id = orders[0].get("id")
                if order_id:
                    fallback_path = f"/order/{order_id}/:invoice"
                    fallback_params = {"invoiceDate": payload.get("invoiceDate", TODAY)}
                    logger.info(f"Step {i}: bank account error, trying PUT {fallback_path}")
                    fallback_result = await client.call("PUT", fallback_path, params=fallback_params)
                    if fallback_result["status"] < 400:
                        _store_response(client, alias, fallback_result["data"])
                        logger.info(f"Step {i} fallback OK: {fallback_result['status']}")
                        continue
                    logger.warning(f"Step {i} fallback also failed: {fallback_result['status']}")

        if _is_unrecoverable(api_result["data"]):
            logger.warning(f"Step {i}: unrecoverable error")
            failed.add(alias)
            if "proxy token" in str(api_result["data"]).lower():
                abort = True
            continue

        # Retry with LLM fix
        last_p, last_q = payload, params
        ok = False
        for retry in range(MAX_RETRIES):
            fixed = await _fix_payload(
                step, [str(api_result["data"])], client.state,
                last_p, registry, prompt, last_q
            )
            if fixed is None:
                break

            # Handle fix response format (may return params or payload)
            if isinstance(fixed, dict) and "params" in fixed and "payload" not in fixed:
                last_q = client.resolve(fixed["params"])
                last_p = None
            elif isinstance(fixed, dict) and "params" in fixed:
                last_q = client.resolve(fixed["params"])
                last_p = client.resolve(fixed.get("payload"))
            else:
                last_p = client.resolve(fixed)

            last_p, last_q = _sanitize_step(path, method, last_p, last_q)

            api_result = await client.call(method, path, json=last_p, params=last_q)
            if api_result["status"] < 400:
                _store_response(client, alias, api_result["data"])
                logger.info(f"Step {i} retry {retry + 1} OK: {api_result['status']}")
                ok = True
                break

            logger.warning(f"Step {i} retry {retry + 1} FAIL: {api_result['status']}")
            if _is_unrecoverable(api_result["data"]):
                break

        if not ok:
            failed.add(alias)


# ── Entry point ───────────────────────────────────────────────────────────────

async def run(prompt: str, base_url: str, session_token: str,
              files: list[dict] | None = None):
    """Main entry point — called by api.py /solve."""
    logger.info(f"TASK_START: {prompt[:100]}")

    client = TripletexClient(base_url, session_token)
    registry = load_registry()

    decoded = decode_files(files) if files else []
    file_parts = files_for_llm(decoded) if decoded else []

    try:
        # Phase 1: Plan
        plan_result = await _plan(prompt, file_parts, registry)
        steps = plan_result.get("steps", [])
        logger.info(f"Plan: {len(steps)} steps")
        for i, s in enumerate(steps):
            logger.info(f"  {i}: {s.get('method')} {s.get('path')} [{s.get('alias')}]")

        if not steps:
            logger.error("No steps generated — aborting")
            return

        # Phase 2: Execute
        await _execute(client, steps, registry, prompt)

        # Summary
        logger.info(
            f"TASK_DONE: {client.call_count} API calls, "
            f"{client.error_count} errors, {client.elapsed()}s elapsed"
        )
    finally:
        await client.close()
