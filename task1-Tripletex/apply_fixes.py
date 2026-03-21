import sys
from datetime import date

TODAY = date.today().isoformat()

# Bank account setup state
_bank_account_registered = False


def apply_fixes(path: str, method: str, payload: dict) -> dict:
    if payload is None:
        return payload

    # === VOUCHER FIXES ===
    if "/voucher" in path and isinstance(payload.get("postings"), list):
        payload.setdefault("description", "Bilag")
        payload.setdefault("date", TODAY)
        for i, p in enumerate(payload["postings"]):
            p["row"] = i + 1
            amt = p.get("amountGross") or p.get("amount") or p.get("amountGrossCurrency")
            if amt is not None:
                p["amountGross"] = amt
                p["amountGrossCurrency"] = amt
                p.pop("amount", None)

    # === ORDER FIXES ===
    if "/order" in path and method == "POST":
        payload.setdefault("deliveryDate", payload.get("orderDate", TODAY))
        payload.setdefault("orderDate", TODAY)
        for line in payload.get("orderLines", []):
            line.pop("vatType", None)

    # === PRODUCT FIXES ===
    if "/product" in path and method == "POST":
        price_ex = payload.get("priceExcludingVatCurrency")
        vat_id = None
        vt = payload.get("vatType")
        if isinstance(vt, dict):
            vat_id = vt.get("id")
        if price_ex is not None and "priceIncludingVatCurrency" not in payload:
            rates = {3: 0.25, 31: 0.15, 32: 0.12, 5: 0.0, 6: 0.0}
            rate = rates.get(vat_id, 0.25)
            payload["priceIncludingVatCurrency"] = round(price_ex * (1 + rate), 2)

    # === SALARY FIXES ===
    if "/salary/transaction" in path:
        payload.setdefault("date", TODAY)
        payload.setdefault("year", int(TODAY[:4]))
        payload.setdefault("month", int(TODAY[5:7]))

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
        payload.setdefault("activityType", "PROJECT_GENERAL_ACTIVITY")

    # === EMPLOYEE FIXES ===
    if path.rstrip("/") == "/employee" and method == "POST":
        for emp in payload.get("employments", []):
            emp.setdefault("isMainEmployer", True)
            emp.setdefault("startDate", TODAY)

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
                account["bankAccountNumber"] = "12345678903"
                await client.call("PUT", f"/ledger/account/{acc_id}", json_data=account)
                print("[SETUP] Bank account registered on 1920", file=sys.stderr)
        _bank_account_registered = True
    except Exception as e:
        print(f"[SETUP ERROR] Bank account: {e}", file=sys.stderr)


async def create_employment(client, employee_id: int):
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

    payload = {
        "employee": {"id": employee_id},
        "startDate": TODAY,
        "isMainEmployer": True,
        "employmentDetails": [
            {
                "date": TODAY,
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
