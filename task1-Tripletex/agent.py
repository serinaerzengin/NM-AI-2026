import json
import os
import sys
import time
import re

from openai import AsyncOpenAI

from apply_fixes import apply_fixes, ensure_bank_account, create_employment
from system_prompt import build_system_prompt

# Tool definitions for the LLM
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "tripletex_get",
            "description": "GET request to Tripletex API. Returns JSON response with status and data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "API path, e.g. /customer or /employee/123",
                    },
                    "params": {
                        "type": "string",
                        "description": 'Query parameters as JSON string, e.g. \'{"name": "Ola"}\'',
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tripletex_post",
            "description": "POST request to Tripletex API. Creates a new resource.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "API path, e.g. /customer or /order",
                    },
                    "body": {
                        "type": "string",
                        "description": "Request body as JSON string",
                    },
                },
                "required": ["path", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tripletex_put",
            "description": "PUT request to Tripletex API. For updates and action endpoints (/:invoice, /:payment, /:send, etc.). Action endpoints use query params.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "API path, e.g. /order/123/:invoice or /employee/456",
                    },
                    "body": {
                        "type": "string",
                        "description": 'Request body as JSON string. Use "{}" for action endpoints.',
                    },
                    "params": {
                        "type": "string",
                        "description": 'Query parameters as JSON string, e.g. \'{"invoiceDate": "2026-03-21"}\'',
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tripletex_delete",
            "description": "DELETE request to Tripletex API. Deletes a resource by ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "API path with ID, e.g. /travelExpense/123 or /ledger/voucher/456",
                    },
                },
                "required": ["path"],
            },
        },
    },
]


def _truncate_response(data, max_chars=4000, max_items=10, path="") -> str:
    """Truncate API response to fit in context."""
    if isinstance(data, dict):
        # For list responses, smart truncation
        values = data.get("values")
        if isinstance(values, list):
            # For vatType, show more items (important for sandbox compatibility)
            if "vatType" in path:
                # Show all standard VAT types (id < 100) for completeness
                filtered = [v for v in values if v.get("id", 999) < 100]
                data = dict(data)
                data["values"] = filtered
                data["_note"] = f"Showing {len(filtered)} standard VAT types (id < 100)"
            elif len(values) > max_items:
                data = dict(data)
                data["values"] = values[:max_items]
                data["_truncated"] = f"Showing {max_items} of {len(values)} items"

    text = json.dumps(data, ensure_ascii=False, default=str)
    if len(text) > max_chars:
        text = text[:max_chars] + "... [truncated]"
    return text


def _extract_employee_id(payload) -> int | None:
    """Try to extract employee ID from salary payload."""
    for ps in payload.get("payslips", []):
        emp = ps.get("employee", {})
        if isinstance(emp, dict) and emp.get("id"):
            return emp["id"]
    return None


async def execute_tool(name: str, args_str: str, client) -> str:
    """Execute a tool call and return the result string."""
    try:
        args = json.loads(args_str) if args_str else {}
    except json.JSONDecodeError as e:
        return f"Invalid JSON arguments: {e}"

    path = args.get("path", "")

    if name == "tripletex_get":
        params = None
        if args.get("params"):
            try:
                params = json.loads(args["params"]) if isinstance(args["params"], str) else args["params"]
            except (json.JSONDecodeError, TypeError):
                params = None
        result = await client.call("GET", path, params=params)
        return _truncate_response(result, path=path)

    elif name == "tripletex_post":
        body_raw = args.get("body", "{}")
        try:
            payload = json.loads(body_raw) if isinstance(body_raw, str) else body_raw
        except json.JSONDecodeError as e:
            return f"Invalid JSON body: {e}"

        payload = apply_fixes(path, "POST", payload)

        result = await client.call("POST", path, json_data=payload)

        # Error recovery
        if result["status"] >= 400:
            error_msg = json.dumps(result.get("data", {}), ensure_ascii=False).lower()

            # Entity already exists
            if "allerede" in error_msg or "i bruk" in error_msg or "already" in error_msg:
                return f"Entity already exists. Use GET {path} to find it instead of creating. Original error: {_truncate_response(result, path=path)}"

            # Invalid VAT type — hint to query available types
            if "ugyldig mva-kode" in error_msg or "vattype" in error_msg:
                return f"Invalid VAT type ID. Query GET /ledger/vatType to see which VAT types are available, then retry with the correct ID. Original error: {_truncate_response(result, path=path)}"

            # No employment record for salary
            if "arbeidsforhold" in error_msg and "/salary" in path:
                emp_id = _extract_employee_id(payload)
                if emp_id:
                    await create_employment(client, emp_id)
                    result = await client.call("POST", path, json_data=payload)
                    if result["status"] < 400:
                        return _truncate_response(result)

            # Bank account missing
            if "bankkontonummer" in error_msg or "bank account" in error_msg.lower():
                await ensure_bank_account(client)
                return f"Bank account was missing and has been registered. Please retry your request. Original error: {_truncate_response(result)}"

        return _truncate_response(result)

    elif name == "tripletex_put":
        params = None
        if args.get("params"):
            try:
                params = json.loads(args["params"]) if isinstance(args["params"], str) else args["params"]
            except (json.JSONDecodeError, TypeError):
                params = None

        body_raw = args.get("body", "{}")
        payload = None
        if body_raw and body_raw != "{}":
            try:
                payload = json.loads(body_raw) if isinstance(body_raw, str) else body_raw
            except json.JSONDecodeError:
                payload = None

        if payload:
            payload = apply_fixes(path, "PUT", payload)

        # Proactive bank account setup for action endpoints
        if "/:invoice" in path or "/:payment" in path:
            await ensure_bank_account(client)

        result = await client.call("PUT", path, json_data=payload, params=params)

        # Bank account error recovery
        if result["status"] >= 400:
            error_msg = json.dumps(result.get("data", {}), ensure_ascii=False).lower()
            if "bankkontonummer" in error_msg or "bank account" in error_msg:
                await ensure_bank_account(client)
                result = await client.call("PUT", path, json_data=payload, params=params)

        return _truncate_response(result)

    elif name == "tripletex_delete":
        result = await client.call("DELETE", path)
        return _truncate_response(result)

    return f"Unknown tool: {name}"


async def run_agent(prompt: str, file_contents: list, tripletex_client, req_id: str = "????") -> dict:
    """Run the agent loop."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    model = os.environ.get("LLM_MODEL", "gemini-3.1-pro-preview")

    openai_client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )

    system_prompt = build_system_prompt()

    # Build user message content
    user_content = [{"type": "text", "text": prompt}]
    if file_contents:
        user_content.extend(file_contents)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    start_time = time.time()
    max_iterations = 50
    time_budget = 270  # seconds (competition allows 300s, leave 30s margin)

    for iteration in range(max_iterations):
        elapsed = time.time() - start_time
        if elapsed > time_budget:
            print(f"[{req_id}][AGENT] Time budget exhausted at {elapsed:.1f}s", file=sys.stderr)
            break

        try:
            response = await openai_client.chat.completions.create(
                model=model,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.1,
            )
        except Exception as e:
            print(f"[{req_id}][AGENT] LLM call failed: {e}", file=sys.stderr)
            # Retry once
            try:
                response = await openai_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    temperature=0.2,
                )
            except Exception as e2:
                print(f"[{req_id}][AGENT] LLM retry failed: {e2}", file=sys.stderr)
                break

        choice = response.choices[0]
        message = choice.message

        # Append assistant message
        messages.append(message)

        # Check if done (no tool calls)
        if not message.tool_calls:
            print(f"[{req_id}][AGENT] Done at iteration {iteration + 1}, {time.time() - start_time:.1f}s", file=sys.stderr)
            break

        # Execute tool calls
        for tool_call in message.tool_calls:
            fn_name = tool_call.function.name
            fn_args = tool_call.function.arguments
            print(f"[{req_id}][TOOL] {fn_name}: {fn_args[:200]}", file=sys.stderr)

            result_str = await execute_tool(fn_name, fn_args, tripletex_client)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result_str,
            })

    return {
        "status": "completed",
        "api_calls": tripletex_client.call_count,
        "errors": tripletex_client.error_count,
        "iterations": min(iteration + 1, max_iterations) if 'iteration' in dir() else 0,
    }
