import sys
from datetime import date


def _valid_norwegian_nin(nin: str) -> bool:
    """Validate Norwegian fødselsnummer (11-digit NIN with checksums)."""
    nin = ''.join(c for c in nin if c.isdigit())
    if len(nin) != 11:
        return False
    d = [int(c) for c in nin]
    # Check digit 1
    w1 = [3, 7, 6, 1, 8, 9, 4, 5, 2]
    r1 = 11 - (sum(a * b for a, b in zip(w1, d[:9])) % 11)
    k1 = 0 if r1 == 11 else r1
    if k1 == 10 or k1 != d[9]:
        return False
    # Check digit 2
    w2 = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    r2 = 11 - (sum(a * b for a, b in zip(w2, d[:10])) % 11)
    k2 = 0 if r2 == 11 else r2
    if k2 == 10 or k2 != d[10]:
        return False
    return True


# Bank account setup state
_bank_account_registered = False


def _strip_vattype_from_bs_accounts(payload):
    """Strip vatType from balance sheet / financial account creation.
    These accounts (1xxx, 2xxx, 8xxx) should not have vatType locked on creation."""
    items = payload if isinstance(payload, list) else [payload]
    for item in items:
        if not isinstance(item, dict):
            continue
        num = item.get("number")
        if num is not None:
            num_str = str(num)
            if num_str and num_str[0] in ("1", "2", "8"):
                item.pop("vatType", None)


def apply_fixes(path: str, method: str, payload):
    today = date.today().isoformat()

    # Handle list payloads (e.g. /ledger/account/list)
    if isinstance(payload, list):
        if "/ledger/account" in path and method == "POST":
            _strip_vattype_from_bs_accounts(payload)
        return payload

    if payload is None or not isinstance(payload, dict):
        return payload

    # === VOUCHER FIXES ===
    if "/voucher" in path and isinstance(payload.get("postings"), list):
        payload.setdefault("description", "Bilag")
        payload.setdefault("date", today)
        for i, p in enumerate(payload["postings"]):
            p["row"] = i + 1
            amt = p.get("amountGross")
            if amt is None:
                amt = p.get("amount")
            if amt is None:
                amt = p.get("amountGrossCurrency")
            if amt is not None:
                p["amountGross"] = amt
                p.setdefault("amountGrossCurrency", amt)
                p.pop("amount", None)
            # Fix dimension field names → freeAccountingDimension1/2
            for wrong in ("dimension1", "accountingDimension1", "customDimension1"):
                if wrong in p and "freeAccountingDimension1" not in p:
                    p["freeAccountingDimension1"] = p.pop(wrong)
            for wrong in ("dimension2", "accountingDimension2", "customDimension2"):
                if wrong in p and "freeAccountingDimension2" not in p:
                    p["freeAccountingDimension2"] = p.pop(wrong)

    # === ORDER FIXES ===
    if "/order" in path and method == "POST":
        payload.setdefault("deliveryDate", payload.get("orderDate", today))
        payload.setdefault("orderDate", today)
        for line in payload.get("orderLines", []):
            line.pop("vatType", None)
            line.pop("deliveryDate", None)  # doesn't exist on orderline
            # Relocate project from orderLine to order body (doesn't exist on orderline)
            line_project = line.pop("project", None)
            if line_project and "project" not in payload:
                payload["project"] = line_project

    # === PRODUCT FIXES ===
    if "/product" in path and method == "POST":
        price_ex = payload.get("priceExcludingVatCurrency")
        vat_id = None
        vt = payload.get("vatType")
        if isinstance(vt, dict):
            vat_id = vt.get("id")
        if price_ex is not None and "priceIncludingVatCurrency" not in payload:
            rates = {3: 0.25, 31: 0.15, 32: 0.12, 5: 0.0, 6: 0.0, 1: 0.25, 11: 0.15}
            if vat_id is not None and vat_id in rates:
                rate = rates[vat_id]
                payload["priceIncludingVatCurrency"] = round(price_ex * (1 + rate), 2)

    # === SALARY FIXES ===
    if "/salary/transaction" in path:
        payload.setdefault("date", today)
        payload.setdefault("year", int(today[:4]))
        payload.setdefault("month", int(today[5:7]))

        # Fix: employee belongs on payslip, not transaction root
        root_employee = payload.pop("employee", None)

        for ps in payload.get("payslips", []):
            if root_employee and "employee" not in ps:
                ps["employee"] = root_employee
            ps.setdefault("date", payload["date"])
            ps.setdefault("year", payload["year"])
            ps.setdefault("month", payload["month"])
            for spec in ps.get("specifications", []):
                if "rate" not in spec and "amount" in spec:
                    spec["rate"] = spec.pop("amount")
                spec.setdefault("count", 1)

    # === ACTIVITY FIXES ===
    if "/activity" in path and method == "POST":
        if payload.get("activityType") == "PROJECT_SPECIFIC":
            payload["activityType"] = "PROJECT_SPECIFIC_ACTIVITY"
        if "/project/projectActivity" in path:
            payload.setdefault("activityType", "PROJECT_SPECIFIC_ACTIVITY")
        else:
            payload.setdefault("activityType", "PROJECT_GENERAL_ACTIVITY")

    # === ACCOUNT FIXES ===
    if "/ledger/account" in path and method == "POST":
        _strip_vattype_from_bs_accounts(payload)

    # === PROJECT FIXES ===
    if path.rstrip("/") == "/project" and method in ("POST", "PUT"):
        for bad in ("budget", "fixedPrice", "budgetAmount", "budgetIncome", "fixedprice", "isFixedPrice"):
            payload.pop(bad, None)
        if method == "POST":
            payload.setdefault("startDate", today)

    # === EMPLOYEE FIXES ===
    if path.rstrip("/") == "/employee" and method == "POST":
        payload.setdefault("userType", "EXTENDED")
        # Validate Norwegian NIN (fødselsnummer) — strip invalid ones to avoid 422
        nin = payload.get("nationalIdentityNumber")
        if nin is not None and not _valid_norwegian_nin(str(nin)):
            payload.pop("nationalIdentityNumber")
        for emp in payload.get("employments", []):
            emp.setdefault("isMainEmployer", True)
            emp.setdefault("startDate", today)

    # === EMPLOYMENT DETAILS FIXES ===
    # Only add enum defaults when LLM is doing a full employment setup (has salary or percentage)
    if "/employee/employment/details" in path and method == "POST":
        if payload.get("annualSalary") or payload.get("percentageOfFullTimeEquivalent"):
            payload.setdefault("employmentType", "ORDINARY")
            payload.setdefault("employmentForm", "PERMANENT")
            payload.setdefault("remunerationType", "MONTHLY_WAGE")
            payload.setdefault("workingHoursScheme", "NOT_SHIFT")
        # occupationCode is allowed — the GET endpoint works in competition

    # === SUPPLIER FIXES ===
    if path.rstrip("/") == "/supplier" and method == "POST":
        payload.pop("bankAccountNumber", None)  # doesn't exist on supplier object

    # === SUPPLIER INVOICE FIXES ===
    if "/supplierInvoice" in path and method == "POST":
        payload.pop("dueDate", None)  # dueDate doesn't exist on supplierInvoice
        voucher = payload.get("voucher")
        if isinstance(voucher, dict):
            voucher.pop("dueDate", None)
            # Auto-inject supplier on leverandørgjeld (2400) postings — "Leverandør mangler"
            supplier_ref = payload.get("supplier")
            if supplier_ref and isinstance(voucher.get("postings"), list):
                for posting in voucher["postings"]:
                    if isinstance(posting, dict) and "supplier" not in posting:
                        # Negative amountGross = credit side = leverandørgjeld
                        amt = posting.get("amountGross", 0)
                        if amt is not None and amt < 0:
                            posting["supplier"] = supplier_ref

    # === TRAVEL EXPENSE COST FIXES ===
    if "/travelExpense/cost" in path and method == "POST":
        # amountCurrencyIncVat is the correct field, not amount
        amt = payload.pop("amount", None)
        if amt is not None and "amountCurrencyIncVat" not in payload:
            payload["amountCurrencyIncVat"] = amt
        # description field does NOT exist on cost objects — strip to avoid 422
        payload.pop("description", None)
        payload.pop("name", None)

    # === TRAVEL EXPENSE PER DIEM FIXES ===
    if "/travelExpense/perDiemCompensation" in path and method == "POST":
        payload.setdefault("location", "DOMESTIC")

    # === ACCOUNTING DIMENSION FIXES ===
    if "/accountingDimensionName" in path and method == "POST":
        if "name" in payload and "dimensionName" not in payload:
            payload["dimensionName"] = payload.pop("name")
    if "/accountingDimensionValue" in path and method == "POST":
        if "name" in payload and "displayName" not in payload:
            payload["displayName"] = payload.pop("name")
        # LLM sometimes sends accountingDimensionName instead of dimensionIndex
        payload.pop("accountingDimensionName", None)

    return payload


async def ensure_bank_account(client):
    global _bank_account_registered
    if _bank_account_registered:
        return
    try:
        result = await client.call("GET", "/ledger/account", params={"number": "1920"})
        values = result.get("data", {}).get("values", [])
        if values:
            account = values[0]
            acc_id = account.get("id")
            if acc_id and not account.get("bankAccountNumber"):
                # Send minimal payload — full object has read-only fields that may cause 422
                minimal = {"id": acc_id, "number": account.get("number", 1920), "name": account.get("name", "Bank"), "bankAccountNumber": "12345678903"}
                put_result = await client.call("PUT", f"/ledger/account/{acc_id}", json_data=minimal)
                if put_result["status"] < 400:
                    print("[SETUP] Bank account registered on 1920", file=sys.stderr)
                    _bank_account_registered = True
                else:
                    print(f"[SETUP] Bank account PUT failed: {put_result['status']}", file=sys.stderr)
            else:
                # Already has bank account number
                _bank_account_registered = True
        else:
            print("[SETUP] Account 1920 not found", file=sys.stderr)
    except Exception as e:
        print(f"[SETUP ERROR] Bank account: {e}", file=sys.stderr)
        raise  # Re-raise so ProxyTokenExpiredError propagates


async def auto_onboard_employee(client, employee_id: int, company_id: int, start_date: str = None, logger=None):
    """Automatically execute post-employee-creation steps: entitlement + employment.
    Called after POST /employee succeeds. The LLM still handles department and employment/details."""
    log = logger.log if logger else lambda msg: print(f"[ONBOARD] {msg}", file=sys.stderr)

    # Step 1: Grant ALL_PRIVILEGES via the BETA endpoint (confirmed working on competition sandboxes)
    try:
        ent_result = await client.call(
            "PUT",
            "/employee/entitlement/:grantEntitlementsByTemplate",
            params={"employeeId": employee_id, "template": "ALL_PRIVILEGES"},
        )
        if ent_result["status"] < 400:
            log(f"  AUTO: ALL_PRIVILEGES granted for employee {employee_id}")
        elif ent_result["status"] == 403:
            # Fallback: if BETA is blocked, use POST /employee/entitlement for ROLE_ADMINISTRATOR only
            log(f"  AUTO: BETA 403, falling back to POST /employee/entitlement")
            await client.call("POST", "/employee/entitlement", json_data={
                "employee": {"id": employee_id},
                "customer": {"id": company_id},
                "entitlementId": 1,
            })
        else:
            log(f"  AUTO: entitlement failed ({ent_result['status']})")
    except Exception as e:
        log(f"  AUTO: entitlement error: {e}")

    # Employment creation removed — the LLM handles this since it knows the correct
    # startDate from the prompt/PDF. Auto-creating with TODAY caused 409 conflicts.


async def create_employment(client, employee_id: int, start_date: str | None = None):
    # Ensure employee has dateOfBirth (required for employment)
    try:
        emp_result = await client.call("GET", f"/employee/{employee_id}")
        emp_data = emp_result.get("data", {}).get("value", {})
        if emp_data and not emp_data.get("dateOfBirth"):
            emp_data["dateOfBirth"] = "1990-01-01"
            await client.call("PUT", f"/employee/{employee_id}", json_data=emp_data)
            print(f"[SETUP] Set dateOfBirth on employee {employee_id}", file=sys.stderr)
    except Exception as e:
        print(f"[SETUP] dateOfBirth check failed: {e}", file=sys.stderr)

    # First check if a division exists, create one if needed
    division_id = await _ensure_division(client)

    effective_date = start_date or date.today().isoformat()
    payload = {
        "employee": {"id": employee_id},
        "startDate": effective_date,
        "isMainEmployer": True,
        "employmentDetails": [
            {
                "date": effective_date,
                "employmentType": "ORDINARY",
                "employmentForm": "PERMANENT",
                "remunerationType": "MONTHLY_WAGE",
                "workingHoursScheme": "NOT_SHIFT",
            }
        ],
    }
    if division_id:
        payload["division"] = {"id": division_id}

    result = await client.call("POST", "/employee/employment", json_data=payload)

    # If overlapping periods, try to update existing employment with division
    if result["status"] == 422:
        error_msg = str(result.get("data", "")).lower()
        if "overlappende" in error_msg and division_id:
            # Get existing employments and link division
            emp_result = await client.call("GET", "/employee/employment", params={"employeeId": str(employee_id)})
            emp_values = emp_result.get("data", {}).get("values", [])
            for emp in emp_values:
                emp_id = emp.get("id")
                if emp_id:
                    emp["division"] = {"id": division_id}
                    update_result = await client.call("PUT", f"/employee/employment/{emp_id}", json_data=emp)
                    if update_result["status"] < 400:
                        print(f"[SETUP] Linked division to existing employment {emp_id}", file=sys.stderr)
                        return update_result
            # Retry original
            result = await client.call("POST", "/employee/employment", json_data=payload)

    print(f"[SETUP] Employment creation: {result['status']}", file=sys.stderr)
    return result


_division_id_cache = None


async def _ensure_division(client):
    global _division_id_cache
    if _division_id_cache:
        return _division_id_cache
    try:
        result = await client.call("GET", "/division", params={"count": "1"})
        values = result.get("data", {}).get("values", [])
        if values:
            _division_id_cache = values[0].get("id")
            return _division_id_cache
        # Create a division (requires organizationNumber, municipality, municipalityDate)
        create_result = await client.call("POST", "/division", json_data={
            "name": "Hovedkontor",
            "startDate": "2020-01-01",
            "organizationNumber": "987654321",
            "municipalityDate": "2020-01-01",
            "municipality": {"id": 301},
        })
        if create_result["status"] < 400:
            _division_id_cache = create_result.get("data", {}).get("value", {}).get("id")
            print(f"[SETUP] Created division: {_division_id_cache}", file=sys.stderr)
            return _division_id_cache
    except Exception as e:
        print(f"[SETUP ERROR] Division: {e}", file=sys.stderr)
    return None


def reset_bank_account_cache():
    global _bank_account_registered, _division_id_cache
    _bank_account_registered = False
    _division_id_cache = None
