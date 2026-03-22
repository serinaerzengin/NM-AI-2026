#!/usr/bin/env python3
"""Parse Cloud Run logs into structured JSONL dataset.

Usage:
    # Fetch fresh logs and parse
    python scripts/parse_logs.py

    # Parse from existing file
    python scripts/parse_logs.py --file /tmp/logs.txt

    # Limit to N most recent runs
    python scripts/parse_logs.py --limit 20

Output: docs/runs_dataset.jsonl (one JSON object per run)
"""
import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime

# Task type classification rules (keyword → type)
TASK_CLASSIFIERS = [
    # Order matters — first match wins
    (r"(employment contract|arbeidskontrakt|contrat de travail|contrato de trabajo|Arbeitsvertrag).*(PDF|pdf|vedlagt|attached|ci-joint|adjunt|anexo|beigef)", "employee_onboarding_pdf"),
    (r"(bank.?statement|kontoauszug|Kontoauszug|extrait.*bancaire|extracto.*bancario|kontoutskrift).*(CSV|csv|beigef|vedlagt|attached)", "bank_reconciliation"),
    (r"(recu|receipt|kvittering|Quittung|recibo|kvitter).*(departement|department|avdeling|Abteilung)", "receipt_expense"),
    (r"(travel.?expense|reisekostnad|Reisekosten|frais de d[eé]placement|gastos de viaje|reiseutgift|reise.?kostnad|despesa de viagem)", "travel_expense"),
    (r"(errors in the general ledger|erreurs dans le grand livre|erros no livro raz|Fehler im Hauptbuch|errores en el libro mayor|feil i hovud)", "ledger_error_correction"),
    (r"(monthly closing|cierre mensual|encerramento mensal|clôture mensuelle|Monatsabschluss|m[åa]na[vd]slutning|m[åa]nedsavslutning)", "monthly_closing"),
    (r"(year.?end|årsoppgj|Jahresabschluss|clôture annuelle|cierre anual|encerramento anual|forenkla årsoppgjer)", "year_end_closing"),
    (r"(complete project lifecycle|cycle de vie.*projet|ciclo de vida.*proyecto|ciclo de vida.*projeto|Projektlebenszyklus|fullstendig prosjekt|prosjektsyklus|hele prosjekt)", "project_lifecycle"),
    (r"(fixed price|fastpris|prix fixe|precio fijo|preço fixo|Festpreis).*(milestone|milepæl|étape|hito|marco)", "project_fixed_price_milestone"),
    (r"(log.*hours|registrer.*timer|enregistrer.*heures|registre.*horas|Stunden.*erfassen|logg.*timer).*(invoice|faktura|facture|fatura|Rechnung)", "project_hours_invoice"),
    (r"(cost.*increase|kostnadsøkning|Kostenanstieg|augmentation.*coûts|aumento.*costes|aumento.*custos|kostnad.*økt)", "cost_analysis"),
    (r"(credit.?note|kreditnota|avoir|nota de cr[eé]dito|Gutschrift)", "credit_note"),
    (r"(exchange rate|valutadifferanse|Wechselkurs|taux de change|tipo de cambio|taxa de câmbio|agio|disagio|kurs)", "foreign_currency_invoice"),
    (r"(salary|payroll|l[øo]nn|salaire|paie|salario|nómina|Gehalt|Lohn|Køyr løn)", "payroll"),
    (r"(supplier invoice|leverandørfaktura|facture.*fournisseur|factura.*proveedor|fatura.*fornecedor|Lieferantenrechnung|fatura.*INV|factura.*INV|Rechnung.*INV)", "supplier_invoice"),
    (r"(payment.*returned|reversal|tilbakef|devolvido|devuelto|retourné|Rückbuchung|reversering)", "payment_reversal"),
    (r"(three.*product|trois.*produit|tres.*producto|três.*produto|drei.*Produkt|tre.*produkt).*(VAT|MVA|TVA|IVA|MwSt)", "multi_vat_invoice"),
    (r"(order|ordre|bestilling|pedido|encomenda|Bestellung).*(invoice|faktura|facture|fatura|Rechnung).*(payment|betaling|paiement|pago|pagamento|Zahlung)", "order_to_invoice_payment"),
    (r"(dimension|dimensjon|dimensão).*(voucher|bilag|pièce|asiento|lançamento|lance|Buchung)", "custom_dimension_voucher"),
    (r"(create|opprett|créez|cree|crie|erstellen).*(customer|kunde|client|cliente)", "create_customer"),
    (r"(create|opprett|register|créez|cree|crie|erstellen).*(supplier|leverandør|fournisseur|proveedor|fornecedor|Lieferant)", "create_supplier"),
    (r"(create|opprett|créez|cree|crie|erstellen).*(product|produkt|produit|producto|produto|Produkt)", "create_product"),
    (r"(create|opprett|créez|cree|crie|erstellen).*(project|prosjekt|projet|proyecto|projeto|Projekt)", "create_project"),
    (r"(invoice|faktura|facture|fatura|Rechnung).*(send|send|envoy|envi|enviar)", "simple_invoice"),
    (r"(invoice|faktura|facture|fatura|Rechnung)", "simple_invoice"),
]


def classify_task(prompt: str) -> str:
    for pattern, task_type in TASK_CLASSIFIERS:
        if re.search(pattern, prompt, re.IGNORECASE):
            return task_type
    return "unknown"


def parse_logs(lines: list[str]) -> list[dict]:
    """Parse raw log lines into structured run records."""
    runs = defaultdict(lambda: {
        "req_id": None,
        "prompt": "",
        "start_time": None,
        "end_time": None,
        "calls": 0,
        "errors": 0,
        "turns": [],
        "api_calls": [],
        "api_errors": [],
        "outcome": "unknown",
        "output": "",
    })

    for line in lines:
        line = line.strip()

        # Extract req_id from [req_id] pattern
        m = re.search(r'\[([a-f0-9]{8})\]', line)
        if not m:
            continue
        req_id = m.group(1)
        run = runs[req_id]
        run["req_id"] = req_id

        # Parse timestamp
        ts_match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
        timestamp = ts_match.group(1) if ts_match else None

        # SOLVE START
        if "[SOLVE] START prompt=" in line:
            prompt = line.split("prompt=", 1)[1] if "prompt=" in line else ""
            run["prompt"] = prompt
            run["start_time"] = timestamp

        # SOLVE Done
        elif "[SOLVE] Done:" in line:
            run["end_time"] = timestamp
            dm = re.search(r'(\d+) calls?, (\d+) errors?', line)
            if dm:
                run["calls"] = int(dm.group(1))
                run["errors"] = int(dm.group(2))
            run["outcome"] = "completed"

        # AGENT Done
        elif "[AGENT] Done" in line:
            om = re.search(r'output=(.+)', line)
            if om:
                run["output"] = om.group(1)[:300]
            run["outcome"] = "completed"

        # AGENT Error
        elif "[AGENT] Error" in line or "[AGENT] TIMEOUT" in line:
            run["outcome"] = "error" if "Error" in line else "timeout"
            run["output"] = line.split("]")[-1].strip() if "]" in line else line

        # AGENT Proxy expired
        elif "Proxy token expired" in line:
            run["outcome"] = "proxy_expired"

        # TURN markers
        elif "[TURN " in line and "] LLM called" in line:
            tm = re.search(r'\[TURN (\d+)\]', line)
            if tm:
                run["turns"].append(int(tm.group(1)))

        # CALL markers
        elif "[CALL]" in line:
            cm = re.search(r'\[CALL\] (\w+)\((.+)\)', line)
            if cm:
                tool = cm.group(1)
                args_str = cm.group(2)[:200]
                # Extract path
                pm = re.search(r'"path"\s*:\s*"([^"]+)"', args_str)
                path = pm.group(1) if pm else "?"
                run["api_calls"].append({"tool": tool, "path": path})

        # TOOL lines (old format)
        elif "[TOOL] tripletex_" in line:
            tm = re.search(r'\[TOOL\] (tripletex_\w+): (\S+)', line)
            if tm:
                tool = tm.group(1)
                path = tm.group(2)
                run["api_calls"].append({"tool": tool, "path": path})

        # API errors
        elif re.search(r'\[API [45]\d\d\]', line):
            em = re.search(r'\[API (\d+)\] (\w+) (\S+): (.+)', line)
            if em:
                run["api_errors"].append({
                    "status": int(em.group(1)),
                    "method": em.group(2),
                    "path": em.group(3),
                    "message": em.group(4)[:200],
                })

    return [r for r in runs.values() if r["prompt"]]


def to_dataset(runs: list[dict]) -> list[dict]:
    """Convert parsed runs into dataset entries."""
    entries = []
    for run in runs:
        task_type = classify_task(run["prompt"])
        max_turn = max(run["turns"]) if run["turns"] else 0

        # Calculate duration
        duration = None
        if run["start_time"] and run["end_time"]:
            try:
                t1 = datetime.strptime(run["start_time"], "%Y-%m-%d %H:%M:%S")
                t2 = datetime.strptime(run["end_time"], "%Y-%m-%d %H:%M:%S")
                duration = (t2 - t1).total_seconds()
            except ValueError:
                pass

        # Summarize API call sequence
        call_sequence = []
        for c in run["api_calls"]:
            method = c["tool"].replace("tripletex_", "").upper()
            call_sequence.append(f"{method} {c['path']}")

        entries.append({
            "req_id": run["req_id"],
            "task_type": task_type,
            "prompt": run["prompt"][:600],
            "outcome": run["outcome"],
            "duration_s": duration,
            "turns": max_turn + 1 if run["turns"] else 0,
            "api_calls": run["calls"],
            "api_errors": run["errors"],
            "call_sequence": call_sequence,
            "error_details": run["api_errors"],
            "output": run["output"][:200],
            "timestamp": run["start_time"],
        })

    return entries


def main():
    parser = argparse.ArgumentParser(description="Parse Cloud Run logs into JSONL dataset")
    parser.add_argument("--file", help="Read from file instead of fetching")
    parser.add_argument("--limit", type=int, default=50, help="Max runs to output")
    parser.add_argument("--fetch-lines", type=int, default=3000, help="Lines to fetch from Cloud Run")
    parser.add_argument("--output", default="docs/runs_dataset.jsonl", help="Output file")
    args = parser.parse_args()

    if args.file:
        with open(args.file) as f:
            lines = f.readlines()
    else:
        print(f"Fetching {args.fetch_lines} log lines from Cloud Run...", file=sys.stderr)
        result = subprocess.run(
            ["gcloud", "run", "services", "logs", "read", "tripletex-agent",
             "--region", "europe-north1", "--project", "ai-nm26osl-1813",
             "--limit", str(args.fetch_lines)],
            capture_output=True, text=True, timeout=60
        )
        lines = result.stdout.splitlines()
        # Also save raw logs
        with open("/tmp/tripletex_latest_logs.txt", "w") as f:
            f.write(result.stdout)
        print(f"Fetched {len(lines)} lines, saved to /tmp/tripletex_latest_logs.txt", file=sys.stderr)

    runs = parse_logs(lines)
    dataset = to_dataset(runs)

    # Sort by timestamp descending
    dataset.sort(key=lambda x: x.get("timestamp") or "", reverse=True)

    # Limit
    dataset = dataset[:args.limit]

    # Write JSONL
    out_path = os.path.join(os.path.dirname(__file__), "..", args.output)
    out_path = os.path.normpath(out_path)
    with open(out_path, "w") as f:
        for entry in dataset:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"\nWrote {len(dataset)} runs to {out_path}", file=sys.stderr)

    # Print summary
    type_counts = defaultdict(lambda: {"count": 0, "ok": 0, "err": 0, "total_calls": 0})
    for e in dataset:
        t = type_counts[e["task_type"]]
        t["count"] += 1
        if e["outcome"] == "completed":
            t["ok"] += 1
        else:
            t["err"] += 1
        t["total_calls"] += e["api_calls"]

    print(f"\n{'Task Type':<35} {'Runs':>5} {'OK':>4} {'Err':>4} {'Avg Calls':>10}", file=sys.stderr)
    print("-" * 62, file=sys.stderr)
    for task_type in sorted(type_counts.keys()):
        t = type_counts[task_type]
        avg = t["total_calls"] / t["count"] if t["count"] else 0
        print(f"{task_type:<35} {t['count']:>5} {t['ok']:>4} {t['err']:>4} {avg:>10.1f}", file=sys.stderr)


if __name__ == "__main__":
    main()
