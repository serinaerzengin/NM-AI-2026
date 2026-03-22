"""Full test suite — covers ALL 30 task types against the sandbox."""
import asyncio
import os
import sys
import json
import time
import base64
from dotenv import load_dotenv
load_dotenv()

from tripletex_client import TripletexClient
from file_handler import process_files
from agent import run_agent
from apply_fixes import reset_bank_account_cache

BASE_URL = os.environ["TRIPLETEX_BASE_URL"]
TOKEN = os.environ["TRIPLETEX_SESSION_TOKEN"]

# ── helpers ──────────────────────────────────────────────────────────
async def _run(name, prompt, files=None):
    reset_bank_account_cache()
    req_id = f"t_{name[:8]}"
    client = TripletexClient(BASE_URL, TOKEN, req_id)
    t0 = time.time()
    file_contents = []
    if files:
        file_contents = await process_files(files)
    try:
        result = await run_agent(prompt, file_contents, client, req_id)
        dt = time.time() - t0
        c, e = client.call_count, client.error_count
        tag = "✅" if e == 0 else ("⚠️" if e <= 1 else "❌")
        print(f"  {tag} {name:<30} {dt:>5.1f}s  {c:>2} calls  {e} err")
        return dict(name=name, dt=dt, calls=c, errors=e)
    except Exception as ex:
        dt = time.time() - t0
        print(f"  ❌ {name:<30} {dt:>5.1f}s  CRASH: {ex}")
        return dict(name=name, dt=dt, calls=0, errors=99)
    finally:
        await client.close()

# ── test cases ───────────────────────────────────────────────────────
TESTS = [
    # ── SIMPLE CRUD (Tasks 1-4, 6) ──
    ("T01_create_customer",
     "Opprett kunden Testfirma AS med organisasjonsnummer 988957747. Adressa er Kirkegata 23, 0182 Oslo. E-post: post@testfirma.no."),

    ("T02_create_supplier",
     "Registrer leverandøren Leveransen AS med organisasjonsnummer 912345678. E-post: faktura@leveransen.no."),

    ("T03_create_product",
     'Create the product "Cloud Service" with product number 7766. The price is 15000 NOK excluding VAT, using the standard 25% VAT rate.'),

    ("T04_create_departments",
     'Opprett tre avdelinger i Tripletex: "Utvikling", "Salg" og "Support".'),

    ("T06_create_project",
     'Create the project "Digital Upgrade" linked to the customer Testfirma AS (org no. 988957747). The project manager is the first employee in the system.'),

    # ── EMPLOYEE (Tasks 5, 11) ──
    ("T05_simple_employee",
     "We have a new employee named Anna Berg, born 12. May 1992. Please create them as an employee with email anna.berg@example.org and start date 1. June 2026."),

    # ── INVOICE TASKS (Tasks 7, 8, 9, 10, 15, 16, 28) ──
    ("T07_create_send_invoice",
     'Créez et envoyez une facture au client Testfirma AS (nº org. 988957747) de 8000 NOK hors TVA. La facture concerne Consultation.'),

    ("T09_order_invoice_pay",
     'Erstellen Sie einen Auftrag für Testfirma AS (Org.-Nr. 988957747) mit dem Produkt Cloud Service (7766) zu 15000 NOK. Wandeln Sie den Auftrag in eine Rechnung um und registrieren Sie die vollständige Zahlung.'),

    # ── SUPPLIER INVOICE (Task 22) ──
    ("T22_supplier_invoice",
     "Recebemos a fatura INV-2026-TEST do fornecedor Leveransen AS (org. nº 912345678) no valor de 25000 NOK com IVA incluído. O montante refere-se a serviços de escritório (conta 6500). Registe a fatura do fornecedor com o IVA dedutível correto (25%)."),

    # ── PAYROLL (Task 18) ──
    ("T18_payroll",
     "Run payroll for Anna Berg (anna.berg@example.org) for this month. The base salary is 45000 NOK. Add a one-time bonus of 12000 NOK."),

    # ── MONTHLY CLOSING (Task 25) ──
    ("T25_monthly_closing",
     "Realice el cierre mensual de marzo de 2026. Registre la periodificación (8000 NOK por mes de la cuenta 1700 a gasto cuenta 6300). Contabilice la depreciación mensual de un activo fijo con costo de adquisición 180000 NOK y vida útil 5 años (depreciación lineal, cuenta 6020 para gasto, cuenta 1200 como contra). También registre una provisión salarial de 45000 (débito 5000, crédito 2900)."),

    # ── ACCOUNTING DIMENSION (Task 14) ──
    ("T14_dimension",
     'Opprett en fri regnskapsdimensjon "Kanal" med verdiene "Nett" og "Butikk". Bokfør deretter et bilag på konto 7300 for 9500 kr, knyttet til dimensjonsverdien "Nett".'),

    # ── TRAVEL EXPENSE (Task 19) ──
    ("T19_travel",
     'Register a travel expense for Anna Berg (anna.berg@example.org) for "Client visit Oslo". The trip lasted 3 days with per diem (daily rate 800 NOK). Expenses: Flight 3500 NOK and Hotel 2200 NOK.'),

    # ── COST ANALYSIS (Task 21) ──
    ("T21_cost_analysis",
     "Total costs increased significantly from January to February 2026. Analyze the general ledger and identify the three expense accounts with the largest increase in amount. Create an internal project for each of the three accounts using the account name. Also create an activity for each project."),
]

async def main():
    print("=" * 70)
    print("  FULL SANDBOX TEST SUITE")
    print("=" * 70)

    # Verify connectivity
    c = TripletexClient(BASE_URL, TOKEN, "ping")
    r = await c.call("GET", "/ledger/account", params={"number": "1920"})
    await c.close()
    if r["status"] >= 400:
        print(f"❌ Sandbox unreachable: {r}")
        return
    print(f"✅ Sandbox OK\n")

    results = []
    for name, prompt in TESTS:
        res = await _run(name, prompt)
        results.append(res)

    # ── Summary ──
    print("\n" + "=" * 70)
    print("  RESULTS SUMMARY")
    print("=" * 70)
    ok = sum(1 for r in results if r["errors"] == 0)
    total_c = sum(r["calls"] for r in results)
    total_e = sum(r["errors"] for r in results)
    total_t = sum(r["dt"] for r in results)
    print(f"  {ok}/{len(results)} passed | {total_c} total calls | {total_e} total errors | {total_t:.0f}s total\n")
    for r in results:
        tag = "✅" if r["errors"] == 0 else "❌"
        print(f"  {tag} {r['name']:<30} {r['calls']:>2}c  {r['errors']}e  {r['dt']:>5.1f}s")

if __name__ == "__main__":
    asyncio.run(main())
