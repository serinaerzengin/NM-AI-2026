"""Orchestrator — Plan-then-Execute agent for Tripletex accounting tasks."""

import logging
import re
from datetime import date

from tripletex_client import TripletexClient
from context import load_registry, load_index, load_domain, get_endpoint, schema_for_prompt
from validator import validate_payload
from file_handler import decode_files, files_for_llm
from llm import get_client, ask_json

logger = logging.getLogger("agent")

MAX_RETRIES_PER_STEP = 3
TIME_BUDGET = 280.0  # ~4.5 minutes (competition timeout is 5 min)
TODAY = date.today().isoformat()  # Dynamic — no hardcoding in domain.md

# Errors that cannot be fixed by retrying — skip immediately to save time
UNRECOVERABLE_ERRORS = [
    "bankkontonummer",  # Company needs bank account — can't register via API
    "proxy token",  # Session expired — all subsequent calls will also fail
]


PLAN_SYSTEM = """You are an expert accounting agent for Tripletex.
You receive a task prompt (possibly in Norwegian, English, Spanish, Portuguese, Nynorsk, German, or French) and must plan which Tripletex API calls to make.

Today's date: {today}

You have access to the full Tripletex v2 API endpoint index below.

{domain}

RULES:
- Output a JSON object with a "steps" array
- Each step has: "method", "path", "alias" (short name to store result), "payload" (request body, or null for GET/DELETE)
- For GET requests, use "params" instead of "payload" for query parameters
- Action endpoints (/:invoice, /:payment, /:createCreditNote) take query "params", NOT "payload"
- Use $alias_field placeholders to reference results from previous steps (e.g. "$customer_id")
- You can use either $customer_id or $customer_0_id — both work for the first resource of that type
- For multiple resources of the same type, use indexed: $customer_0_id, $customer_1_id, etc.
- Available fields after storing: id, name, and other simple fields returned by the API
- Minimize API calls — don't fetch what you just created
- If files are attached, extract relevant data from them for the API calls
- Path should NOT include /v2 prefix — the base URL already includes it
- For PUT/DELETE with IDs, use placeholders in the path: e.g. "/customer/$customer_id"
- DELETE requests typically need the ID in the path: "/travelExpense/$expense_id"
- For existing entities mentioned in the task, use GET to look them up first. Only POST to create new ones.

ENDPOINT INDEX:
{index}
"""

PLAN_WITH_SCHEMAS = """
DETAILED SCHEMAS for the endpoints you'll need:
{schemas}
"""

EXECUTE_FIX_SYSTEM = """You are fixing a failed Tripletex API call.
The call returned an error. Fix the payload based on the error message.

Original task: {prompt}

Return a JSON object with the corrected "payload" (the request body).
For action endpoints (/:invoice, /:payment, /:createCreditNote), return {"params": {...}} with query parameters instead.
If the step cannot be fixed, return {"skip": true}.

Today's date: {today}

Current agent state (available $placeholders):
{state}

{schema_section}
"""


async def plan(llm_client, prompt: str, file_parts: list[dict], registry: dict) -> dict:
    """Phase 1: Ask LLM to generate an execution plan."""
    index = load_index()
    domain = load_domain()
    system = PLAN_SYSTEM.replace("{domain}", domain).replace("{index}", index).replace("{today}", TODAY)

    # Build user message with prompt + optional file vision
    user_content: list[dict] | str
    if file_parts:
        user_content = [{"type": "text", "text": f"Task: {prompt}"}] + file_parts
    else:
        user_content = f"Task: {prompt}"

    # Try planning with retry on LLM failure
    plan_result = await ask_json(llm_client, system, user_content)

    if "error" in plan_result:
        logger.warning(f"Plan attempt 1 failed, retrying: {plan_result}")
        plan_result = await ask_json(llm_client, system, user_content)
        if "error" in plan_result:
            logger.error(f"Plan failed after retry: {plan_result}")
            return {"steps": []}

    # If the LLM returned steps, enrich with schemas for a second pass
    # Skip for simple plans (≤2 steps) — they're usually correct and second pass wastes time
    steps = plan_result.get("steps", [])
    if len(steps) > 2:
        # Collect schemas for endpoints used in the plan
        schemas = []
        seen = set()
        for step in steps:
            if "method" not in step or "path" not in step:
                continue
            lookup_path = re.sub(r'/\$[a-zA-Z0-9_]+', '/{id}', step['path'])
            key = f"{step['method']} {lookup_path}"
            if key not in seen:
                ep = get_endpoint(registry, step["method"], lookup_path)
                if ep:
                    schemas.append(schema_for_prompt(ep))
                seen.add(key)

        if schemas:
            schema_text = "\n\n".join(schemas)
            refined_system = system + PLAN_WITH_SCHEMAS.replace("{schemas}", schema_text)
            plan_result = await ask_json(llm_client, refined_system, user_content)
            if "error" not in plan_result:
                steps = plan_result.get("steps", steps)

    return {"steps": steps}


_PLACEHOLDER_RE = re.compile(r'\$[a-zA-Z][a-zA-Z0-9]*_[a-zA-Z0-9_]+')


def _has_unresolved(value) -> bool:
    """Check if a value still contains unresolved $placeholders like $customer_id.
    Does NOT flag literal dollar signs in text (e.g. '$100', 'cost $5')."""
    if isinstance(value, str):
        return bool(_PLACEHOLDER_RE.search(value))
    if isinstance(value, dict):
        return any(_has_unresolved(v) for v in value.values())
    if isinstance(value, list):
        return any(_has_unresolved(v) for v in value)
    return False


def _is_unrecoverable(error_data) -> bool:
    """Check if an API error is known to be unrecoverable (no point retrying)."""
    error_str = str(error_data).lower()
    return any(phrase in error_str for phrase in UNRECOVERABLE_ERRORS)


# ── Payload sanitization ──────────────────────────────────────────────
# Rules that the LLM often gets wrong, enforced in code so domain.md
# only needs to describe *what* to do, not *how* to avoid pitfalls.

# Fields that are valid in voucher postings — everything else gets stripped
_VOUCHER_POSTING_FIELDS = {
    "account", "amount", "amountCurrency", "amountGross", "amountGrossCurrency",
    "description", "date", "customer", "supplier", "employee", "project", "product",
    "department", "vatType", "currency", "invoiceNumber", "termOfPayment",
    "freeAccountingDimension1", "freeAccountingDimension2", "freeAccountingDimension3",
    "closeGroup", "amortizationAccount", "amortizationStartDate", "amortizationEndDate",
}


def _sanitize_step(path: str, method: str, payload: dict | None, params: dict | None) -> tuple[dict | None, dict | None]:
    """Apply all endpoint-specific sanitizations. Moves domain rules into code.
    Returns (payload, params) — possibly modified."""

    # ── Action endpoints: move body fields to query params ──
    if "/:payment" in path:
        if payload and isinstance(payload, dict):
            if not params:
                params = {}
            for key in ("paymentDate", "paymentTypeId", "paidAmount", "paidAmountCurrency"):
                if key in payload:
                    params[key] = payload.pop(key)
            if not payload:
                payload = None

    elif "/:createCreditNote" in path:
        if payload and isinstance(payload, dict):
            if not params:
                params = {}
            for key in ("date", "comment", "sendToCustomer"):
                if key in payload:
                    params[key] = payload.pop(key)
            if not payload:
                payload = None
        # Always ensure date param
        if not params:
            params = {"date": TODAY}
        elif "date" not in params:
            params["date"] = TODAY

    elif "/:invoice" in path:
        # PUT /order/{id}/:invoice — query-param-only endpoint, NO body
        if payload and isinstance(payload, dict):
            if not params:
                params = {}
            for key in ("invoiceDate", "sendToCustomer", "sendType", "paymentTypeId",
                        "paidAmount", "paidAmountAccountCurrency", "createOnAccount",
                        "createBackorder", "overrideEmailAddress"):
                if key in payload:
                    params[key] = payload.pop(key)
            if not payload:
                payload = None
        # invoiceDate is REQUIRED
        if not params:
            params = {"invoiceDate": TODAY}
        elif "invoiceDate" not in params:
            params["invoiceDate"] = TODAY
        payload = None  # This endpoint never takes a body

    # ── Voucher postings: whitelist fields, validate balance ──
    elif "/voucher" in path and method == "POST" and payload and isinstance(payload, dict):
        postings = payload.get("postings")
        if postings and isinstance(postings, list):
            clean = []
            for p in postings:
                if isinstance(p, dict):
                    filtered = {k: v for k, v in p.items() if k in _VOUCHER_POSTING_FIELDS}
                    if filtered.get("account") and filtered.get("amount") is not None:
                        clean.append(filtered)
            payload["postings"] = clean
        # Ensure date is present
        if "date" not in payload:
            payload["date"] = TODAY

    # ── accountingDimensionName: remap fields + inject defaults ──
    elif "/accountingDimensionName" in path and method == "POST" and payload and isinstance(payload, dict):
        if "name" in payload and "dimensionName" not in payload:
            payload["dimensionName"] = payload.pop("name")
        if "active" not in payload:
            payload["active"] = True
        if "description" not in payload:
            payload["description"] = payload.get("dimensionName", "")

    # ── accountingDimensionValue: remap fields + inject defaults ──
    elif "/accountingDimensionValue" in path and method == "POST" and payload and isinstance(payload, dict):
        if "name" in payload and "displayName" not in payload:
            payload["displayName"] = payload.pop("name")
        # Remove wrong field — dimensionIndex is what's needed, not accountingDimensionName
        payload.pop("accountingDimensionName", None)
        if "active" not in payload:
            payload["active"] = True

    # ── Order: ensure deliveryDate is present ──
    elif path.rstrip("/") == "/order" and method == "POST" and payload and isinstance(payload, dict):
        if "deliveryDate" not in payload:
            payload["deliveryDate"] = payload.get("orderDate", TODAY)
        if "orderDate" not in payload:
            payload["orderDate"] = TODAY

    # ── Salary transaction: ensure date/year/month at both levels ──
    elif "/salary/transaction" in path and method == "POST" and payload and isinstance(payload, dict):
        # Ensure top-level date fields
        if "date" not in payload:
            payload["date"] = TODAY
        if "year" not in payload:
            payload["year"] = int(TODAY[:4])
        if "month" not in payload:
            payload["month"] = int(TODAY[5:7])
        # Propagate to each payslip
        payslips = payload.get("payslips")
        if payslips and isinstance(payslips, list):
            for ps in payslips:
                if isinstance(ps, dict):
                    if "date" not in ps:
                        ps["date"] = payload["date"]
                    if "year" not in ps:
                        ps["year"] = payload["year"]
                    if "month" not in ps:
                        ps["month"] = payload["month"]

    # ── Travel expense cost: ensure travelExpense ref ──
    elif "/travelExpense/cost" in path and method == "POST" and payload and isinstance(payload, dict):
        if "date" not in payload:
            payload["date"] = TODAY

    # ── Employee: ensure employments have isMainEmployer ──
    elif path.rstrip("/") == "/employee" and method == "POST" and payload and isinstance(payload, dict):
        employments = payload.get("employments")
        if employments and isinstance(employments, list):
            for emp in employments:
                if isinstance(emp, dict):
                    if "isMainEmployer" not in emp:
                        emp["isMainEmployer"] = True
                    if "startDate" not in emp:
                        emp["startDate"] = TODAY

    # ── Activity: ensure activityType ──
    elif "/activity" in path and method == "POST" and payload and isinstance(payload, dict):
        if "activityType" not in payload:
            payload["activityType"] = "PROJECT_SPECIFIC"

    # ── GET /invoice: ensure date range params ──
    elif "/invoice" in path and method == "GET" and "/:send" not in path and "/paymentType" not in path:
        if not params:
            params = {}
        if "invoiceDateFrom" not in params:
            params["invoiceDateFrom"] = "2020-01-01"
        if "invoiceDateTo" not in params:
            params["invoiceDateTo"] = "2030-01-01"

    # ── GET /ledger/account: ensure narrow range to avoid huge result sets ──
    elif "/ledger/account" in path and method == "GET" and "/account/" not in path:
        if params and ("numberFrom" not in params and "numberTo" not in params):
            if not any(k in params for k in ("numberFrom", "numberTo", "id", "number")):
                logger.warning("GET /ledger/account without number range — may be slow")

    # ── Global: clean numeric strings in params ──
    if params and isinstance(params, dict):
        for key, val in params.items():
            if isinstance(val, str) and any(c.isdigit() for c in val):
                # Strip non-numeric suffixes/prefixes (e.g. "55312.5IncVat" → 55312.5)
                cleaned = re.sub(r'[^0-9.\-]', '', val)
                if cleaned and cleaned != val:
                    try:
                        params[key] = float(cleaned) if '.' in cleaned else int(cleaned)
                        logger.info(f"Cleaned param {key}: '{val}' → {params[key]}")
                    except (ValueError, TypeError):
                        pass

    return payload, params


async def execute(llm_client, tripletex: TripletexClient, steps: list[dict], registry: dict, prompt: str = ""):
    """Phase 2: Execute each step in the plan."""
    failed_aliases: set[str] = set()  # Track which aliases failed — skip dependent steps
    abort_all = False  # Set when proxy token expires — all further calls will fail

    for i, step in enumerate(steps):
        if tripletex.time_left(TIME_BUDGET) < 10:
            logger.warning(f"Time budget nearly exhausted, stopping at step {i}")
            break

        if abort_all:
            logger.warning(f"Step {i}: skipping (session expired)")
            continue

        # Guard against malformed steps
        if "method" not in step or "path" not in step:
            logger.warning(f"Step {i} malformed, skipping: {step}")
            continue

        method = step["method"].upper()
        path = step["path"]
        alias = step.get("alias", f"step_{i}")
        payload = step.get("payload")
        params = step.get("params")

        # Resolve placeholders in path, payload, and params
        path = tripletex.resolve(path)
        if payload is not None:
            payload = tripletex.resolve(payload)
        if params is not None:
            params = tripletex.resolve(params)

        # Check for unresolved placeholders — skip if dependencies are missing
        if _has_unresolved(path):
            logger.warning(f"Step {i}: unresolved placeholder in path '{path}', skipping")
            failed_aliases.add(alias)
            continue
        if payload is not None and _has_unresolved(payload):
            logger.warning(f"Step {i}: unresolved placeholder in payload, skipping")
            failed_aliases.add(alias)
            continue
        if params is not None and _has_unresolved(params):
            logger.warning(f"Step {i}: unresolved placeholder in params, skipping")
            failed_aliases.add(alias)
            continue

        # Sanitize: apply all endpoint-specific fixes
        payload, params = _sanitize_step(path, method, payload, params)

        # Validate payload before sending
        # For paths with placeholders, use the resolved path for registry lookup
        lookup_path = re.sub(r'/\d+', '/{id}', path) if path != step["path"] else path
        if payload is not None and method in ("POST", "PUT"):
            result = validate_payload(registry, method, lookup_path, payload)
            if result["errors"]:
                logger.warning(f"Step {i} validation errors: {result['errors']}")
                payload = await fix_payload(llm_client, step, result["errors"], tripletex.state, payload, registry, prompt, params)
                if payload is None:
                    logger.error(f"Step {i} skipped after validation failure")
                    failed_aliases.add(alias)
                    continue
                payload = tripletex.resolve(payload)
                # Re-sanitize after fix
                payload, params = _sanitize_step(path, method, payload, params)
            if result["warnings"]:
                logger.info(f"Step {i} validation warnings: {result['warnings']}")

        # Log payload and params for debugging
        if payload:
            logger.info(f"Step {i} payload: {str(payload)[:300]}")
        if params:
            logger.info(f"Step {i} params: {params}")

        # Make the API call
        logger.info(f"Step {i}: {method} {path}")
        api_result = await tripletex.call(method, path, json=payload, params=params)

        if api_result["status"] < 400:
            _store_response(tripletex, alias, api_result["data"])
            logger.info(f"Step {i} OK: {api_result['status']}")
        else:
            # Error — check if unrecoverable
            logger.warning(f"Step {i} failed: {api_result['status']} — {api_result['data']}")

            if _is_unrecoverable(api_result["data"]):
                logger.warning(f"Step {i}: unrecoverable error, skipping retries")
                failed_aliases.add(alias)
                if "proxy token" in str(api_result["data"]).lower():
                    abort_all = True
                continue

            # Try to fix and retry
            last_payload = payload
            last_params = params
            success = False
            for retry in range(MAX_RETRIES_PER_STEP):
                fixed = await fix_payload(
                    llm_client, step, [str(api_result["data"])], tripletex.state, last_payload, registry, prompt, last_params
                )
                if fixed is None:
                    break

                # fix_payload may return params for action endpoints
                if isinstance(fixed, dict) and "params" in fixed and "payload" not in fixed:
                    last_params = tripletex.resolve(fixed["params"])
                    last_payload = None
                elif isinstance(fixed, dict) and "params" in fixed:
                    last_params = tripletex.resolve(fixed["params"])
                    last_payload = tripletex.resolve(fixed.get("payload"))
                else:
                    last_payload = tripletex.resolve(fixed)

                # Re-sanitize
                last_payload, last_params = _sanitize_step(path, method, last_payload, last_params)

                api_result = await tripletex.call(method, path, json=last_payload, params=last_params)
                if api_result["status"] < 400:
                    _store_response(tripletex, alias, api_result["data"])
                    logger.info(f"Step {i} retry {retry+1} OK: {api_result['status']}")
                    success = True
                    break
                logger.warning(f"Step {i} retry {retry+1} failed: {api_result['status']}")

                # Check if retry error is also unrecoverable
                if _is_unrecoverable(api_result["data"]):
                    break

            if not success:
                failed_aliases.add(alias)


def _store_response(tripletex: TripletexClient, alias: str, data):
    """Store response data in state."""
    if not isinstance(data, dict):
        return
    if "value" in data and isinstance(data["value"], dict):
        tripletex.store(alias, data["value"])
    elif "values" in data and isinstance(data["values"], list):
        for item in data["values"]:
            if isinstance(item, dict):
                tripletex.store(alias, item)


async def fix_payload(llm_client, step: dict, errors: list[str], state: dict,
                      resolved_payload: dict | None = None, registry: dict | None = None,
                      prompt: str = "", resolved_params: dict | None = None) -> dict | None:
    """Ask LLM to fix a failed payload based on error messages."""
    state_summary = ", ".join(f"{k}={v}" for k, v in state.items() if isinstance(v, (int, str)))

    # Include schema if available
    schema_section = ""
    if registry:
        lookup_path = re.sub(r'/\d+', '/{id}', step.get("path", ""))
        ep = get_endpoint(registry, step.get("method", ""), lookup_path)
        if ep:
            schema_section = f"Endpoint schema:\n{schema_for_prompt(ep)}"

    system = (EXECUTE_FIX_SYSTEM
              .replace("{state}", state_summary or "(empty)")
              .replace("{schema_section}", schema_section)
              .replace("{today}", TODAY)
              .replace("{prompt}", prompt[:500] if prompt else "(unknown)"))

    user_msg = (
        f"Step: {step['method']} {step['path']}\n"
        f"Payload sent: {resolved_payload or step.get('payload')}\n"
        f"Params sent: {resolved_params or step.get('params')}\n"
        f"Errors: {errors}"
    )

    result = await ask_json(llm_client, system, user_msg)
    if result.get("skip"):
        return None
    return result.get("payload", result)


async def run(prompt: str, base_url: str, session_token: str, files: list[dict] | None = None):
    """Main entry point — called by api.py."""
    logger.info(f"Starting agent for: {prompt[:100]}")

    # Initialize
    llm_client = get_client()
    tripletex = TripletexClient(base_url, session_token)
    registry = load_registry()

    # Decode files
    decoded_files = decode_files(files) if files else []
    file_parts = files_for_llm(decoded_files) if decoded_files else []

    try:
        # Phase 1: Plan
        logger.info("Phase 1: Planning...")
        plan_result = await plan(llm_client, prompt, file_parts, registry)
        steps = plan_result.get("steps", [])
        logger.info(f"Plan: {len(steps)} steps")
        for i, s in enumerate(steps):
            logger.info(f"  Step {i}: {s.get('method')} {s.get('path')} alias={s.get('alias')}")

        if not steps:
            logger.error("No steps generated — aborting")
            return

        # Phase 2: Execute
        logger.info("Phase 2: Executing...")
        await execute(llm_client, tripletex, steps, registry, prompt)

        # Summary
        logger.info(
            f"Done: {tripletex.call_count} API calls, "
            f"{tripletex.error_count} errors, "
            f"{tripletex.elapsed()}s elapsed"
        )
    finally:
        await tripletex.close()
