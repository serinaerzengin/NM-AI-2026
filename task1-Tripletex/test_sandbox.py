"""Test agent against sandbox with representative tasks from ALL 30 task types."""
import asyncio
import os
import sys
import json
import time
from dotenv import load_dotenv
load_dotenv()

from tripletex_client import TripletexClient
from file_handler import process_files
from agent import run_agent
from apply_fixes import reset_bank_account_cache

BASE_URL = os.environ["TRIPLETEX_BASE_URL"]
TOKEN = os.environ["TRIPLETEX_SESSION_TOKEN"]

# Representative tasks covering the BIGGEST scoring gaps
TESTS = [
    # Task 5: Simple employee (department.id error = 6x)
    {
        "name": "simple_employee",
        "prompt": "We have a new employee named Test Person, born 15. March 1990. Please create them as an employee with email test.person@example.org and start date 1. April 2026.",
    },
    # Task 3: Create product
    {
        "name": "create_product",
        "prompt": 'Opprett produktet "Testprodukt" med produktnummer 9999. Prisen er 5000 kr eksklusiv MVA, og MVA-sats er 25 %.',
    },
    # Task 9: Order + invoice + payment
    {
        "name": "order_invoice_payment",
        "prompt": "Erstellen Sie einen Auftrag für den Kunden Nordlicht GmbH (Org.-Nr. 985301476) mit dem Produkt Testprodukt (9999) zu 5000 NOK. Wandeln Sie den Auftrag in eine Rechnung um und registrieren Sie die vollständige Zahlung.",
    },
    # Task 22: Supplier invoice (from prompt)
    {
        "name": "supplier_invoice",
        "prompt": "We have received invoice INV-2026-TEST from the supplier Ridgepoint Ltd (org no. 946578193) for 12500 NOK including VAT. The amount is for office supplies (account 6500). Register the supplier invoice with the correct incoming VAT (25%).",
    },
    # Task 18: Payroll
    {
        "name": "payroll",
        "prompt": "Kjør lønn for Lars Berg (lars.berg@example.org) for denne måneden. Grunnlønn er 40000 kr. Legg til en engangsbonus på 10000 kr.",
    },
    # Task 25: Monthly closing
    {
        "name": "monthly_closing",
        "prompt": "Führen Sie den Monatsabschluss für März 2026 durch. Buchen Sie die Rechnungsabgrenzung (5000 NOK pro Monat von Konto 1700 auf Aufwand Konto 6300). Erfassen Sie die monatliche Abschreibung für eine Anlage mit Anschaffungskosten 120000 NOK und Nutzungsdauer 5 Jahre (lineare Abschreibung, Konto 6020 für Abschreibung, Konto 1200 als Gegenkonto).",
    },
    # Task 27: Foreign currency
    {
        "name": "foreign_currency",
        "prompt": "Vi sendte en faktura på 10000 EUR til Tindra AS (org.nr 862097653) da kursen var 10.00 NOK/EUR. Kunden har nå betalt, men kursen er 10.50 NOK/EUR. Registrer betalingen og bokfør valutagevinsten (agio) på riktig konto.",
    },
]


async def run_test(test: dict):
    reset_bank_account_cache()
    req_id = f"test_{test['name'][:6]}"
    client = TripletexClient(BASE_URL, TOKEN, req_id)

    start = time.time()
    try:
        result = await run_agent(test["prompt"], [], client, req_id)
        elapsed = time.time() - start
        calls = client.call_count
        errors = client.error_count

        status = "✅" if errors == 0 else "⚠️" if errors <= 1 else "❌"
        print(f"{status} {test['name']:<25} {elapsed:>5.1f}s  {calls:>2} calls  {errors} errors")
        return {"name": test["name"], "elapsed": elapsed, "calls": calls, "errors": errors}
    except Exception as e:
        elapsed = time.time() - start
        print(f"❌ {test['name']:<25} {elapsed:>5.1f}s  EXCEPTION: {e}")
        return {"name": test["name"], "elapsed": elapsed, "calls": 0, "errors": 99}
    finally:
        await client.close()


async def main():
    print("=" * 70)
    print("SANDBOX TEST — Testing agent against live Tripletex sandbox")
    print("=" * 70)

    # First verify sandbox is accessible
    client = TripletexClient(BASE_URL, TOKEN, "verify")
    result = await client.call("GET", "/ledger/account", params={"number": "1920"})
    await client.close()

    if result["status"] >= 400:
        print(f"❌ Sandbox not accessible: {result}")
        return
    print(f"✅ Sandbox accessible\n")

    results = []
    for test in TESTS:
        r = await run_test(test)
        results.append(r)
        print()  # Space between tests

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    total_calls = sum(r["calls"] for r in results)
    total_errors = sum(r["errors"] for r in results)
    total_time = sum(r["elapsed"] for r in results)
    print(f"Total: {len(results)} tasks, {total_calls} calls, {total_errors} errors, {total_time:.1f}s")

    for r in results:
        status = "✅" if r["errors"] == 0 else "❌"
        print(f"  {status} {r['name']:<25} {r['calls']:>2} calls  {r['errors']} errors  {r['elapsed']:.1f}s")


if __name__ == "__main__":
    asyncio.run(main())
