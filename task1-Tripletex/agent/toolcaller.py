"""
Step 5: Tool-Calling Executor.

Receives ONLY the structured ExecutionPlan + credentials + files.
Does NOT see: original prompt, translation, rewrite, index.md, or full registry.

Design principles (from research):
- Plan-then-Execute: plan is already made, executor just follows it
- No JSON reasoning: the agent reasons in natural language, tool calls are typed functions
- Schema-grounded: exact field names/types come from registry.json (via the plan)
- _ref stubs: linked entities use {"id": N}, executor resolves IDs from prior step results
- response.type: executor reads .value (single) or .values (list) as indicated
- Minimal context: only the plan steps + their schemas are in the prompt, not 800 endpoints
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
from agents import Agent, Runner, RunContextWrapper, function_tool

from agent.config import MODEL_ID
from agent.logging_config import write_trace
from agents.extensions.models.litellm_model import LitellmModel

logger = logging.getLogger("tripletex-agent.toolcaller")

model = LitellmModel(model=MODEL_ID)


# ── Execution context (passed via RunContext) ────────────────────────────────


@dataclass
class ToolContext:
    """Shared state for the executor agent's tools."""

    base_url: str
    auth: tuple[str, str]  # ("0", session_token)
    step_results: dict[int, Any] = field(default_factory=dict)
    call_log: list[dict] = field(default_factory=list)


# ── Tools ────────────────────────────────────────────────────────────────────


@function_tool
async def tripletex_get(
    ctx: RunContextWrapper[ToolContext],
    endpoint: str,
    params: str = "{}",
) -> str:
    """Make a GET request to the Tripletex API.

    Args:
        endpoint: The API path, e.g. "/employee" or "/customer/123"
        params: JSON string of query parameters, e.g. '{"name": "Acme", "fields": "id,name"}'
    """
    tc = ctx.context
    query = json.loads(params) if params else {}

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{tc.base_url}{endpoint}",
            params=query,
            auth=tc.auth,
            timeout=30.0,
        )

    result = _log_call(tc, "GET", endpoint, query, None, resp)
    return result


@function_tool
async def tripletex_post(
    ctx: RunContextWrapper[ToolContext],
    endpoint: str,
    body: str = "{}",
) -> str:
    """Make a POST request to the Tripletex API to create an entity.

    Args:
        endpoint: The API path, e.g. "/employee" or "/customer"
        body: JSON string of the request body with the fields to create
    """
    tc = ctx.context
    payload = json.loads(body) if body else {}

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{tc.base_url}{endpoint}",
            json=payload,
            auth=tc.auth,
            timeout=30.0,
        )

    result = _log_call(tc, "POST", endpoint, None, payload, resp)
    return result


@function_tool
async def tripletex_put(
    ctx: RunContextWrapper[ToolContext],
    endpoint: str,
    body: str = "{}",
    params: str = "{}",
) -> str:
    """Make a PUT request to the Tripletex API to update an entity or trigger an action.

    Args:
        endpoint: The API path, e.g. "/employee/123" or "/employee/entitlement/:grantEntitlementsByTemplate"
        body: JSON string of the request body (empty for action endpoints)
        params: JSON string of query parameters
    """
    tc = ctx.context
    payload = json.loads(body) if body and body != "{}" else None
    query = json.loads(params) if params and params != "{}" else {}

    async with httpx.AsyncClient() as client:
        resp = await client.put(
            f"{tc.base_url}{endpoint}",
            json=payload,
            params=query,
            auth=tc.auth,
            timeout=30.0,
        )

    result = _log_call(tc, "PUT", endpoint, query, payload, resp)
    return result


@function_tool
async def tripletex_delete(
    ctx: RunContextWrapper[ToolContext],
    endpoint: str,
) -> str:
    """Make a DELETE request to the Tripletex API.

    Args:
        endpoint: The API path including ID, e.g. "/travelExpense/123"
    """
    tc = ctx.context

    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{tc.base_url}{endpoint}",
            auth=tc.auth,
            timeout=30.0,
        )

    result = _log_call(tc, "DELETE", endpoint, None, None, resp)
    return result


@function_tool
async def store_step_result(
    ctx: RunContextWrapper[ToolContext],
    step_number: int,
    key: str,
    value: str,
) -> str:
    """Store a result from a completed step so later steps can reference it.

    Use this to save IDs or values from API responses that later steps need.

    Args:
        step_number: Which step produced this result (e.g. 1)
        key: A descriptive key (e.g. "customer_id", "order_id")
        value: The value to store (e.g. "12345")
    """
    tc = ctx.context
    if step_number not in tc.step_results:
        tc.step_results[step_number] = {}
    tc.step_results[step_number][key] = value
    logger.info("STORED step_%d.%s = %s", step_number, key, value)
    return f"Stored: step_{step_number}.{key} = {value}"


@function_tool
async def get_step_result(
    ctx: RunContextWrapper[ToolContext],
    step_number: int,
    key: str,
) -> str:
    """Retrieve a stored result from a previous step.

    Args:
        step_number: Which step to look up (e.g. 1)
        key: The key that was stored (e.g. "customer_id")
    """
    tc = ctx.context
    step_data = tc.step_results.get(step_number, {})
    value = step_data.get(key, None)
    if value is None:
        return f"No result found for step_{step_number}.{key}"
    return str(value)


# ── Helper ───────────────────────────────────────────────────────────────────


def _log_call(
    tc: ToolContext,
    method: str,
    endpoint: str,
    params: dict | None,
    body: dict | None,
    resp: httpx.Response,
) -> str:
    """Log the API call and return a formatted result string."""
    status = resp.status_code
    try:
        resp_body = resp.json()
    except Exception:
        resp_body = resp.text[:500]

    entry = {
        "method": method,
        "endpoint": endpoint,
        "params": params,
        "body": body,
        "status": status,
        "response": resp_body if status >= 400 else _summarize_response(resp_body),
    }
    tc.call_log.append(entry)

    if status >= 400:
        logger.warning(
            "API_ERROR | %s %s | %d | %s",
            method, endpoint, status,
            json.dumps(resp_body, ensure_ascii=False, default=str)[:300],
        )
        return json.dumps({"status": status, "error": resp_body}, ensure_ascii=False, default=str)
    else:
        logger.info("API_OK | %s %s | %d", method, endpoint, status)
        return json.dumps({"status": status, "data": resp_body}, ensure_ascii=False, default=str)


def _summarize_response(body: Any) -> Any:
    """Keep response in log but trim large payloads."""
    if isinstance(body, dict):
        if "value" in body:
            return {"value": _trim_entity(body["value"])}
        if "values" in body:
            values = body["values"]
            return {
                "count": len(values) if isinstance(values, list) else "?",
                "values": [_trim_entity(v) for v in values[:3]] if isinstance(values, list) else values,
            }
    return body


def _trim_entity(entity: Any) -> Any:
    """Keep only id and a few key fields for logging."""
    if not isinstance(entity, dict):
        return entity
    keep = {"id", "name", "firstName", "lastName", "email", "number", "displayName"}
    return {k: v for k, v in entity.items() if k in keep}


# ── Build the executor prompt from the plan ─────────────────────────────────


def _build_executor_prompt(plan_steps: list, files: list | None = None) -> str:
    """Build a natural language prompt for the executor from the structured plan.

    The agent gets:
    - The ordered steps with descriptions and dependencies
    - The schema for each endpoint (field names, types, enums, _ref hints)
    - File info if present

    The agent does NOT get:
    - The original user prompt
    - index.md or full registry.json
    """
    lines = [
        "Execute the following plan step by step. Each step is one API call.",
        "",
        "IMPORTANT RULES:",
        "- Follow the step order. Respect depends_on — do not execute a step until its dependencies are done.",
        "- Use ONLY the field names shown in the schema. Do not guess or invent field names.",
        "- For fields marked REQUIRED — you MUST include them or the API will return 422.",
        "- For fields with _ref (linked entities), send ONLY {\"id\": <int>}. If you don't have the ID yet,",
        "  make a GET request to find it BEFORE the step that needs it. This is allowed even if not in the plan.",
        "- After each API call, use store_step_result to save any IDs or values that later steps need.",
        "- Use get_step_result to retrieve values saved by earlier steps.",
        "- For GET responses: .value has a single entity, .values has a list.",
        "- Query parameters go in the params argument, NOT in the endpoint URL.",
        "  Example: tripletex_put(endpoint='/employee/entitlement/:grantEntitlementsByTemplate', params='{\"employeeId\": 123, \"template\": \"ALL_PRIVILEGES\"}')",
        "- If a step has a condition (e.g. 'only if step 1 returns empty'), check before executing.",
        "- If you get a 422 error, read the validationMessages carefully and fix the request.",
        "- Do NOT retry more than once with the same payload — adjust based on the error.",
        "",
    ]

    if files:
        lines.append(f"ATTACHED FILES ({len(files)}):")
        for f in files:
            lines.append(f"  - {f['filename']} ({f['mime_type']}, {len(f.get('content_base64', ''))} bytes b64)")
        lines.append("")

    lines.append("=" * 50)
    lines.append("EXECUTION PLAN")
    lines.append("=" * 50)

    for s in plan_steps:
        lines.append("")
        deps = f" (after Step {', '.join(str(d) for d in s.depends_on)})" if s.depends_on else ""
        lines.append(f"STEP {s.step}: {s.action}{deps}")
        lines.append(f"  Method: {s.method}")
        lines.append(f"  Endpoint: {s.endpoint}")

        if s.condition:
            lines.append(f"  Condition: {s.condition}")

        schema = s.schema
        if not schema:
            lines.append("  Schema: NOT FOUND — proceed with caution")
            continue

        # Show request body fields for POST/PUT
        req_body = schema.get("request_body", {})
        props = req_body.get("properties", {})
        required_fields = set(req_body.get("required", []))

        # Heuristic: _ref fields and enum fields are almost always required by Tripletex
        # even when the OpenAPI spec doesn't mark them. Flag them prominently.
        if props:
            lines.append("  Request body fields:")
            for fname, fschema in props.items():
                ftype = fschema.get("type", "?")
                ref = fschema.get("_ref", "")
                enum = fschema.get("enum", [])
                desc = fschema.get("description", "")
                is_required = fname in required_fields

                parts = [f"    - {fname}: {ftype}"]
                if is_required:
                    parts.append("REQUIRED")
                if ref:
                    parts.append(f'(linked entity → send {{"id": <int>}}, GET /{ref.lower()} to find ID)')
                if enum:
                    parts.append(f"(enum: {enum})")
                if desc:
                    parts.append(f"— {desc[:80]}")
                lines.append(" ".join(parts))

        # Show query params for GET/action endpoints
        qparams = schema.get("query_params", [])
        if qparams:
            lines.append("  Query parameters:")
            for qp in qparams:
                qname = qp.get("name", "?")
                qtype = qp.get("type", "?")
                qdesc = qp.get("description", "")
                qreq = " (required)" if qp.get("required") else ""
                lines.append(f"    - {qname}: {qtype}{qreq} — {qdesc[:60]}")

        # Show response type
        resp_info = schema.get("response", {})
        rtype = resp_info.get("type", "")
        if rtype:
            accessor = ".value" if rtype == "single" else ".values"
            lines.append(f"  Response: read from {accessor}")

    return "\n".join(lines)


# ── Executor agent ───────────────────────────────────────────────────────────

executor_agent = Agent[ToolContext](
    name="Executor",
    model=model,
    tools=[
        tripletex_get,
        tripletex_post,
        tripletex_put,
        tripletex_delete,
        store_step_result,
        get_step_result,
    ],
    instructions=(
        "You are a precise API execution agent for Tripletex accounting software.\n\n"
        "You receive a structured execution plan. Execute each step in order using the tools provided.\n\n"
        "Rules:\n"
        "- Execute steps in dependency order. If Step 2 depends on Step 1, finish Step 1 first.\n"
        "- Use the exact field names from the schema. Never guess field names.\n"
        "- After each successful POST/PUT, store the created entity's ID with store_step_result.\n"
        "- Before a step that needs a previous ID, retrieve it with get_step_result.\n"
        "- For _ref fields (linked entities), send only {\"id\": <int>} — not the full object.\n"
        "  If you need an ID you don't have, do a GET to find it first.\n"
        "- Read single-entity responses from .value and list responses from .values.\n"
        "- If a GET returns empty .values, the entity doesn't exist yet.\n"
        "- If a step has a condition, evaluate it before making the call.\n"
        "- Pass params and body as JSON strings to the tools.\n"
        "- Query parameters go in the params argument. Do NOT append them to the endpoint URL.\n"
        "- If you get a 422 error, read the validationMessages in the response.\n"
        "  They tell you exactly which field is missing or wrong. Fix it and retry ONCE.\n"
        "- You may make extra GET calls to resolve IDs (departments, categories) if needed.\n"
        "- When done with all steps, say DONE."
    ),
)


# ── Execute ──────────────────────────────────────────────────────────────────


async def execute(
    plan_steps: list,
    base_url: str,
    session_token: str,
    files: list | None = None,
) -> ToolContext:
    """Execute the structured plan against the Tripletex API.

    Receives ONLY: plan steps, credentials, files.
    Does NOT receive: original prompt, translation, rewrite, index.md, full registry.
    """
    start = time.monotonic()

    ctx = ToolContext(
        base_url=base_url,
        auth=("0", session_token),
    )

    prompt = _build_executor_prompt(plan_steps, files)

    logger.info(
        "EXECUTOR_START | %d steps | base_url=%s",
        len(plan_steps),
        base_url[:50],
    )

    result = await Runner.run(
        executor_agent,
        input=prompt,
        context=ctx,
        max_turns=25,
    )

    duration_ms = (time.monotonic() - start) * 1000

    # Trace the execution
    write_trace(
        step=5,
        name="EXECUTE",
        input_text=f"{len(plan_steps)} plan steps",
        output_text=result.final_output[:500] if result.final_output else "no output",
        duration_ms=duration_ms,
        extra={
            "api_calls": len(ctx.call_log),
            "errors": sum(1 for c in ctx.call_log if c["status"] >= 400),
            "step_results": ctx.step_results,
            "call_log": ctx.call_log,
        },
    )

    logger.info(
        "EXECUTOR_DONE | %.0fms | %d API calls | %d errors",
        duration_ms,
        len(ctx.call_log),
        sum(1 for c in ctx.call_log if c["status"] >= 400),
    )

    return ctx
