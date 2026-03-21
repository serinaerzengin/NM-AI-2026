"""
Local evaluation runner — tests the agent against the sandbox.

Usage:
    source .env && uv run python eval_local.py
    source .env && uv run python eval_local.py --case 0   # run a single case
    source .env && uv run python eval_local.py --tag employee  # run cases with tag
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time

import httpx

sys.path.insert(0, os.path.dirname(__file__))

from agent.logging_config import setup_logging
from agent import run

setup_logging()

BASE_URL = os.environ["TRIPLETEX_BASE_URL"]
TOKEN = os.environ["TRIPLETEX_SESSION_TOKEN"]
AUTH = ("0", TOKEN)


# ── Test cases ──────────────────────────────────────────────────────────────

EVAL_CASES = [
    # ── Task 01: Employee ──
    {
        "name": "T01: Create employee with start date",
        "tags": ["employee", "t01"],
        "prompt": "Vi har en ny ansatt som heter Lars Berg, født 15. March 1990. Opprett vedkommende som ansatt med e-post lars.berg@example.org og startdato 1. September 2026.",
        "verify": lambda: verify_employee("Lars", "Berg", "lars.berg@example.org"),
    },
    # ── Task 02: Customer with address ──
    {
        "name": "T02: Create customer with address",
        "tags": ["customer", "t02"],
        "prompt": "Crie o cliente Nordvik AS com número de organização 912345678. O endereço é Storgata 10, 0182 Oslo. E-mail: post@nordvik.no.",
        "verify": lambda: verify_customer("Nordvik"),
    },
    # ── Task 03: Supplier ──
    {
        "name": "T03: Register supplier",
        "tags": ["supplier", "t03"],
        "prompt": "Register the supplier Greenfield Ltd with organization number 987654321. Email: faktura@greenfield.no.",
        "verify": lambda: verify_supplier("Greenfield"),
    },
    # ── Task 04: Product with VAT ──
    {
        "name": "T04: Create product standard VAT",
        "tags": ["product", "t04"],
        "prompt": "Create the product \"Workshop\" with product number 5001. The price is 15000 NOK excluding VAT, using the standard 25% VAT rate.",
        "verify": lambda: verify_product("Workshop"),
    },
    # ── Task 05: Multiple departments ──
    {
        "name": "T05: Create three departments",
        "tags": ["department", "t05"],
        "prompt": "Create three departments in Tripletex: \"Salg\", \"Utvikling\", and \"Support\".",
        "verify": lambda: verify_departments(["Salg", "Utvikling", "Support"]),
    },
    # ── Task 06: Multi-line invoice with different VAT rates ──
    {
        "name": "T06: Invoice with 3 product lines, mixed VAT",
        "tags": ["invoice", "multiline", "t06"],
        "prompt": "Create an invoice for the customer Birchwood Ltd (org no. 800100200) with three product lines: Consulting (3001) at 25000 NOK with 25% VAT, Food Service (3002) at 8000 NOK with 15% VAT (food/næringsmiddel), and Textbook (3003) at 5000 NOK with 0% VAT (exempt).",
        "verify": lambda: verify_customer("Birchwood"),
    },
    # ── Task 07: Order → Invoice → Payment ──
    {
        "name": "T07: Order, invoice, and full payment",
        "tags": ["order", "payment", "t07"],
        "prompt": "Erstellen Sie einen Auftrag für den Kunden Bergmann GmbH (Org.-Nr. 800200300) mit den Produkten Beratung (4001) zu 30000 NOK und Wartung (4002) zu 15000 NOK. Wandeln Sie den Auftrag in eine Rechnung um und registrieren Sie die vollständige Zahlung.",
        "verify": lambda: verify_customer("Bergmann"),
    },
    # ── Task 09: Payment on existing invoice ──
    {
        "name": "T09: Register payment on existing invoice",
        "tags": ["payment", "t09"],
        "prompt": "Kunden TestCorp AS (org.nr 800300400) har en utestående faktura på 20000 kr eksklusiv MVA for \"Konsulenttimer\". Registrer full betaling på denne fakturaen.",
        "verify": lambda: verify_customer("TestCorp"),
    },
    # ── Task: Payment reversal ──
    {
        "name": "T09b: Reverse payment (bank return)",
        "tags": ["reversal", "t09"],
        "prompt": "Betalingen fra ReversTest AS (org.nr 800400500) for fakturaen \"Skylagring\" (10000 kr ekskl. MVA) ble returnert av banken. Reverser betalingen slik at fakturaen igjen viser utestående beløp.",
        "verify": lambda: verify_customer("ReversTest"),
    },
    # ── Task: Credit note ──
    {
        "name": "T10: Create credit note",
        "tags": ["credit", "t10"],
        "prompt": "Kunden KreditTest AS (org.nr 800500600) har reklamert på fakturaen for \"Nettverkstjeneste\" (15000 kr ekskl. MVA). Opprett en fullstendig kreditnota som reverserer hele fakturaen.",
        "verify": lambda: verify_customer("KreditTest"),
    },
    # ── Task 11: Create project ──
    {
        "name": "T11: Create project",
        "tags": ["project", "t11"],
        "prompt": "Opprett prosjektet \"Prosjekt Alpha\" knytt til kunden AlphaKunde AS (org.nr 800600700). Prosjektleiar er Ola Nordmann (ola.nordmann@example.org).",
        "verify": lambda: verify_project("Alpha"),
    },
    # ── Task 12: Project fixed price + milestone ──
    {
        "name": "T12: Fixed price project with milestone invoice",
        "tags": ["project", "fixed", "t12"],
        "prompt": "Sett fastpris 200000 kr på prosjektet \"FastPris Test\" for FastKunde AS (org.nr 800700800). Prosjektleiar er Kari Hansen (kari.hansen@example.org). Fakturer kunden for 50 % av fastprisen som ei delbetaling.",
        "verify": lambda: verify_customer("FastKunde"),
    },
    # ── Task 13: Hourly billing ──
    {
        "name": "T13: Project hourly billing",
        "tags": ["project", "hourly", "t13"],
        "prompt": "Registrer 20 timar for Test Testesen (test.testesen@example.org) på aktiviteten \"Utvikling\" i prosjektet \"TimeTest\" for TimeKunde AS (org.nr 800800900). Timesats: 1500 kr/t. Generer ein prosjektfaktura til kunden basert på dei registrerte timane.",
        "verify": lambda: verify_customer("TimeKunde"),
    },
    # ── Task: Salary/Payroll ──
    {
        "name": "T14: Run payroll",
        "tags": ["salary", "t14"],
        "prompt": "Køyr løn for Lønn Testesen (lonn.testesen@example.org) for denne månaden. Grunnløn er 45000 kr. Legg til ein eingongsbonus på 10000 kr i tillegg til grunnløna.",
        "verify": lambda: verify_employee_by_email("lonn.testesen@example.org"),
    },
    # ── Task: Travel expense ──
    {
        "name": "T15: Travel expense report",
        "tags": ["travel", "t15"],
        "prompt": "Registre una nota de gastos de viaje para Viaje Test (viaje.test@example.org) por \"Kundebesøk Oslo\". El viaje duró 3 días con dietas (tarifa diaria 800 NOK). Gastos: billete de avión 5000 NOK y taxi 500 NOK.",
        "verify": lambda: verify_employee_by_email("viaje.test@example.org"),
    },
    # ── Task: Accounting dimensions ──
    {
        "name": "T16: Accounting dimensions + voucher",
        "tags": ["dimension", "t16"],
        "prompt": "Opprett ein fri rekneskapsdimensjon \"Testregion\" med verdiane \"Nord\" og \"Sør\". Bokfør deretter eit bilag på konto 6300 for 30000 kr, knytt til dimensjonsverdien \"Nord\".",
        "verify": lambda: verify_dimension("Testregion"),
    },
    # ── Task 17: Create and send invoice ──
    {
        "name": "T17: Create and send invoice",
        "tags": ["invoice", "send", "t17"],
        "prompt": "Opprett og send ein faktura til kunden FakturaTest AS (org.nr 800900100) på 25000 kr eksklusiv MVA. Fakturaen gjeld Programvarelisens.",
        "verify": lambda: verify_customer("FakturaTest"),
    },
]


# ── Verification helpers ────────────────────────────────────────────────────

async def verify_employee(first: str, last: str, email: str) -> dict:
    async with httpx.AsyncClient() as c:
        resp = await c.get(
            f"{BASE_URL}/employee", auth=AUTH,
            params={"fields": "id,firstName,lastName,email", "count": 100},
        )
    for emp in resp.json().get("values", []):
        if emp.get("firstName") == first and emp.get("lastName") == last:
            return {"pass": True, "entity": emp}
    return {"pass": False, "reason": f"Employee {first} {last} not found"}


async def verify_employee_by_email(email: str) -> dict:
    async with httpx.AsyncClient() as c:
        resp = await c.get(
            f"{BASE_URL}/employee", auth=AUTH,
            params={"email": email, "fields": "id,firstName,lastName,email", "count": 10},
        )
    values = resp.json().get("values", [])
    if values:
        return {"pass": True, "entity": values[0]}
    return {"pass": False, "reason": f"Employee with email {email} not found"}


async def verify_customer(name_contains: str) -> dict:
    async with httpx.AsyncClient() as c:
        resp = await c.get(
            f"{BASE_URL}/customer", auth=AUTH,
            params={"fields": "id,name,email", "count": 100},
        )
    for v in resp.json().get("values", []):
        if name_contains.lower() in v.get("name", "").lower():
            return {"pass": True, "entity": v}
    return {"pass": False, "reason": f"Customer '{name_contains}' not found"}


async def verify_supplier(name_contains: str) -> dict:
    async with httpx.AsyncClient() as c:
        resp = await c.get(
            f"{BASE_URL}/supplier", auth=AUTH,
            params={"fields": "id,name,email", "count": 100},
        )
    for v in resp.json().get("values", []):
        if name_contains.lower() in v.get("name", "").lower():
            return {"pass": True, "entity": v}
    return {"pass": False, "reason": f"Supplier '{name_contains}' not found"}


async def verify_product(name_contains: str) -> dict:
    async with httpx.AsyncClient() as c:
        resp = await c.get(
            f"{BASE_URL}/product", auth=AUTH,
            params={"fields": "id,name,number", "count": 100},
        )
    for v in resp.json().get("values", []):
        if name_contains.lower() in v.get("name", "").lower():
            return {"pass": True, "entity": v}
    return {"pass": False, "reason": f"Product '{name_contains}' not found"}


async def verify_departments(names: list[str]) -> dict:
    async with httpx.AsyncClient() as c:
        resp = await c.get(
            f"{BASE_URL}/department", auth=AUTH,
            params={"fields": "id,name,departmentNumber", "count": 100},
        )
    found = []
    all_depts = resp.json().get("values", [])
    for name in names:
        match = any(name.lower() in d.get("name", "").lower() for d in all_depts)
        found.append({"name": name, "found": match})
    all_found = all(f["found"] for f in found)
    return {"pass": all_found, "details": found}


async def verify_project(name_contains: str) -> dict:
    async with httpx.AsyncClient() as c:
        resp = await c.get(
            f"{BASE_URL}/project", auth=AUTH,
            params={"fields": "id,name", "count": 100},
        )
    for v in resp.json().get("values", []):
        if name_contains.lower() in v.get("name", "").lower():
            return {"pass": True, "entity": v}
    return {"pass": False, "reason": f"Project '{name_contains}' not found"}


async def verify_dimension(name_contains: str) -> dict:
    """Check if an accounting dimension name was created."""
    async with httpx.AsyncClient() as c:
        resp = await c.get(
            f"{BASE_URL}/ledger/accountingDimensionName", auth=AUTH,
            params={"count": 50},
        )
    for v in resp.json().get("values", []):
        dim_name = v.get("dimensionName", "") or v.get("name", "")
        if name_contains.lower() in dim_name.lower():
            return {"pass": True, "entity": v}
    return {"pass": False, "reason": f"Dimension '{name_contains}' not found"}


# ── Runner ──────────────────────────────────────────────────────────────────

async def run_case(idx: int, case: dict) -> dict:
    name = case["name"]
    prompt = case["prompt"]
    print(f"\n{'=' * 70}")
    print(f"EVAL {idx}: {name}")
    print(f"PROMPT: {prompt[:100]}...")
    print(f"{'=' * 70}")

    start = time.monotonic()
    result_data = {"name": name, "prompt": prompt}

    try:
        await run(
            prompt=prompt,
            base_url=BASE_URL,
            session_token=TOKEN,
        )
        result_data["executed"] = True
    except Exception as e:
        result_data["error"] = str(e)
        print(f"\n  EXECUTION ERROR: {e}")

    # Verify
    try:
        verification = await case["verify"]()
        result_data["verified"] = verification.get("pass", False)
        result_data["verification"] = verification
        icon = "PASS" if verification.get("pass") else "FAIL"
        print(f"\n  VERIFICATION: {icon}")
        if not verification.get("pass"):
            print(f"    Reason: {verification.get('reason', verification)}")
        if verification.get("entity"):
            print(f"    Entity: {json.dumps(verification['entity'], ensure_ascii=False)}")
        if verification.get("details"):
            for d in verification["details"]:
                print(f"    {d['name']}: {'found' if d['found'] else 'MISSING'}")
    except Exception as e:
        result_data["verified"] = False
        result_data["verification_error"] = str(e)
        print(f"\n  VERIFICATION ERROR: {e}")

    total_ms = (time.monotonic() - start) * 1000
    result_data["total_ms"] = round(total_ms)
    print(f"\n  Total: {total_ms / 1000:.1f}s")

    return result_data


async def main():
    cases_to_run = list(range(len(EVAL_CASES)))

    # Parse args
    if len(sys.argv) > 1:
        if sys.argv[1] == "--case":
            cases_to_run = [int(sys.argv[2])]
        elif sys.argv[1] == "--tag":
            tag = sys.argv[2].lower()
            cases_to_run = [i for i, c in enumerate(EVAL_CASES) if tag in [t.lower() for t in c.get("tags", [])]]

    results = []
    for idx in cases_to_run:
        r = await run_case(idx, EVAL_CASES[idx])
        results.append(r)

    # Summary
    print(f"\n\n{'=' * 70}")
    print("EVAL SUMMARY")
    print(f"{'=' * 70}")
    passed = sum(1 for r in results if r.get("verified"))
    print(f"\n  {passed}/{len(results)} passed\n")

    for r in results:
        icon = "PASS" if r.get("verified") else "FAIL"
        time_info = f" [{r['total_ms'] / 1000:.0f}s]"
        print(f"  {icon} {r['name']}{time_info}")

    out_path = "logs/eval_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n  Results saved to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
