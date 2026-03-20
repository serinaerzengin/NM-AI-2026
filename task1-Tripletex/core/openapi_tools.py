"""Auto-generate OpenAI Agents SDK tools from the Tripletex OpenAPI spec."""

import json
from pathlib import Path
import httpx
from agents import function_tool

SPEC_PATH = Path(__file__).parent.parent / "docs" / "openapi.json"
_spec = None


def _get_spec():
    global _spec
    if _spec is None:
        _spec = json.loads(SPEC_PATH.read_text())
    return _spec


def _resolve_ref(ref: str) -> dict:
    name = ref.split("/")[-1]
    return _get_spec().get("components", {}).get("schemas", {}).get(name, {})


def _make_search_tool(func_name, path, desc, base_url, auth):
    @function_tool(name_override=func_name, description_override=desc)
    async def tool(query_params: str = "{}") -> str:
        """query_params: JSON string of query parameters e.g. {"fields": "id,name", "count": "10"}"""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{base_url}{path}", auth=auth, params=json.loads(query_params), timeout=30)
            return resp.text
    return tool


def _make_get_by_id_tool(func_name, path, desc, base_url, auth):
    @function_tool(name_override=func_name, description_override=desc)
    async def tool(id: int, fields: str = "*") -> str:
        """id: Entity ID. fields: Comma-separated fields to return."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{base_url}{path}/{id}", auth=auth, params={"fields": fields}, timeout=30)
            return resp.text
    return tool


def _make_create_tool(func_name, path, desc, base_url, auth):
    @function_tool(name_override=func_name, description_override=desc)
    async def tool(body: str) -> str:
        """body: JSON string of the entity to create."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{base_url}{path}", auth=auth, json=json.loads(body), timeout=30)
            return resp.text
    return tool


def _make_update_tool(func_name, path, desc, base_url, auth):
    @function_tool(name_override=func_name, description_override=desc)
    async def tool(id: int, body: str) -> str:
        """id: Entity ID. body: JSON string with updated fields (must include 'id')."""
        async with httpx.AsyncClient() as client:
            resp = await client.put(f"{base_url}{path}/{id}", auth=auth, json=json.loads(body), timeout=30)
            return resp.text
    return tool


def _make_delete_tool(func_name, path, desc, base_url, auth):
    @function_tool(name_override=func_name, description_override=desc)
    async def tool(id: int) -> str:
        """id: Entity ID to delete."""
        async with httpx.AsyncClient() as client:
            resp = await client.delete(f"{base_url}{path}/{id}", auth=auth, timeout=30)
            return resp.text or '{"status": 204}'
    return tool


def make_openapi_tools(base_url: str, token: str, skills_dir: Path | None = None):
    auth = ("0", token)
    spec = _get_spec()
    tools = []

    def load_skill(name: str) -> str:
        if skills_dir and (skills_dir / f"{name}.md").exists():
            return (skills_dir / f"{name}.md").read_text()[:2000]
        return ""

    # ── Search (GET list) ───────────────────────────────────────
    for func_name, path, category in [
        ("search_employees", "/employee", "employee"),
        ("search_customers", "/customer", "customer"),
        ("search_products", "/product", "product"),
        ("search_departments", "/department", "department"),
        ("search_contacts", "/contact", "contact"),
        ("search_invoices", "/invoice", "invoice"),
        ("search_orders", "/order", "order"),
        ("search_projects", "/project", "project"),
        ("search_travel_expenses", "/travelExpense", "travelExpense"),
        ("search_ledger_accounts", "/ledger/account", "ledger"),
        ("search_vouchers", "/ledger/voucher", "ledger"),
    ]:
        skill = load_skill(category)
        desc = f"Search/list {category}. Use 'fields' to select fields, 'count' for pagination.\n\n{skill[:1000]}"
        tools.append(_make_search_tool(func_name, path, desc, base_url, auth))

    # ── Get by ID ───────────────────────────────────────────────
    for func_name, path, category in [
        ("get_employee", "/employee", "employee"),
        ("get_customer", "/customer", "customer"),
        ("get_product", "/product", "product"),
        ("get_department", "/department", "department"),
        ("get_invoice", "/invoice", "invoice"),
        ("get_order", "/order", "order"),
        ("get_project", "/project", "project"),
        ("get_travel_expense", "/travelExpense", "travelExpense"),
    ]:
        desc = f"Get a single {category} by ID."
        tools.append(_make_get_by_id_tool(func_name, path, desc, base_url, auth))

    # ── Create (POST) ──────────────────────────────────────────
    for func_name, path in [
        ("create_employee", "/employee"),
        ("create_customer", "/customer"),
        ("create_product", "/product"),
        ("create_department", "/department"),
        ("create_contact", "/contact"),
        ("create_invoice", "/invoice"),
        ("create_order", "/order"),
        ("create_order_line", "/order/orderline"),
        ("create_project", "/project"),
        ("create_travel_expense", "/travelExpense"),
        ("create_voucher", "/ledger/voucher"),
    ]:
        # Extract field names from spec
        ep = spec.get("paths", {}).get(path, {}).get("post", {})
        summary = ep.get("summary", f"Create {path}")
        req_body = ep.get("requestBody", {})
        content = req_body.get("content", {})
        jc = content.get("application/json", content.get("application/json; charset=utf-8", {}))
        schema = jc.get("schema", {})
        if "$ref" in schema:
            resolved = _resolve_ref(schema["$ref"])
            field_names = [k for k in resolved.get("properties", {}).keys()
                          if k not in ("id", "version", "changes", "url")][:20]
        else:
            field_names = []

        category = path.strip("/").split("/")[0]
        skill = load_skill(category)
        fields_desc = ", ".join(field_names) if field_names else "see spec"
        desc = f"{summary}\nFields: {fields_desc}\n\n{skill[:1000]}"
        tools.append(_make_create_tool(func_name, path, desc, base_url, auth))

    # ── Update (PUT) ───────────────────────────────────────────
    for func_name, path in [
        ("update_employee", "/employee"),
        ("update_customer", "/customer"),
        ("update_product", "/product"),
        ("update_department", "/department"),
    ]:
        desc = f"Update {path.strip('/')} by ID. Include 'id' in body."
        tools.append(_make_update_tool(func_name, path, desc, base_url, auth))

    # ── Delete ─────────────────────────────────────────────────
    for func_name, path in [
        ("delete_customer", "/customer"),
        ("delete_travel_expense", "/travelExpense"),
        ("delete_voucher", "/ledger/voucher"),
    ]:
        desc = f"Delete {path.strip('/')} by ID."
        tools.append(_make_delete_tool(func_name, path, desc, base_url, auth))

    # ── Special actions ────────────────────────────────────────
    @function_tool
    async def invoice_payment(invoice_id: int, payment_date: str, payment_type_id: int, amount: float) -> str:
        """Register payment on an invoice. payment_date: YYYY-MM-DD."""
        async with httpx.AsyncClient() as client:
            resp = await client.put(
                f"{base_url}/invoice/{invoice_id}/:payment", auth=auth,
                json={"paymentDate": payment_date, "paymentTypeId": payment_type_id, "amount": amount}, timeout=30)
            return resp.text
    tools.append(invoice_payment)

    @function_tool
    async def invoice_credit_note(invoice_id: int) -> str:
        """Create a credit note for an invoice, nullifying it."""
        async with httpx.AsyncClient() as client:
            resp = await client.put(f"{base_url}/invoice/{invoice_id}/:createCreditNote", auth=auth, timeout=30)
            return resp.text
    tools.append(invoice_credit_note)

    @function_tool
    async def reverse_voucher(voucher_id: int) -> str:
        """Reverse a voucher, creating a reversal entry."""
        async with httpx.AsyncClient() as client:
            resp = await client.put(f"{base_url}/ledger/voucher/{voucher_id}/:reverse", auth=auth, timeout=30)
            return resp.text
    tools.append(reverse_voucher)

    @function_tool
    async def grant_employee_entitlements(employee_id: int, template: str) -> str:
        """Grant entitlements/permissions to an employee using a template.
        Use this to make an employee an administrator or assign roles.
        employee_id: The employee ID.
        template: One of NONE_PRIVILEGES, ALL_PRIVILEGES, INVOICING_MANAGER, PERSONELL_MANAGER, ACCOUNTANT, AUDITOR, DEPARTMENT_LEADER.
        For 'kontoadministrator' / 'account administrator' use ALL_PRIVILEGES.
        IMPORTANT: Employee must be created with userType EXTENDED (not STANDARD) to receive entitlements."""
        async with httpx.AsyncClient() as client:
            resp = await client.put(
                f"{base_url}/employee/entitlement/:grantEntitlementsByTemplate",
                auth=auth,
                params={"employeeId": employee_id, "template": template},
                timeout=30,
            )
            return resp.text
    tools.append(grant_employee_entitlements)

    return tools
