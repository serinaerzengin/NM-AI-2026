"""
Comprehensive test suite for the Tripletex AI Accounting Agent.
Tests all 30 competition task types + specific bug fixes.

Usage:
    uv run python test_comprehensive.py              # Run all tests
    uv run python test_comprehensive.py --unit-only  # Run only unit tests (no API)
    uv run python test_comprehensive.py --skip-slow  # Skip tests that tend to be slow
    uv run python test_comprehensive.py --test 5     # Run only test #5
"""

import asyncio
import base64
import csv
import io
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import date, timedelta

from dotenv import load_dotenv

load_dotenv()

# Add project to path
sys.path.insert(0, os.path.dirname(__file__))

from tripletex_client import TripletexClient, ProxyTokenExpiredError
from file_handler import process_files
from apply_fixes import apply_fixes, reset_bank_account_cache
from agent import run_agent, _slim_values, _SLIM_FIELDS


# ============================================================
# Test infrastructure
# ============================================================

TODAY = date.today().isoformat()
TOMORROW = (date.today() + timedelta(days=1)).isoformat()
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()
LAST_MONTH = (date.today().replace(day=1) - timedelta(days=1)).isoformat()


@dataclass
class TestResult:
    name: str
    task_type: str
    passed: bool = False
    skipped: bool = False
    skip_reason: str = ""
    elapsed: float = 0.0
    api_calls: int = 0
    errors: int = 0
    error_msg: str = ""


class TestRunner:
    def __init__(self):
        self.results: list[TestResult] = []
        self.base_url = os.environ.get("TRIPLETEX_BASE_URL", "")
        self.session_token = os.environ.get("TRIPLETEX_SESSION_TOKEN", "")
        self.token_expired = False
        # Shared entity IDs populated during setup
        self.shared = {
            "department_id": None,
            "customer_id": None,
            "supplier_id": None,
            "employee_id": None,
            "product_id": None,
            "product_number": None,
            "account_1920_id": None,
            "voucher_type_id": None,
            "company_id": None,
        }

    def new_client(self, req_id: str = "test") -> TripletexClient:
        return TripletexClient(self.base_url, self.session_token, req_id)

    async def run_test(self, name: str, task_type: str, coro, timeout: float = 120.0):
        """Run a single test with timeout and error handling."""
        result = TestResult(name=name, task_type=task_type)

        if self.token_expired:
            result.skipped = True
            result.skip_reason = "Token expired"
            self.results.append(result)
            return result

        print(f"\n{'='*60}")
        print(f"  TEST: {name}")
        print(f"  Type: {task_type}")
        print(f"{'='*60}")

        start = time.time()
        try:
            await asyncio.wait_for(coro(result), timeout=timeout)
            result.elapsed = time.time() - start
            if not result.skipped:
                result.passed = True
                print(f"  PASS ({result.elapsed:.1f}s, {result.api_calls} calls, {result.errors} errors)")
        except asyncio.TimeoutError:
            result.elapsed = time.time() - start
            result.error_msg = f"Timeout after {timeout}s"
            print(f"  TIMEOUT after {result.elapsed:.1f}s")
        except ProxyTokenExpiredError:
            result.elapsed = time.time() - start
            result.error_msg = "Proxy token expired"
            self.token_expired = True
            print(f"  TOKEN EXPIRED - aborting remaining tests")
        except Exception as e:
            result.elapsed = time.time() - start
            result.error_msg = str(e)[:200]
            print(f"  FAIL: {e}")

        self.results.append(result)
        return result

    async def run_agent_test(self, prompt: str, file_contents: list = None,
                              req_id: str = "test") -> dict:
        """Run the agent and return result dict. Resets bank account cache."""
        reset_bank_account_cache()
        client = self.new_client(req_id)
        try:
            result = await run_agent(prompt, file_contents or [], client, req_id)
            result["client"] = client
            return result
        except Exception as e:
            await client.close()
            raise

    def print_summary(self):
        """Print final pass/fail summary."""
        print(f"\n\n{'='*80}")
        print(f"  COMPREHENSIVE TEST SUMMARY")
        print(f"{'='*80}")
        print(f"{'#':<4} {'Test Name':<50} {'Type':<12} {'Status':<8} {'Time':>6} {'Calls':>5} {'Errs':>4}")
        print(f"{'-'*4} {'-'*50} {'-'*12} {'-'*8} {'-'*6} {'-'*5} {'-'*4}")

        passed = 0
        failed = 0
        skipped = 0
        total_time = 0.0
        total_calls = 0

        for i, r in enumerate(self.results, 1):
            if r.skipped:
                status = "SKIP"
                skipped += 1
            elif r.passed:
                status = "PASS"
                passed += 1
            else:
                status = "FAIL"
                failed += 1

            total_time += r.elapsed
            total_calls += r.api_calls

            time_str = f"{r.elapsed:.1f}s" if r.elapsed else "-"
            calls_str = str(r.api_calls) if r.api_calls else "-"
            errs_str = str(r.errors) if r.errors else "-"

            print(f"{i:<4} {r.name:<50} {r.task_type:<12} {status:<8} {time_str:>6} {calls_str:>5} {errs_str:>4}")
            if r.error_msg and not r.passed:
                print(f"     -> {r.error_msg[:70]}")

        print(f"{'-'*4} {'-'*50} {'-'*12} {'-'*8} {'-'*6} {'-'*5} {'-'*4}")
        print(f"{'':4} {'TOTAL':<50} {'':12} {'':8} {total_time:>5.0f}s {total_calls:>5}")
        print()
        print(f"  PASSED:  {passed}")
        print(f"  FAILED:  {failed}")
        print(f"  SKIPPED: {skipped}")
        print(f"  TOTAL:   {len(self.results)}")
        print(f"  TIME:    {total_time:.0f}s")
        print(f"{'='*80}")

        return failed == 0


# ============================================================
# Helper: make CSV file content for agent
# ============================================================

def make_csv_file_content(rows: list[list[str]], filename: str = "data.csv",
                           delimiter: str = ";") -> list:
    """Create a base64-encoded CSV file payload like the competition sends."""
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=delimiter)
    for row in rows:
        writer.writerow(row)
    csv_bytes = buf.getvalue().encode("utf-8")
    b64 = base64.b64encode(csv_bytes).decode()
    return [{"filename": filename, "content_base64": b64, "mime_type": "text/csv"}]


async def process_file_for_agent(files: list) -> list:
    """Process files through file_handler, same as api.py does."""
    return await process_files(files)


# ============================================================
# SETUP: Create shared entities
# ============================================================

async def setup_shared_data(runner: TestRunner):
    """Create entities needed by multiple tests. Uses raw API calls (no LLM)."""
    print("\n" + "="*60)
    print("  SETUP: Creating shared entities")
    print("="*60)

    client = runner.new_client("setup")
    try:
        # 1. Get or create department
        r = await client.call("GET", "/department", params={"count": "1"})
        vals = r.get("data", {}).get("values", [])
        if vals:
            runner.shared["department_id"] = vals[0]["id"]
            print(f"  Department: {vals[0]['id']} (existing)")
        else:
            r = await client.call("POST", "/department",
                                   json_data={"name": "Testadm", "departmentNumber": "99"})
            if r["status"] < 400:
                runner.shared["department_id"] = r["data"]["value"]["id"]
                print(f"  Department: {runner.shared['department_id']} (created)")

        # 2. Get or create customer
        r = await client.call("GET", "/customer", params={"name": "TestKunde AS", "count": "1"})
        vals = r.get("data", {}).get("values", [])
        if vals:
            runner.shared["customer_id"] = vals[0]["id"]
            print(f"  Customer: {vals[0]['id']} (existing)")
        else:
            r = await client.call("POST", "/customer",
                                   json_data={"name": "TestKunde AS", "isCustomer": True,
                                              "email": "test@testkunde.no"})
            if r["status"] < 400:
                runner.shared["customer_id"] = r["data"]["value"]["id"]
                print(f"  Customer: {runner.shared['customer_id']} (created)")
            else:
                # May already exist with slightly different name
                r = await client.call("GET", "/customer", params={"count": "1"})
                vals = r.get("data", {}).get("values", [])
                if vals:
                    runner.shared["customer_id"] = vals[0]["id"]
                    print(f"  Customer: {vals[0]['id']} (fallback existing)")

        # 3. Get or create supplier
        r = await client.call("GET", "/supplier", params={"name": "TestLeverandor AS", "count": "1"})
        vals = r.get("data", {}).get("values", [])
        if vals:
            runner.shared["supplier_id"] = vals[0]["id"]
            print(f"  Supplier: {vals[0]['id']} (existing)")
        else:
            r = await client.call("POST", "/supplier",
                                   json_data={"name": "TestLeverandor AS", "isSupplier": True,
                                              "email": "test@testlev.no"})
            if r["status"] < 400:
                runner.shared["supplier_id"] = r["data"]["value"]["id"]
                print(f"  Supplier: {runner.shared['supplier_id']} (created)")
            else:
                r = await client.call("GET", "/supplier", params={"count": "1"})
                vals = r.get("data", {}).get("values", [])
                if vals:
                    runner.shared["supplier_id"] = vals[0]["id"]
                    print(f"  Supplier: {vals[0]['id']} (fallback existing)")

        # 4. Get or create employee
        r = await client.call("GET", "/employee", params={"count": "1"})
        vals = r.get("data", {}).get("values", [])
        if vals:
            runner.shared["employee_id"] = vals[0]["id"]
            runner.shared["company_id"] = vals[0].get("companyId")
            print(f"  Employee: {vals[0]['id']} (existing, companyId={runner.shared['company_id']})")
        else:
            dept_id = runner.shared["department_id"]
            r = await client.call("POST", "/employee",
                                   json_data={"firstName": "Test", "lastName": "Bruker",
                                              "email": "test.bruker@example.org",
                                              "dateOfBirth": "1990-01-15",
                                              "userType": "EXTENDED",
                                              "department": {"id": dept_id} if dept_id else None})
            if r["status"] < 400:
                runner.shared["employee_id"] = r["data"]["value"]["id"]
                runner.shared["company_id"] = r["data"]["value"].get("companyId")
                print(f"  Employee: {runner.shared['employee_id']} (created)")

        # 5. Get or create product
        r = await client.call("GET", "/product", params={"number": "TEST001", "count": "1"})
        vals = r.get("data", {}).get("values", [])
        if vals:
            runner.shared["product_id"] = vals[0]["id"]
            runner.shared["product_number"] = "TEST001"
            print(f"  Product: {vals[0]['id']} (existing)")
        else:
            r = await client.call("POST", "/product",
                                   json_data={"name": "Testprodukt", "number": "TEST001",
                                              "priceExcludingVatCurrency": 1000.0,
                                              "priceIncludingVatCurrency": 1250.0,
                                              "vatType": {"id": 3}})
            if r["status"] < 400:
                runner.shared["product_id"] = r["data"]["value"]["id"]
                runner.shared["product_number"] = "TEST001"
                print(f"  Product: {runner.shared['product_id']} (created)")
            else:
                # Fallback: get any product
                r = await client.call("GET", "/product", params={"count": "1"})
                vals = r.get("data", {}).get("values", [])
                if vals:
                    runner.shared["product_id"] = vals[0]["id"]
                    runner.shared["product_number"] = vals[0].get("number", "1")
                    print(f"  Product: {vals[0]['id']} (fallback existing)")

        # 6. Get account 1920 and voucher type
        r = await client.call("GET", "/ledger/account", params={"number": "1920"})
        vals = r.get("data", {}).get("values", [])
        if vals:
            runner.shared["account_1920_id"] = vals[0]["id"]

        r = await client.call("GET", "/ledger/voucherType", params={"count": "1"})
        vals = r.get("data", {}).get("values", [])
        if vals:
            runner.shared["voucher_type_id"] = vals[0]["id"]

        print(f"\n  Shared data: {json.dumps({k: v for k, v in runner.shared.items() if v is not None}, indent=2)}")

    except ProxyTokenExpiredError:
        runner.token_expired = True
        print("  TOKEN EXPIRED during setup - cannot continue")
    except Exception as e:
        print(f"  Setup error: {e}")
    finally:
        await client.close()


# ============================================================
# UNIT TESTS (no LLM, no API)
# ============================================================

async def test_csv_semicolon_parsing(result: TestResult):
    """Bug fix: CSV with semicolons must be parsed into proper columns."""
    # Create a semicolon-delimited CSV (standard in Norway)
    csv_data = "Dato;Beskrivelse;Inn;Ut\n2026-01-15;Betaling fra Kunde AS;5000;\n2026-01-16;Bankgebyr;;150\n"
    b64 = base64.b64encode(csv_data.encode()).decode()

    files = [{"filename": "kontoutskrift.csv", "content_base64": b64, "mime_type": "text/csv"}]
    parts = await process_files(files)

    assert parts, "No content parts returned from CSV"
    text = parts[0]["text"]

    # Verify columns are separated (pipe-delimited in output)
    assert "Dato" in text, "Header 'Dato' not found"
    assert "Beskrivelse" in text, "Header 'Beskrivelse' not found"

    # Key check: "Betaling fra Kunde AS" should be ONE column, not split
    lines = text.strip().split("\n")
    data_line = [l for l in lines if "Betaling fra Kunde AS" in l]
    assert data_line, "Data row with 'Betaling fra Kunde AS' not found"

    # The line should have exactly 4 pipe-separated columns
    cols = data_line[0].split("|")
    cols = [c.strip() for c in cols]
    assert len(cols) == 4, f"Expected 4 columns, got {len(cols)}: {cols}"
    assert cols[0] == "2026-01-15", f"Date column wrong: {cols[0]}"
    assert "Betaling fra Kunde AS" in cols[1], f"Description column wrong: {cols[1]}"
    assert cols[2].strip() == "5000", f"Inn column wrong: {cols[2]}"

    print(f"    CSV parsed correctly: {len(lines)-1} data rows, 4 columns each")
    result.passed = True


async def test_supplier_invoice_slimming(result: TestResult):
    """Bug fix: /supplierInvoice must NOT be caught by /supplier slim pattern."""
    # The _SLIM_FIELDS list has /supplierInvoice BEFORE /supplier
    # Verify that a supplierInvoice path uses supplierInvoice fields, not supplier fields

    supplier_invoice_data = [
        {"id": 1, "invoiceNumber": "INV-001", "amount": 5000, "amountOutstanding": 5000,
         "invoiceDate": "2026-01-01", "supplier": {"id": 10, "name": "Test"},
         "name": "should be stripped", "organizationNumber": "should be stripped"}
    ]

    slimmed = _slim_values(supplier_invoice_data, "/supplierInvoice")
    item = slimmed[0]

    # supplierInvoice fields should be kept
    assert "invoiceNumber" in item, "invoiceNumber missing from supplierInvoice slim"
    assert "amount" in item, "amount missing from supplierInvoice slim"
    assert "supplier" in item, "supplier missing from supplierInvoice slim"

    # supplier-only fields should NOT be present (they aren't in supplierInvoice slim fields)
    # The key test: organizationNumber and isSupplier are supplier fields, not supplierInvoice
    assert "organizationNumber" not in item, "organizationNumber leaked from supplier pattern"
    assert "name" not in item, "'name' should not be in supplierInvoice slim (it's a supplier field)"

    # Now verify /supplier path still works correctly
    supplier_data = [
        {"id": 10, "name": "Test Supplier", "organizationNumber": "123456789",
         "email": "test@test.no", "isSupplier": True, "phoneNumber": "12345"}
    ]
    slimmed_supplier = _slim_values(supplier_data, "/supplier")
    s = slimmed_supplier[0]
    assert "name" in s, "name missing from supplier slim"
    assert "organizationNumber" in s, "orgNumber missing from supplier slim"
    assert "phoneNumber" not in s, "phoneNumber should be stripped from supplier"

    print("    /supplierInvoice correctly uses own fields, not /supplier fields")
    result.passed = True


async def test_write_lock_serialization(result: TestResult):
    """Bug fix: parallel writes must be serialized via write_lock to avoid 409s."""
    import asyncio
    from agent import TaskContext, RunLogger

    # Create a mock context with a write lock
    client_mock = type("MockClient", (), {
        "call_count": 0, "error_count": 0,
        "call": lambda self, *a, **kw: asyncio.coroutine(lambda: {"status": 200, "data": {}})()
    })()

    logger = RunLogger("test")
    logger.start_time = time.time()
    ctx = TaskContext(client=client_mock, req_id="test", start_time=time.time(), logger=logger)

    # Track execution order
    order = []
    original_lock = ctx.write_lock

    async def simulated_write(n: int):
        async with original_lock:
            order.append(f"start_{n}")
            await asyncio.sleep(0.05)  # Simulate API call
            order.append(f"end_{n}")

    # Launch 3 "parallel" writes
    await asyncio.gather(
        simulated_write(1),
        simulated_write(2),
        simulated_write(3),
    )

    # Verify serialization: each start_N must be followed by end_N before next start
    for i in range(0, len(order), 2):
        assert order[i].startswith("start_"), f"Expected start at {i}, got {order[i]}"
        assert order[i+1].startswith("end_"), f"Expected end at {i+1}, got {order[i+1]}"
        start_n = order[i].split("_")[1]
        end_n = order[i+1].split("_")[1]
        assert start_n == end_n, f"Interleaved execution: {order}"

    print(f"    Write lock serialized correctly: {order}")
    result.passed = True


async def test_apply_fixes_auto_retries(result: TestResult):
    """Bug fix: apply_fixes correctly transforms payloads for common error scenarios."""

    # Test 1: Department injection field name (apply_fixes doesn't do this, agent.py does,
    # but we test the voucher fixes)
    voucher_payload = {
        "description": "Test",
        "date": "2026-01-01",
        "postings": [
            {"account": {"id": 1}, "amount": 1000},
            {"account": {"id": 2}, "amount": -1000},
        ]
    }
    fixed = apply_fixes("/ledger/voucher", "POST", voucher_payload)
    # Check: amount -> amountGross, rows assigned
    assert fixed["postings"][0]["amountGross"] == 1000, "amount not converted to amountGross"
    assert fixed["postings"][0]["row"] == 1, "row not set"
    assert fixed["postings"][1]["row"] == 2, "row not set"
    assert "amount" not in fixed["postings"][0], "amount field not removed"

    # Test 2: vatType stripped from balance sheet accounts
    account_payload = {"number": 1920, "name": "Bank", "vatType": {"id": 3}}
    fixed = apply_fixes("/ledger/account", "POST", account_payload)
    assert "vatType" not in fixed, "vatType not stripped from BS account 1920"

    # Test 3: vatType kept on P&L accounts
    account_payload2 = {"number": 3000, "name": "Salg", "vatType": {"id": 3}}
    fixed2 = apply_fixes("/ledger/account", "POST", account_payload2)
    assert "vatType" in fixed2, "vatType incorrectly stripped from P&L account 3000"

    # Test 4: Employee fixes
    emp_payload = {"firstName": "Test", "lastName": "User",
                   "nationalIdentityNumber": "invalid123"}
    fixed = apply_fixes("/employee", "POST", emp_payload)
    assert "nationalIdentityNumber" not in fixed, "Invalid NIN not stripped"
    assert fixed["userType"] == "EXTENDED", "userType not defaulted"

    # Test 5: Order fixes - vatType stripped from orderLines
    order_payload = {
        "customer": {"id": 1},
        "orderLines": [{"product": {"id": 1}, "count": 1, "vatType": {"id": 3}}]
    }
    fixed = apply_fixes("/order", "POST", order_payload)
    assert "vatType" not in fixed["orderLines"][0], "vatType not stripped from orderLine"
    assert "deliveryDate" in fixed, "deliveryDate not defaulted on order"

    # Test 6: Supplier fixes - bankAccountNumber stripped
    sup_payload = {"name": "Test", "bankAccountNumber": "12345678903"}
    fixed = apply_fixes("/supplier", "POST", sup_payload)
    assert "bankAccountNumber" not in fixed, "bankAccountNumber not stripped from supplier"

    # Test 7: Salary transaction fixes
    salary_payload = {
        "employee": {"id": 1},
        "payslips": [{"specifications": [{"amount": 50000, "count": 1}]}]
    }
    fixed = apply_fixes("/salary/transaction", "POST", salary_payload)
    assert "employee" not in fixed, "employee not moved from root to payslip"
    assert fixed["payslips"][0].get("employee", {}).get("id") == 1, "employee not injected into payslip"
    assert fixed["payslips"][0]["specifications"][0].get("rate") == 50000, "amount not converted to rate"

    # Test 8: Project fixes - budget fields stripped
    proj_payload = {"name": "Test", "budget": 100000, "fixedPrice": 50000,
                    "projectManager": {"id": 1}}
    fixed = apply_fixes("/project", "POST", proj_payload)
    assert "budget" not in fixed, "budget not stripped from project"
    assert "fixedPrice" not in fixed, "fixedPrice not stripped from project"
    assert "startDate" in fixed, "startDate not defaulted"

    # Test 9: supplierInvoice fixes - dueDate stripped
    si_payload = {"invoiceNumber": "1", "dueDate": "2026-02-01",
                  "supplier": {"id": 1},
                  "voucher": {"dueDate": "2026-02-01", "postings": [
                      {"account": {"id": 1}, "amountGross": -5000, "amountGrossCurrency": -5000}
                  ]}}
    fixed = apply_fixes("/supplierInvoice", "POST", si_payload)
    assert "dueDate" not in fixed, "dueDate not stripped from supplierInvoice"
    assert "dueDate" not in fixed["voucher"], "dueDate not stripped from voucher"
    # supplier auto-injected into negative posting
    assert fixed["voucher"]["postings"][0].get("supplier") == {"id": 1}, \
        "supplier not auto-injected into leverandorgjeld posting"

    # Test 10: Dimension fixes
    dim_payload = {"name": "Prosjekttype"}
    fixed = apply_fixes("/ledger/accountingDimensionName", "POST", dim_payload)
    assert fixed.get("dimensionName") == "Prosjekttype", "name not converted to dimensionName"
    assert "name" not in fixed, "name field not removed"

    dimval_payload = {"name": "Intern", "dimensionIndex": 1}
    fixed = apply_fixes("/ledger/accountingDimensionValue", "POST", dimval_payload)
    assert fixed.get("displayName") == "Intern", "name not converted to displayName"

    print("    All apply_fixes transformations verified (10 sub-tests)")
    result.passed = True


# ============================================================
# AGENT TESTS (use LLM + real API)
# ============================================================

async def test_create_customer(runner: TestRunner, result: TestResult):
    """Task type: Create customer."""
    ts = int(time.time()) % 10000
    r = await runner.run_agent_test(
        f"Opprett en ny kunde med navn 'Testkunde {ts} AS', e-post 'kunde{ts}@test.no' og organisasjonsnummer '999{ts:04d}000'.",
        req_id=f"t_cust_{ts}"
    )
    result.api_calls = r.get("api_calls", 0)
    result.errors = r.get("errors", 0)
    client = r.get("client")
    if client:
        await client.close()
    result.passed = True


async def test_create_supplier(runner: TestRunner, result: TestResult):
    """Task type: Create supplier."""
    ts = int(time.time()) % 10000
    r = await runner.run_agent_test(
        f"Erstelle einen neuen Lieferanten mit dem Namen 'Lieferant {ts} GmbH', "
        f"E-Mail 'lieferant{ts}@test.de'.",
        req_id=f"t_sup_{ts}"
    )
    result.api_calls = r.get("api_calls", 0)
    result.errors = r.get("errors", 0)
    client = r.get("client")
    if client:
        await client.close()
    result.passed = True


async def test_create_employee_simple(runner: TestRunner, result: TestResult):
    """Task type: Create employee (simple, no PDF)."""
    ts = int(time.time()) % 10000
    r = await runner.run_agent_test(
        f"Create a new employee: first name 'Jane', last name 'Doe{ts}', "
        f"email 'jane.doe{ts}@example.org', date of birth 1995-03-20.",
        req_id=f"t_emp_{ts}"
    )
    result.api_calls = r.get("api_calls", 0)
    result.errors = r.get("errors", 0)
    client = r.get("client")
    if client:
        await client.close()
    result.passed = True


async def test_create_product(runner: TestRunner, result: TestResult):
    """Task type: Create product."""
    ts = int(time.time()) % 10000
    r = await runner.run_agent_test(
        f"Crea un nuevo producto con nombre 'Producto Test {ts}', numero '{ts}', "
        f"precio sin IVA 500 NOK, IVA 25%.",
        req_id=f"t_prod_{ts}"
    )
    result.api_calls = r.get("api_calls", 0)
    result.errors = r.get("errors", 0)
    client = r.get("client")
    if client:
        await client.close()
    result.passed = True


async def test_create_department(runner: TestRunner, result: TestResult):
    """Task type: Create department."""
    ts = int(time.time()) % 10000
    r = await runner.run_agent_test(
        f"Créer un nouveau département nommé 'Département {ts}' avec le numéro {ts}.",
        req_id=f"t_dept_{ts}"
    )
    result.api_calls = r.get("api_calls", 0)
    result.errors = r.get("errors", 0)
    client = r.get("client")
    if client:
        await client.close()
    result.passed = True


async def test_create_invoice(runner: TestRunner, result: TestResult):
    """Task type: Create order and invoice it."""
    cust_id = runner.shared.get("customer_id")
    prod_id = runner.shared.get("product_id")
    if not cust_id or not prod_id:
        result.skipped = True
        result.skip_reason = "Missing customer or product"
        return

    r = await runner.run_agent_test(
        f"Opprett en ordre for kunde med ID {cust_id} med produkt ID {prod_id} "
        f"(antall 2). Fakturer ordren med fakturadato {TODAY}.",
        req_id="t_inv"
    )
    result.api_calls = r.get("api_calls", 0)
    result.errors = r.get("errors", 0)
    client = r.get("client")
    if client:
        await client.close()
    result.passed = True


async def test_register_payment(runner: TestRunner, result: TestResult):
    """Task type: Register payment on invoice."""
    r = await runner.run_agent_test(
        f"Find the most recent invoice and register a full payment on it "
        f"with payment date {TODAY}.",
        req_id="t_pay"
    )
    result.api_calls = r.get("api_calls", 0)
    result.errors = r.get("errors", 0)
    client = r.get("client")
    if client:
        await client.close()
    result.passed = True


async def test_create_credit_note(runner: TestRunner, result: TestResult):
    """Task type: Create credit note."""
    r = await runner.run_agent_test(
        f"Finn den nyeste fakturaen og opprett en kreditnota med dato {TODAY}.",
        req_id="t_credit"
    )
    result.api_calls = r.get("api_calls", 0)
    result.errors = r.get("errors", 0)
    client = r.get("client")
    if client:
        await client.close()
    result.passed = True


async def test_create_supplier_invoice(runner: TestRunner, result: TestResult):
    """Task type: Create supplier invoice (leverandorfaktura)."""
    sup_id = runner.shared.get("supplier_id")
    if not sup_id:
        result.skipped = True
        result.skip_reason = "Missing supplier"
        return

    r = await runner.run_agent_test(
        f"Registrer en leverandorfaktura fra leverandor ID {sup_id}. "
        f"Fakturanummer 'LF-9001', fakturadato {YESTERDAY}, "
        f"totalbelop inkl. mva 12500 NOK. Bokfor pa konto 6300 (Leie lokaler).",
        req_id="t_sinv"
    )
    result.api_calls = r.get("api_calls", 0)
    result.errors = r.get("errors", 0)
    client = r.get("client")
    if client:
        await client.close()
    result.passed = True


async def test_create_voucher(runner: TestRunner, result: TestResult):
    """Task type: Create manual journal voucher."""
    r = await runner.run_agent_test(
        f"Crie um lançamento contábil manual (bilag): débito conta 6500 (Material de escritório) "
        f"1000 NOK, crédito conta 1920 (Banco) 1000 NOK. Data: {TODAY}. "
        f"Descrição: 'Compra de material de escritório'.",
        req_id="t_vouch"
    )
    result.api_calls = r.get("api_calls", 0)
    result.errors = r.get("errors", 0)
    client = r.get("client")
    if client:
        await client.close()
    result.passed = True


async def test_create_project(runner: TestRunner, result: TestResult):
    """Task type: Create project."""
    emp_id = runner.shared.get("employee_id")
    if not emp_id:
        result.skipped = True
        result.skip_reason = "Missing employee"
        return

    ts = int(time.time()) % 10000
    r = await runner.run_agent_test(
        f"Crea un progetto chiamato 'Progetto Alpha {ts}' con project manager "
        f"employee ID {emp_id}. Data di inizio: {TODAY}.",
        req_id=f"t_proj_{ts}"
    )
    result.api_calls = r.get("api_calls", 0)
    result.errors = r.get("errors", 0)
    client = r.get("client")
    if client:
        await client.close()
    result.passed = True


async def test_project_with_activities(runner: TestRunner, result: TestResult):
    """Task type: Create project with activities."""
    emp_id = runner.shared.get("employee_id")
    if not emp_id:
        result.skipped = True
        result.skip_reason = "Missing employee"
        return

    ts = int(time.time()) % 10000
    r = await runner.run_agent_test(
        f"Opprett et prosjekt 'Prosjekt Beta {ts}' med prosjektleder ansatt-ID {emp_id}. "
        f"Legg til to aktiviteter: 'Design' og 'Utvikling'. Startdato: {TODAY}.",
        req_id=f"t_projact_{ts}"
    )
    result.api_calls = r.get("api_calls", 0)
    result.errors = r.get("errors", 0)
    client = r.get("client")
    if client:
        await client.close()
    result.passed = True


async def test_create_travel_expense(runner: TestRunner, result: TestResult):
    """Task type: Create travel expense."""
    emp_id = runner.shared.get("employee_id")
    if not emp_id:
        result.skipped = True
        result.skip_reason = "Missing employee"
        return

    r = await runner.run_agent_test(
        f"Opprett en reiseregning for ansatt ID {emp_id}. "
        f"Tittel: 'Tjenestereise Oslo-Bergen'. "
        f"Avreise: {TODAY}, retur: {TOMORROW}. Destinasjon: Bergen. "
        f"Innenlands reise, ikke dagstur.",
        req_id="t_travel"
    )
    result.api_calls = r.get("api_calls", 0)
    result.errors = r.get("errors", 0)
    client = r.get("client")
    if client:
        await client.close()
    result.passed = True


async def test_travel_expense_with_costs(runner: TestRunner, result: TestResult):
    """Task type: Travel expense with cost items."""
    emp_id = runner.shared.get("employee_id")
    if not emp_id:
        result.skipped = True
        result.skip_reason = "Missing employee"
        return

    r = await runner.run_agent_test(
        f"Create a travel expense for employee ID {emp_id}. "
        f"Title: 'Conference Trip'. Departure: {TODAY}, return: {TOMORROW}. "
        f"Destination: Stavanger. Domestic trip. "
        f"Costs: Flight 2500 NOK, Taxi 350 NOK.",
        req_id="t_trcost"
    )
    result.api_calls = r.get("api_calls", 0)
    result.errors = r.get("errors", 0)
    client = r.get("client")
    if client:
        await client.close()
    result.passed = True


async def test_travel_expense_per_diem(runner: TestRunner, result: TestResult):
    """Task type: Travel expense with per diem compensation."""
    emp_id = runner.shared.get("employee_id")
    if not emp_id:
        result.skipped = True
        result.skip_reason = "Missing employee"
        return

    r = await runner.run_agent_test(
        f"Registrer reiseregning for ansatt ID {emp_id}. "
        f"Tittel: 'Kurs Trondheim'. Avreise: {TODAY}, retur: {TOMORROW}. "
        f"Destinasjon: Trondheim. Innenlands. "
        f"Diett: 2 dager a 800 NOK. Ingen overnatting.",
        req_id="t_perdiem"
    )
    result.api_calls = r.get("api_calls", 0)
    result.errors = r.get("errors", 0)
    client = r.get("client")
    if client:
        await client.close()
    result.passed = True


async def test_salary_transaction(runner: TestRunner, result: TestResult):
    """Task type: Create salary transaction."""
    emp_id = runner.shared.get("employee_id")
    if not emp_id:
        result.skipped = True
        result.skip_reason = "Missing employee"
        return

    month = date.today().month
    year = date.today().year
    r = await runner.run_agent_test(
        f"Registrer lonn for ansatt ID {emp_id} for {year}-{month:02d}. "
        f"Fastlonn 45000 NOK.",
        req_id="t_salary"
    )
    result.api_calls = r.get("api_calls", 0)
    result.errors = r.get("errors", 0)
    client = r.get("client")
    if client:
        await client.close()
    result.passed = True


async def test_monthly_closing_accrual(runner: TestRunner, result: TestResult):
    """Task type: Monthly closing - accrual reversal."""
    r = await runner.run_agent_test(
        f"Bokfor manedsslutt for mars 2026: Reverser forskuddsbetalt forsikring. "
        f"Forskuddsbetalt belop var 60000 NOK for 12 maneder (konto 1700). "
        f"Bokfor manedlig andel pa konto 6300 (leie/forsikring). "
        f"Dato: 2026-03-31.",
        req_id="t_accrual"
    )
    result.api_calls = r.get("api_calls", 0)
    result.errors = r.get("errors", 0)
    client = r.get("client")
    if client:
        await client.close()
    result.passed = True


async def test_monthly_closing_depreciation(runner: TestRunner, result: TestResult):
    """Task type: Monthly closing - depreciation."""
    r = await runner.run_agent_test(
        f"Buchung monatliche Abschreibung: Maschine Anschaffungskosten 240.000 NOK, "
        f"Nutzungsdauer 5 Jahre. Konto Abschreibung: 6015, Konto Gegenwert: 1200. "
        f"Datum: 2026-03-31.",
        req_id="t_depr"
    )
    result.api_calls = r.get("api_calls", 0)
    result.errors = r.get("errors", 0)
    client = r.get("client")
    if client:
        await client.close()
    result.passed = True


async def test_monthly_closing_salary_accrual(runner: TestRunner, result: TestResult):
    """Task type: Monthly closing - salary accrual."""
    r = await runner.run_agent_test(
        f"Bokfor manedsslutt mars 2026: Palopt lonn. "
        f"Lonnskostnad for mars er 85000 NOK. "
        f"Debet konto 5000 (Lonn), kredit konto 2900 (Palopte kostnader). "
        f"Dato: 2026-03-31.",
        req_id="t_salaccrual"
    )
    result.api_calls = r.get("api_calls", 0)
    result.errors = r.get("errors", 0)
    client = r.get("client")
    if client:
        await client.close()
    result.passed = True


async def test_bank_reconciliation_csv(runner: TestRunner, result: TestResult):
    """Task type: Bank reconciliation from CSV."""
    cust_id = runner.shared.get("customer_id")
    if not cust_id:
        result.skipped = True
        result.skip_reason = "Missing customer"
        return

    # Create a simple bank statement CSV
    csv_rows = [
        ["Dato", "Beskrivelse", "Inn", "Ut"],
        ["2026-03-15", "Bankgebyr", "", "250"],
    ]
    files_raw = make_csv_file_content(csv_rows, "kontoutskrift.csv", ";")
    file_contents = await process_file_for_agent(files_raw)

    r = await runner.run_agent_test(
        f"Avstem denne kontoutskriften mot bank (konto 1920). "
        f"Bokfor alle transaksjoner.",
        file_contents=file_contents,
        req_id="t_bankrec"
    )
    result.api_calls = r.get("api_calls", 0)
    result.errors = r.get("errors", 0)
    client = r.get("client")
    if client:
        await client.close()
    result.passed = True


async def test_ledger_correction(runner: TestRunner, result: TestResult):
    """Task type: Ledger error correction."""
    r = await runner.run_agent_test(
        f"Sjekk hovedboken for mars 2026 (perioden 2026-03-01 til 2026-03-31). "
        f"Finn eventuelle feilposteringer pa konto 6500 (kontorkostnader) og korriger dem. "
        f"Hvis det finnes poster som skulle vart pa konto 7300 (markedsforing), "
        f"lag en korreksjonsbilag.",
        req_id="t_ledger"
    )
    result.api_calls = r.get("api_calls", 0)
    result.errors = r.get("errors", 0)
    client = r.get("client")
    if client:
        await client.close()
    result.passed = True


async def test_overdue_invoice_reminder(runner: TestRunner, result: TestResult):
    """Task type: Overdue invoice + reminder fee + partial payment."""
    r = await runner.run_agent_test(
        f"En faktura er forfalt. Registrer en delbetaling pa 5000 NOK med dato {TODAY}. "
        f"Opprett et purregebyr pa 700 NOK. Send den nye purrefakturaen pa e-post.",
        req_id="t_overdue"
    )
    result.api_calls = r.get("api_calls", 0)
    result.errors = r.get("errors", 0)
    client = r.get("client")
    if client:
        await client.close()
    result.passed = True


async def test_foreign_currency_payment(runner: TestRunner, result: TestResult):
    """Task type: Foreign currency payment (agio/disagio)."""
    r = await runner.run_agent_test(
        f"Register payment for an invoice. The invoice was 1000 EUR at rate 11.20 NOK/EUR. "
        f"The payment is at rate 11.50 NOK/EUR. Payment date: {TODAY}. "
        f"Book the exchange rate difference (agio).",
        req_id="t_forex"
    )
    result.api_calls = r.get("api_calls", 0)
    result.errors = r.get("errors", 0)
    client = r.get("client")
    if client:
        await client.close()
    result.passed = True


async def test_create_dimension(runner: TestRunner, result: TestResult):
    """Task type: Create accounting dimension."""
    ts = int(time.time()) % 10000
    r = await runner.run_agent_test(
        f"Opprett en ny regnskapsdimensjon kalt 'Kostnadssted{ts}' "
        f"med verdiene 'Oslo' og 'Bergen'.",
        req_id=f"t_dim_{ts}"
    )
    result.api_calls = r.get("api_calls", 0)
    result.errors = r.get("errors", 0)
    client = r.get("client")
    if client:
        await client.close()
    result.passed = True


async def test_batch_products(runner: TestRunner, result: TestResult):
    """Task type: Create multiple products (batch)."""
    ts = int(time.time()) % 10000
    r = await runner.run_agent_test(
        f"Opprett tre produkter:\n"
        f"1. 'Konsulenttime' nummer 'KT{ts}', pris eks. mva 1200 NOK, 25% mva\n"
        f"2. 'Reisekostnad' nummer 'RK{ts}', pris eks. mva 500 NOK, 0% mva\n"
        f"3. 'Programvare' nummer 'PV{ts}', pris eks. mva 3000 NOK, 25% mva",
        req_id=f"t_bprod_{ts}"
    )
    result.api_calls = r.get("api_calls", 0)
    result.errors = r.get("errors", 0)
    client = r.get("client")
    if client:
        await client.close()
    result.passed = True


async def test_batch_departments(runner: TestRunner, result: TestResult):
    """Task type: Create multiple departments (batch)."""
    ts = int(time.time()) % 10000
    r = await runner.run_agent_test(
        f"Create three departments:\n"
        f"1. 'Sales{ts}' number {ts+1}\n"
        f"2. 'Engineering{ts}' number {ts+2}\n"
        f"3. 'Marketing{ts}' number {ts+3}",
        req_id=f"t_bdept_{ts}"
    )
    result.api_calls = r.get("api_calls", 0)
    result.errors = r.get("errors", 0)
    client = r.get("client")
    if client:
        await client.close()
    result.passed = True


async def test_balance_sheet_query(runner: TestRunner, result: TestResult):
    """Task type: Balance sheet query."""
    r = await runner.run_agent_test(
        f"Hent balansen for perioden 2026-01-01 til 2026-03-31. "
        f"Vis saldoen for konto 1920 (Bank).",
        req_id="t_balance"
    )
    result.api_calls = r.get("api_calls", 0)
    result.errors = r.get("errors", 0)
    client = r.get("client")
    if client:
        await client.close()
    result.passed = True


async def test_send_invoice_email(runner: TestRunner, result: TestResult):
    """Task type: Send invoice by email."""
    r = await runner.run_agent_test(
        f"Finn den nyeste fakturaen og send den pa e-post.",
        req_id="t_email"
    )
    result.api_calls = r.get("api_calls", 0)
    result.errors = r.get("errors", 0)
    client = r.get("client")
    if client:
        await client.close()
    result.passed = True


async def test_project_hours_invoice(runner: TestRunner, result: TestResult):
    """Task type: Project hours + invoice workflow."""
    emp_id = runner.shared.get("employee_id")
    cust_id = runner.shared.get("customer_id")
    if not emp_id or not cust_id:
        result.skipped = True
        result.skip_reason = "Missing employee or customer"
        return

    ts = int(time.time()) % 10000
    r = await runner.run_agent_test(
        f"Opprett prosjekt 'Kundeprosjekt {ts}' med prosjektleder ansatt-ID {emp_id}. "
        f"Legg til aktivitet 'Konsulentarbeid'. "
        f"Registrer 10 timer pa aktiviteten i dag. "
        f"Opprett et produkt 'Timer {ts}' (nummer 'TIM{ts}', pris 1200 NOK eks. mva, 25% mva). "
        f"Opprett en ordre for kunde ID {cust_id} med dette produktet (10 stk) "
        f"og knytt til prosjektet. Fakturer ordren.",
        req_id=f"t_projinv_{ts}"
    )
    result.api_calls = r.get("api_calls", 0)
    result.errors = r.get("errors", 0)
    client = r.get("client")
    if client:
        await client.close()
    result.passed = True


async def test_create_order(runner: TestRunner, result: TestResult):
    """Task type: Create order."""
    cust_id = runner.shared.get("customer_id")
    prod_id = runner.shared.get("product_id")
    if not cust_id or not prod_id:
        result.skipped = True
        result.skip_reason = "Missing customer or product"
        return

    r = await runner.run_agent_test(
        f"Opprett en ordre for kunde ID {cust_id} med produkt ID {prod_id}, antall 3. "
        f"Ordredato: {TODAY}.",
        req_id="t_order"
    )
    result.api_calls = r.get("api_calls", 0)
    result.errors = r.get("errors", 0)
    client = r.get("client")
    if client:
        await client.close()
    result.passed = True


async def test_receipt_expense_posting(runner: TestRunner, result: TestResult):
    """Task type: Receipt/kvittering expense posting (simulated — no real PDF)."""
    # We simulate what a receipt prompt looks like
    r = await runner.run_agent_test(
        f"Bokfor en kvittering: USB-mus kjopt for 299 NOK inkl. mva (25%) pa konto 6860 "
        f"(Kontorrekvisita). Betalt fra konto 1920 (Bank). "
        f"Dato: {TODAY}. Avdeling: bruk den forste avdelingen som finnes.",
        req_id="t_receipt"
    )
    result.api_calls = r.get("api_calls", 0)
    result.errors = r.get("errors", 0)
    client = r.get("client")
    if client:
        await client.close()
    result.passed = True


# ============================================================
# MAIN
# ============================================================

async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--unit-only", action="store_true", help="Run only unit tests")
    parser.add_argument("--skip-slow", action="store_true", help="Skip slow multi-step tests")
    parser.add_argument("--test", type=int, default=0, help="Run only test #N")
    args = parser.parse_args()

    runner = TestRunner()

    if not runner.base_url or not runner.session_token:
        print("ERROR: TRIPLETEX_BASE_URL and TRIPLETEX_SESSION_TOKEN must be set in .env")
        sys.exit(1)

    print(f"Tripletex base URL: {runner.base_url}")
    print(f"Today: {TODAY}")
    print(f"Token: {runner.session_token[:20]}...")

    # === UNIT TESTS (no API, no LLM) ===
    unit_tests = [
        ("CSV semicolon parsing", "unit", test_csv_semicolon_parsing),
        ("SupplierInvoice vs Supplier slimming", "unit", test_supplier_invoice_slimming),
        ("Write lock serialization", "unit", test_write_lock_serialization),
        ("apply_fixes auto-retry transforms", "unit", test_apply_fixes_auto_retries),
    ]

    # === AGENT TESTS (LLM + API) ===
    agent_tests = [
        ("Create customer", "customer", lambda r: test_create_customer(runner, r)),
        ("Create supplier", "supplier", lambda r: test_create_supplier(runner, r)),
        ("Create employee (simple)", "employee", lambda r: test_create_employee_simple(runner, r)),
        ("Create product", "product", lambda r: test_create_product(runner, r)),
        ("Create department", "department", lambda r: test_create_department(runner, r)),
        ("Create order", "order", lambda r: test_create_order(runner, r)),
        ("Create invoice (order->invoice)", "invoice", lambda r: test_create_invoice(runner, r)),
        ("Register payment", "payment", lambda r: test_register_payment(runner, r)),
        ("Create credit note", "creditnote", lambda r: test_create_credit_note(runner, r)),
        ("Send invoice email", "email", lambda r: test_send_invoice_email(runner, r)),
        ("Create supplier invoice", "sup_invoice", lambda r: test_create_supplier_invoice(runner, r)),
        ("Create voucher", "voucher", lambda r: test_create_voucher(runner, r)),
        ("Create project", "project", lambda r: test_create_project(runner, r)),
        ("Project with activities", "proj_act", lambda r: test_project_with_activities(runner, r)),
        ("Create travel expense", "travel", lambda r: test_create_travel_expense(runner, r)),
        ("Travel expense + costs", "travel_cost", lambda r: test_travel_expense_with_costs(runner, r)),
        ("Travel expense + per diem", "perdiem", lambda r: test_travel_expense_per_diem(runner, r)),
        ("Salary transaction", "salary", lambda r: test_salary_transaction(runner, r)),
        ("Monthly closing: accrual", "closing", lambda r: test_monthly_closing_accrual(runner, r)),
        ("Monthly closing: depreciation", "closing", lambda r: test_monthly_closing_depreciation(runner, r)),
        ("Monthly closing: salary accrual", "closing", lambda r: test_monthly_closing_salary_accrual(runner, r)),
        ("Bank reconciliation (CSV)", "bankrec", lambda r: test_bank_reconciliation_csv(runner, r)),
        ("Ledger error correction", "ledger_fix", lambda r: test_ledger_correction(runner, r)),
        ("Overdue invoice + reminder", "overdue", lambda r: test_overdue_invoice_reminder(runner, r)),
        ("Foreign currency payment", "forex", lambda r: test_foreign_currency_payment(runner, r)),
        ("Create accounting dimension", "dimension", lambda r: test_create_dimension(runner, r)),
        ("Batch: multiple products", "batch", lambda r: test_batch_products(runner, r)),
        ("Batch: multiple departments", "batch", lambda r: test_batch_departments(runner, r)),
        ("Balance sheet query", "query", lambda r: test_balance_sheet_query(runner, r)),
        ("Receipt expense posting", "receipt", lambda r: test_receipt_expense_posting(runner, r)),
        ("Project hours + invoice", "proj_inv", lambda r: test_project_hours_invoice(runner, r)),
    ]

    # Determine which tests to run
    all_tests = []
    for i, (name, ttype, fn) in enumerate(unit_tests, 1):
        all_tests.append((i, name, ttype, fn, False))  # False = not slow
    for i, (name, ttype, fn) in enumerate(agent_tests, len(unit_tests) + 1):
        is_slow = ttype in ("proj_inv", "bankrec", "overdue", "forex", "travel_cost", "perdiem")
        all_tests.append((i, name, ttype, fn, is_slow))

    # Run unit tests
    print(f"\n{'#'*60}")
    print(f"  UNIT TESTS ({len(unit_tests)} tests)")
    print(f"{'#'*60}")

    for idx, name, ttype, fn, _ in all_tests:
        if ttype != "unit":
            continue
        if args.test and args.test != idx:
            continue
        await runner.run_test(name, ttype, fn, timeout=10.0)

    if args.unit_only:
        runner.print_summary()
        return

    # Setup shared data
    await setup_shared_data(runner)

    if runner.token_expired:
        print("\nToken expired during setup. Skipping all agent tests.")
        runner.print_summary()
        return

    # Run agent tests
    print(f"\n{'#'*60}")
    print(f"  AGENT TESTS ({len(agent_tests)} tests)")
    print(f"{'#'*60}")

    for idx, name, ttype, fn, is_slow in all_tests:
        if ttype == "unit":
            continue
        if args.test and args.test != idx:
            continue
        if args.skip_slow and is_slow:
            result = TestResult(name=name, task_type=ttype, skipped=True,
                                skip_reason="Skipped (--skip-slow)")
            runner.results.append(result)
            print(f"\n  SKIP: {name} (--skip-slow)")
            continue

        await runner.run_test(name, ttype, fn, timeout=120.0)

        if runner.token_expired:
            print("\nToken expired. Skipping remaining tests.")
            break

    success = runner.print_summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
