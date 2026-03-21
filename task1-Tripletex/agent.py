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
            "description": """GET request to Tripletex API.
Key patterns:
- /customer?organizationNumber=X, /supplier?organizationNumber=X, /employee?email=X — find existing entities
- /ledger/account?number=N1,N2,N3 — batch lookup accounts (ALWAYS batch, never one at a time)
- /ledger/posting?dateFrom=X&dateTo=Y — REQUIRES dateFrom+dateTo always
- /invoice?customerId=X&invoiceDateFrom=2020-01-01&invoiceDateTo=2030-01-01 — REQUIRES date range
- /ledger/voucherType, /invoice/paymentType, /salary/type — lookup reference data
- /balanceSheet?dateFrom=X&dateTo=Y — REQUIRES dateFrom+dateTo
- /department, /division — lookup org structure
- /travelExpense/costCategory, /travelExpense/rateCategory?type=PER_DIEM&isValidDomestic=true&dateFrom=X&dateTo=Y""",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "API path, e.g. /customer or /ledger/account?number=1920,2400,6300",
                    },
                    "params": {
                        "type": "string",
                        "description": 'Query parameters as JSON string, e.g. \'{"organizationNumber": "912345678"}\'',
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
            "description": """POST request to Tripletex API. Creates new resources.
Key workflows:
- Employee: POST /employee {firstName,lastName,email,dateOfBirth,userType:"EXTENDED",department:{id}} → POST /employee/entitlement {employee:{id},customer:{id:companyId},entitlementId:1} for admin → POST /employee/employment {employee:{id},division:{id},startDate} → POST /employee/employment/details {employment:{id},annualSalary,percentageOfFullTimeEquivalent}
- Customer: POST /customer {name,isCustomer:true,email,organizationNumber,postalAddress:{...},physicalAddress:{...}}
- Supplier: POST /supplier {name,isSupplier:true,organizationNumber,postalAddress:{...},physicalAddress:{...}}
- Product: POST /product {name,number(STRING),priceExcludingVatCurrency,vatType:{id}}
- Order: POST /order {customer:{id},orderDate,deliveryDate(required),orderLines:[{product:{id},count}]} — NO vatType on orderLines
- Voucher: POST /ledger/voucher {date,description(required),voucherType:{id},postings:[{account:{id},amountGross,amountGrossCurrency,row(from 1)}]} — postings MUST sum to 0
- Salary: POST /salary/transaction {date,year,month,payslips:[{employee:{id},date,year,month,specifications:[{salaryType:{id},rate(not amount),count}]}]}
- Division: POST /division {name,startDate,organizationNumber(random 9-digit),municipalityDate,municipality:{id:301}}
- Travel expense: POST /travelExpense {title,employee:{id}} → PUT convert → PUT travelDetails → POST costs (amountCurrencyIncVat, NOT amount)
- Batch: POST /product/list, /department/list, /ledger/account/list for multiple items in one call
- Correction voucher: reverse wrong postings with negated amounts + add correct postings""",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "API path, e.g. /customer or /ledger/voucher",
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
            "description": """PUT request to Tripletex API. For updates and action endpoints.
Action endpoints use QUERY PARAMS (not body):
- PUT /order/{id}/:invoice?invoiceDate=DATE — create invoice from order
- PUT /invoice/{id}/:payment?paymentDate=DATE&paymentTypeId=ID&paidAmount=AMOUNT — register payment (paidAmount incl VAT, negative for reversal)
- PUT /invoice/{id}/:createCreditNote?date=DATE — create credit note
- PUT /invoice/{id}/:send?sendType=EMAIL — send invoice
- PUT /travelExpense/{id}/convert — convert to travel report (REQUIRED before per diem/travelDetails)
- PUT /travelExpense/{id} — set travelDetails:{departureDate,returnDate,destination,isDayTrip:false,isForeignTravel:false,isCompensationFromRates:true}
Foreign currency: after payment, book exchange rate difference as voucher. Agio(gain)→credit 8060, Disagio(loss)→debit 8160.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "API path, e.g. /order/123/:invoice",
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
            "description": "DELETE request. For travel expenses: DELETE /travelExpense/{id}. Posted vouchers CANNOT be deleted — use correction voucher instead.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "API path with ID, e.g. /travelExpense/123",
                    },
                },
                "required": ["path"],
            },
        },
    },
]


def _slim_account(acct: dict) -> dict:
    """Keep only id, number, name from account objects."""
    return {k: acct[k] for k in ("id", "number", "name") if k in acct}


def _slim_values(values: list, path: str) -> list:
    """Strip bulky fields from list responses based on endpoint."""
    if "/ledger/account" in path:
        return [_slim_account(v) for v in values]
    if "/ledger/posting" in path:
        return [
            {k: (_slim_account(v[k]) if k == "account" and isinstance(v.get(k), dict) else v[k])
             for k in ("id", "row", "account", "amountGross", "description") if k in v}
            for v in values
        ]
    return values


def _truncate_response(data, max_chars=6000, max_items=50, path="") -> str:
    """Truncate API response to fit in context."""
    if isinstance(data, dict):
        # Response is {"status": N, "data": {...}} — look for values inside "data"
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
                    inner["values"] = _slim_values(values, path)
                    if len(inner["values"]) > max_items:
                        inner["values"] = inner["values"][:max_items]
                        inner["_truncated"] = f"Showing {max_items} of {len(values)} items"
                # Update the outer dict
                if "data" in data:
                    data = dict(data)
                    data["data"] = inner
                else:
                    data = inner

            # Slim single-object "value" responses
            value = inner.get("value")
            if isinstance(value, dict) and "/ledger/account" in path:
                inner = dict(inner)
                inner["value"] = _slim_account(value)
                if "data" in data:
                    data = dict(data)
                    data["data"] = inner
                else:
                    data = inner

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

        # apply_fixes only works on dict payloads, not list (batch endpoints)
        if isinstance(payload, dict):
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

        if payload and isinstance(payload, dict):
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
    get_cache = {}  # Cache duplicate GET requests

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
                reasoning_effort="high",
            )
        except Exception as e:
            print(f"[{req_id}][AGENT] LLM call failed: {e}", file=sys.stderr)
            # Retry once — try without reasoning_effort in case of compatibility issue
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

            # Guardrail: cache duplicate GET requests
            cache_key = f"{fn_name}:{fn_args}" if fn_name == "tripletex_get" else None
            if cache_key and cache_key in get_cache:
                result_str = get_cache[cache_key]
                print(f"[{req_id}][CACHE] Hit for {fn_args[:100]}", file=sys.stderr)
                tripletex_client.call_count -= 0  # don't count cached
            else:
                result_str = await execute_tool(fn_name, fn_args, tripletex_client)
                if cache_key:
                    get_cache[cache_key] = result_str

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result_str,
            })

        # Guardrail: warn if too many GETs without writes
        gets_since_write = 0
        for m in reversed(messages):
            if isinstance(m, dict) and m.get("role") == "tool":
                gets_since_write += 1
            elif hasattr(m, 'tool_calls') and m.tool_calls:
                if any(tc.function.name in ("tripletex_post", "tripletex_put", "tripletex_delete") for tc in m.tool_calls):
                    break
        if gets_since_write > 8:
            messages.append({
                "role": "user",
                "content": f"WARNING: You have made {gets_since_write} GET calls without any POST/PUT. You should have enough data. Create the required resources NOW.",
            })

    return {
        "status": "completed",
        "api_calls": tripletex_client.call_count,
        "errors": tripletex_client.error_count,
        "iterations": min(iteration + 1, max_iterations) if 'iteration' in dir() else 0,
    }
