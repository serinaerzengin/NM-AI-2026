"""Test the full agent pipeline against the Tripletex sandbox."""

import asyncio
import base64
import logging
import os
import time
from dotenv import load_dotenv

load_dotenv()

from agent import run

logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s: %(message)s")


BASE_URL = os.getenv("TRIPLETEX_BASE_URL")
SESSION_TOKEN = os.getenv("TRIPLETEX_SESSION_TOKEN")


# --- Test cases ---

TESTS = [
    # ===== BASIC =====
    {
        "name": "1. Simple customer creation",
        "prompt": "Opprett en kunde med navn 'TestFirma AS', e-post 'test@testfirma.no'.",
        "files": [],
    },
    {
        "name": "2. Multi-step: customer + contact",
        "prompt": (
            "Create a customer called 'Nordlys Consulting AS' with email 'post@nordlys.no'. "
            "Then create a contact person for this customer: 'Ola Nordmann', email 'ola@nordlys.no', phone '91234567'."
        ),
        "files": [],
    },
    {
        "name": "3. Employee creation",
        "prompt": (
            "Registrer en ny ansatt i Tripletex. Fornavn: Kari, Etternavn: Hansen. "
            "Startdato: 2025-01-01."
        ),
        "files": [],
    },

    # ===== COMPLEX — scrambled prompts, multi-step, LLM must reorder =====
    {
        "name": "4. Scrambled: order details before customer",
        "prompt": (
            "Leveringsdato er 2025-08-15. Ordren skal ha 3 linjer:\n"
            "- 5 stk 'Skrivebordlampe' til 450 kr\n"
            "- 10 stk 'USB-kabel' til 89 kr\n"
            "- 2 stk 'Skjermstativ' til 1200 kr\n"
            "Ordredato er 2025-07-01.\n"
            "Å ja, kunden heter 'Kontorutstyr Bergen AS' med e-post 'ordre@kontorutstyr.no'.\n"
            "Opprett alt dette i Tripletex."
        ),
        "files": [],
    },
    {
        "name": "5. Multiple customers + contacts in one prompt",
        "prompt": (
            "Registrer disse tre kundene i Tripletex:\n"
            "1. 'Fjellsport AS' — e-post: post@fjellsport.no, kontaktperson: Per Fjell, per@fjellsport.no\n"
            "2. 'Havfisk AS' — e-post: post@havfisk.no, kontaktperson: Lise Hav, lise@havfisk.no\n"
            "3. 'Skog & Natur AS' — e-post: post@skognatur.no, kontaktperson: Erik Skog, erik@skognatur.no"
        ),
        "files": [],
    },
    {
        "name": "6. Mixed languages — German prompt",
        "prompt": (
            "Erstellen Sie einen Kunden namens 'München Technik GmbH' mit der E-Mail 'info@muenchen-technik.de'. "
            "Dann erstellen Sie ein Produkt 'Laptop-Ständer' zum Preis von 599 NOK. "
            "Erstellen Sie eine Bestellung für diesen Kunden mit dem Produkt, "
            "Bestelldatum 2025-05-01, Lieferdatum 2025-05-15."
        ),
        "files": [],
    },
    {
        "name": "7. Implicit dependencies — contact before mentioning customer",
        "prompt": (
            "Kontaktpersonen heter 'Anna Larsen' med e-post anna@techstartup.no og telefon 98765432. "
            "Hun jobber hos 'TechStartup Oslo AS' som har e-post faktura@techstartup.no. "
            "Registrer begge i Tripletex."
        ),
        "files": [],
    },
    {
        "name": "8. Complex order with product creation + Norwegian nynorsk",
        "prompt": (
            "Eg treng å registrere ein ny ordre. Kunden er 'Vestland Bygg AS' med e-post vest@bygg.no. "
            "Produkta som skal bestillast:\n"
            "- 'Sement 25kg' — pris 149 kr, antal 20\n"
            "- 'Armering 12mm' — pris 89 kr per meter, antal 100\n"
            "Ordredato: 2025-09-01, leveringsdato: 2025-09-15."
        ),
        "files": [],
    },

    # ===== WITH FILES =====
    {
        "name": "9. CSV file — multiple products",
        "prompt": "Opprett alle produktene fra vedlagt fil i Tripletex.",
        "files": [
            {
                "filename": "produkter.csv",
                "mime_type": "text/csv",
                "content_base64": base64.b64encode(
                    b"navn,pris,beskrivelse\n"
                    b"Kontorpult Delux,4500,Justerbar kontorpult\n"
                    b"Ergonomisk Stol Pro,6200,Kontorstol med nakkestoette\n"
                    b"Skjerm 27 tommer,3800,4K IPS skjerm\n"
                    b"Tastatur Mek,1200,Mekanisk tastatur\n"
                    b"Mus Ergonomisk,650,Vertikal ergonomisk mus\n"
                ).decode(),
            }
        ],
    },
    {
        "name": "10. JSON file — customer + order data",
        "prompt": "Opprett kunden og ordren fra vedlagt JSON-fil.",
        "files": [
            {
                "filename": "bestilling.json",
                "mime_type": "application/json",
                "content_base64": base64.b64encode(
                    b'{\n'
                    b'  "kunde": {\n'
                    b'    "navn": "Digitale Loesninger AS",\n'
                    b'    "epost": "faktura@diglos.no",\n'
                    b'    "org_nr": "987654321"\n'
                    b'  },\n'
                    b'  "ordre": {\n'
                    b'    "ordredato": "2025-06-01",\n'
                    b'    "leveringsdato": "2025-06-15",\n'
                    b'    "linjer": [\n'
                    b'      {"produkt": "Konsulenttime", "antall": 40, "pris": 1500},\n'
                    b'      {"produkt": "Prosjektledelse", "antall": 10, "pris": 2000}\n'
                    b'    ]\n'
                    b'  }\n'
                    b'}'
                ).decode(),
            }
        ],
    },
    {
        "name": "11. Scrambled + file — contact info in file, customer in prompt",
        "prompt": (
            "Kunden er 'Nordkapp Reiseliv AS' med e-post booking@nordkapp.no. "
            "Se vedlagt fil for kontaktpersoner som skal registreres."
        ),
        "files": [
            {
                "filename": "kontakter.txt",
                "mime_type": "text/plain",
                "content_base64": base64.b64encode(
                    b"Kontaktpersoner for Nordkapp Reiseliv AS:\n"
                    b"\n"
                    b"1. Navn: Siri Nordlys\n"
                    b"   E-post: siri@nordkapp.no\n"
                    b"   Telefon: 91111111\n"
                    b"\n"
                    b"2. Navn: Magnus Fjord\n"
                    b"   E-post: magnus@nordkapp.no\n"
                    b"   Telefon: 92222222\n"
                ).decode(),
            }
        ],
    },
]


async def run_test(test: dict):
    """Run a single test case."""
    print(f"\n{'='*60}")
    print(f"TEST: {test['name']}")
    print(f"Prompt: {test['prompt'][:120]}...")
    if test["files"]:
        print(f"Files: {[f['filename'] for f in test['files']]}")
    print(f"{'='*60}")

    t0 = time.monotonic()
    try:
        await run(
            prompt=test["prompt"],
            base_url=BASE_URL,
            session_token=SESSION_TOKEN,
            files=test["files"] if test["files"] else None,
        )
        elapsed = time.monotonic() - t0
        print(f"\n>> DONE in {elapsed:.1f}s")
    except Exception as e:
        elapsed = time.monotonic() - t0
        print(f"\n>> FAILED in {elapsed:.1f}s: {e}")
        import traceback
        traceback.print_exc()


async def main():
    if not BASE_URL or not SESSION_TOKEN:
        print("ERROR: Set TRIPLETEX_BASE_URL and TRIPLETEX_SESSION_TOKEN in .env")
        return

    print(f"Base URL: {BASE_URL}")
    print(f"Token: {SESSION_TOKEN[:20]}...")

    import sys
    if len(sys.argv) > 1:
        # Run specific tests: "python test_agent.py 4 5 6" or "python test_agent.py 4-8"
        indices = []
        for arg in sys.argv[1:]:
            if "-" in arg:
                start, end = arg.split("-")
                indices.extend(range(int(start) - 1, int(end)))
            else:
                indices.append(int(arg) - 1)
        for idx in indices:
            await run_test(TESTS[idx])
    else:
        for test in TESTS:
            await run_test(test)


if __name__ == "__main__":
    asyncio.run(main())
