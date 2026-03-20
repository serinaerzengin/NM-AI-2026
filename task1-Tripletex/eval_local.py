"""
Local evaluation runner — tests the full pipeline against the sandbox.

Usage:
    source .env && uv run python eval_local.py
    source .env && uv run python eval_local.py --case 0   # run a single case
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time

import httpx

# Ensure agent package is importable
sys.path.insert(0, os.path.dirname(__file__))

from agent.logging_config import setup_logging
from agent.pipeline import preprocess, PipelineResult
from agent.toolcaller import execute

setup_logging()

BASE_URL = os.environ["TRIPLETEX_BASE_URL"]
TOKEN = os.environ["TRIPLETEX_SESSION_TOKEN"]
AUTH = ("0", TOKEN)


# ── Test cases ──────────────────────────────────────────────────────────────

EVAL_CASES = [
    {
        "name": "Create employee (Norwegian)",
        "prompt": "Opprett en ansatt med navn Kari Hansen, kari.hansen@example.com. Hun skal ha brukertype STANDARD.",
        "verify": lambda: verify_employee("Kari", "Hansen", "kari.hansen@example.com"),
    },
    {
        "name": "Create customer (English)",
        "prompt": "Create a customer named 'Nordic Solutions AS' with email nordic@solutions.no.",
        "verify": lambda: verify_customer("Nordic Solutions AS"),
    },
    {
        "name": "Create product (Spanish)",
        "prompt": "Crea un producto llamado 'Servicio de Consultoría' con un precio de 2500 NOK.",
        "verify": lambda: verify_product("Consultoría"),
    },
    {
        "name": "Create department (German)",
        "prompt": "Erstellen Sie eine Abteilung mit dem Namen 'Buchhaltung'.",
        "verify": lambda: verify_department("Buchhaltung"),
    },
    {
        "name": "Create customer + product (Norwegian)",
        "prompt": "Opprett en kunde med navn 'Fjord Tech AS' og epost fjord@tech.no. Opprett også et produkt 'Webdesign' til 3500 kr.",
        "verify": lambda: verify_customer_and_product("Fjord Tech AS", "Webdesign"),
    },
]


# ── Verification helpers ────────────────────────────────────────────────────

async def verify_employee(first: str, last: str, email: str) -> dict:
    async with httpx.AsyncClient() as c:
        resp = await c.get(
            f"{BASE_URL}/employee",
            auth=AUTH,
            params={"fields": "id,firstName,lastName,email", "count": 100},
        )
    data = resp.json()
    values = data.get("values", [])
    # Search through all employees for a match
    for emp in values:
        if emp.get("firstName") == first and emp.get("lastName") == last:
            checks = {
                "found": True,
                "firstName": emp.get("firstName") == first,
                "lastName": emp.get("lastName") == last,
                "email": emp.get("email") == email,
            }
            return {"pass": all(checks.values()), "checks": checks, "entity": emp}
    return {"pass": False, "reason": f"Employee {first} {last} not found in {len(values)} employees"}


async def verify_customer(name_contains: str) -> dict:
    async with httpx.AsyncClient() as c:
        resp = await c.get(
            f"{BASE_URL}/customer",
            auth=AUTH,
            params={"fields": "id,name,email", "count": 100},
        )
    data = resp.json()
    values = data.get("values", [])
    for v in values:
        if name_contains.lower() in v.get("name", "").lower():
            return {"pass": True, "entity": v}
    return {"pass": False, "reason": f"Customer '{name_contains}' not found in {len(values)} customers"}


async def verify_product(name_contains: str) -> dict:
    async with httpx.AsyncClient() as c:
        resp = await c.get(
            f"{BASE_URL}/product",
            auth=AUTH,
            params={"fields": "id,name", "count": 100},
        )
    data = resp.json()
    values = data.get("values", [])
    for v in values:
        if name_contains.lower() in v.get("name", "").lower():
            return {"pass": True, "entity": v}
    return {"pass": False, "reason": f"Product '{name_contains}' not found in {len(values)} products"}


async def verify_department(name_contains: str) -> dict:
    async with httpx.AsyncClient() as c:
        resp = await c.get(
            f"{BASE_URL}/department",
            auth=AUTH,
            params={"fields": "id,name", "count": 100},
        )
    data = resp.json()
    values = data.get("values", [])
    for v in values:
        if name_contains.lower() in v.get("name", "").lower():
            return {"pass": True, "entity": v}
    return {"pass": False, "reason": f"Department '{name_contains}' not found in {len(values)} departments"}


async def verify_customer_and_product(cust_name: str, prod_name: str) -> dict:
    cust = await verify_customer(cust_name)
    prod = await verify_product(prod_name)
    both_pass = cust.get("pass", False) and prod.get("pass", False)
    return {"pass": both_pass, "customer": cust, "product": prod}


# ── Runner ──────────────────────────────────────────────────────────────────

async def run_case(idx: int, case: dict) -> dict:
    name = case["name"]
    prompt = case["prompt"]
    print(f"\n{'='*70}")
    print(f"EVAL {idx}: {name}")
    print(f"PROMPT: {prompt}")
    print(f"{'='*70}")

    start = time.monotonic()
    result_data = {"name": name, "prompt": prompt}

    try:
        # Preprocess
        pp_result: PipelineResult = await preprocess(prompt)
        result_data["plan_steps"] = len(pp_result.plan.steps)
        result_data["preprocess_ms"] = sum(t.duration_ms for t in pp_result.trace.traces)

        print(f"\n  Plan: {len(pp_result.plan.steps)} steps")
        for s in pp_result.plan.steps:
            print(f"    Step {s.step}: {s.method} {s.endpoint} — {s.action[:60]}")

        # Execute
        ctx = await execute(
            plan_steps=pp_result.plan.steps,
            base_url=BASE_URL,
            session_token=TOKEN,
        )
        result_data["api_calls"] = len(ctx.call_log)
        result_data["api_errors"] = sum(1 for c in ctx.call_log if c["status"] >= 400)

        print(f"\n  API calls: {len(ctx.call_log)}, errors: {result_data['api_errors']}")
        for c in ctx.call_log:
            status_icon = "✓" if c["status"] < 400 else "✗"
            print(f"    {status_icon} {c['method']} {c['endpoint']} → {c['status']}")

    except Exception as e:
        result_data["error"] = str(e)
        print(f"\n  ✗ EXECUTION ERROR: {e}")

    # Verify
    try:
        verification = await case["verify"]()
        result_data["verified"] = verification.get("pass", False)
        result_data["verification"] = verification
        icon = "✓" if verification.get("pass") else "✗"
        print(f"\n  {icon} VERIFICATION: {'PASS' if verification.get('pass') else 'FAIL'}")
        if not verification.get("pass"):
            print(f"    Reason: {verification.get('reason', verification)}")
        if verification.get("entity"):
            print(f"    Entity: {json.dumps(verification['entity'], ensure_ascii=False)}")
    except Exception as e:
        result_data["verified"] = False
        result_data["verification_error"] = str(e)
        print(f"\n  ✗ VERIFICATION ERROR: {e}")

    total_ms = (time.monotonic() - start) * 1000
    result_data["total_ms"] = round(total_ms)
    print(f"\n  Total: {total_ms/1000:.1f}s")

    return result_data


async def main():
    # Parse args
    cases_to_run = list(range(len(EVAL_CASES)))
    if len(sys.argv) > 1 and sys.argv[1] == "--case":
        cases_to_run = [int(sys.argv[2])]

    results = []
    for idx in cases_to_run:
        r = await run_case(idx, EVAL_CASES[idx])
        results.append(r)

    # Summary
    print(f"\n\n{'='*70}")
    print("EVAL SUMMARY")
    print(f"{'='*70}")
    passed = sum(1 for r in results if r.get("verified"))
    total = len(results)
    print(f"\n  {passed}/{total} passed\n")

    for r in results:
        icon = "✓" if r.get("verified") else "✗"
        err_info = f" ({r['api_errors']} API errors)" if r.get("api_errors") else ""
        time_info = f" [{r['total_ms']/1000:.0f}s]"
        print(f"  {icon} {r['name']}{err_info}{time_info}")

    # Save results
    out_path = "logs/eval_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n  Results saved to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
