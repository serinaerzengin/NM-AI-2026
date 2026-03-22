# NS 4102 — Norwegian Standard Chart of Accounts (Kontoplan)

## Research Sources
- Tripletex sandbox: GET /ledger/account?count=2000 → 531 accounts
- NS 4102 standard (via jithomassen.no, regnskapskoden.no, favrit.com)
- Unimicro hjelpesenter (kontoklassene i NS 4102)
- Tripletex developer docs (developer.tripletex.no)

## Key Finding: Why the LLM Wastes API Calls

From v4 efficiency analysis: the LLM probed 12 different account numbers (1209, 1239, 1249, 1149, 1230, 1240, 1250, 1140, 1241, 1231, 1201, 1290) looking for an accumulated depreciation account. **These accounts don't exist as separate "accumulated depreciation" entries in the default Tripletex chart.** The LLM doesn't know the NS 4102 structure and guesses blindly.

**Total waste**: ~68 duplicate GET /ledger/account calls across 10 runs, biggest single offender being 26 calls in one run (98757578).

---

## NS 4102 Structure (4-digit accounts)

First digit = class, first two digits = group.

### Class 1 — Eiendeler (Assets)

| Group | Name | Key Accounts |
|-------|------|-------------|
| 10xx | Immaterielle eiendeler | 1000=Forskning/utvikling ervervet, 1005=egenutviklet, 1020=Konsesjoner, 1030=Patenter, 1040=Lisenser, 1050=Varemerker, 1060=Andre rettigheter, 1070=Utsatt skattefordel, 1080=Goodwill |
| 11xx | Bygninger/fast eiendom | 1100=Forretningsbygg, 1117=Elektroteknisk utrustning, 1120=Bygningsmessig anlegg, 1130=Anlegg under utførelse, 1150=Tomter, 1160=Boliger, 1180=Investeringseiendommer |
| 12xx | Transportmidler/maskiner/inventar | 1200=Maskiner og anlegg, 1210=Maskiner under utførelse, 1220=Skip, 1225=Fly, 1230=Vare-/lastebiler, 1240=Traktorer, 1249=Andre transportmidler, 1250=Inventar, 1260=Fast bygningsinventar eget bygg, 1265=leide bygg, 1270=Verktøy, 1280=Kontormaskiner, 1290=Andre driftsmidler, 1291=ikke avskrivbare |
| 13xx | Finansielle anleggsmidler | 1300=Datterselskap, 1350=Aksjer/andeler, 1370=Fordringer eiere, 1380=Fordringer ansatte, 1396=Depositum |
| 14xx | Varelager | 1400=Råvarer, 1420=Under tilvirkning, 1440=Ferdig tilvirkede, 1460=Innkjøpte varer for videresalg, 1480=Forskudd til leverandører |
| 15xx | Kortsiktige fordringer | 1500=Kundefordringer, 1570=Reiseforskudd, 1571=Lønnsforskudd, 1580=Avsetning tap kundefordringer |
| 16xx | MVA | 1600=Utg.MVA høy, 1610=Inng.MVA høy, 1640=Oppgjørskonto MVA, 1670=Krav offentlige tilskudd |
| 17xx | Periodiseringer | 1700=Forskuddsbetalt leie, 1710=Forskuddsbetalt rente, 1720=Andre depositum, 1740=Forskuddsbetalt lønn, 1741=Strøm/varme, 1742=Forsikring, 1749=Andre forskuddsbetalte, 1750=Påløpt leieinntekt, 1760=Påløpt renteinntekt, 1770=Andre periodiseringer |
| 18xx | Kortsiktige finansinvesteringer | 1810=Markedsbaserte aksjer, 1820=Andre aksjer, 1830=Obligasjoner |
| 19xx | Bank/kontanter | 1900=Kontanter NOK, 1908=Kontanter annen valuta, 1920=Bankinnskudd, 1940=Bank utland, 1950=Skattetrekk |

### Class 2 — Egenkapital og gjeld (Equity & Liabilities)

| Group | Name | Key Accounts |
|-------|------|-------------|
| 20xx | Egenkapital | 2000=Aksjekapital, 2020=Overkurs, 2050=Annen egenkapital, 2080=Udekket tap |
| 21xx | Avsetning forpliktelser | 2100=Pensjonsforpliktelser, 2120=Utsatt skatt |
| 22xx | Langsiktig gjeld | 2200=Konvertible lån, 2220=Gjeld kredittinstitusjoner, 2250=Gjeld ansatte/eiere |
| 23xx | Kortsiktig gjeld kreditt | 2380=Kassakreditt |
| 24xx | Leverandørgjeld | 2400=Leverandørgjeld (AP) |
| 25xx | Betalbar skatt | 2500=Betalbar skatt ikke utlignet, 2510=utlignet |
| 26xx | Skattetrekk | 2600=Forskuddstrekk, 2610=Utleggstrekk, 2650=Fagforeningskontingent |
| 27xx | Off.avgifter/MVA | 2700=Utg.MVA høy, 2701=middels, 2702=lav, 2710=Inng.MVA 25%, 2711=15%, 2712=lav, 2740=Oppgjørskonto MVA, 2770=Skyldig AGA, 2780=Påløpt AGA på påløpt lønn, 2785=Påløpt AGA feriepenger |
| 28xx | Utbytte | 2800=Avsatt utbytte |
| 29xx | Annen kortsiktig gjeld | 2900=Forskudd fra kunder, 2910=Gjeld ansatte/eiere, 2930=Skyldig lønn, 2940=Skyldig feriepenger, 2950=Påløpt rente, 2960=Annen påløpt kostnad, 2965=Forskuddsbetalt inntekt, 2970=Uopptjent inntekt, 2980=Avsetning styrehonorar, 2981=revisjonshonorar, 2990=Annen kortsiktig gjeld |

### Class 3 — Salgs- og driftsinntekter (Revenue)

| Group | Name | Key Accounts |
|-------|------|-------------|
| 30xx | Avgiftspliktig salg | 3000=Salg avgiftspliktig (25%), 3001=middels sats, 3002=lav sats |
| 31xx | Avgiftsfri salg | |
| 32xx | Utenfor avgiftsområdet | |
| 36xx | Leieinntekt | |
| 38xx | Gevinst avgang anleggsmidler | |
| 39xx | Annen driftsinntekt | |

### Class 4 — Varekostnader (COGS)

| Group | Name | Key Accounts |
|-------|------|-------------|
| 40xx | Råvarer/halvfabrikater | 4000=Varekjøp, 4090=Frakt og toll |
| 43xx | Innkjøpte varer videresalg | 4300=Innkjøpte varer |

### Class 5 — Lønnskostnader (Payroll)

| Group | Name | Key Accounts |
|-------|------|-------------|
| 50xx | Lønn | 5000=Lønn til ansatte, 5092=Feriepenger |
| 52xx | Fordel i arbeidsforhold | |
| 54xx | AGA/pensjon | 5400=Arbeidsgiveravgift, 5420=Yrkesforsikring |
| 59xx | Annen personalkostnad | |

### Class 6 — Driftskostnader I (Depreciation, premises, office)

| Group | Name | Key Accounts |
|-------|------|-------------|
| 60xx | Avskrivning | 6000=Avskr.bygninger/fast eiendom, 6010=Avskr.transportmidler, 6015=Avskr.maskiner, 6017=Avskr.inventar, 6020=Avskr.immaterielle, 6050=Nedskrivning |
| 61xx | Frakt/transport salg | |
| 62xx | Energi/produksjon | |
| 63xx | Lokaler | 6300=Leie lokaler, 6340=Lys/varme |
| 64xx | Leie maskiner/inventar | |
| 65xx | Verktøy/inventar (ikke aktivert) | 6500=Kontorkostnader, 6540=Inventar |
| 66xx | Reparasjon/vedlikehold | |
| 67xx | Fremmedtjeneste | |
| 68xx | Kontorkostnad | 6800=Kontorrekvisita, 6860=Møte/kurs |
| 69xx | Telefon/porto | |

### Class 7 — Driftskostnader II (Transport, travel, marketing)

| Group | Name | Key Accounts |
|-------|------|-------------|
| 70xx | Transportmidler | 7000=Drivstoff, 7020=Vedlikehold, 7040=Forsikring, 7080=Bilkostnader, 7100=Bilgodtgjørelse |
| 71xx | Reise/diett | 7130=Reisekostnader, 7140=Reise og diett |
| 73xx | Salg/reklame | 7300=Markedsføring, 7320=Reklame, 7350=Representasjon |
| 74xx | Kontingent/gaver | |
| 75xx | Forsikring | |
| 77xx | Annen kostnad | |
| 78xx | Tap | |

### Class 8 — Finansposter (Financial items)

| Group | Name | Key Accounts |
|-------|------|-------------|
| 80xx | Finansinntekter | 8000=Inntekt datterselskap, 8050=Renteinntekt, 8060=Valutagevinst (agio), 8070=Annen finansinntekt, 8078=Gevinst aksjer |
| 81xx | Finanskostnader | 8100=Verdireduksjon fin.instrumenter, 8150=Rentekostnad, 8160=Valutatap (disagio), 8170=Annen finanskostnad, 8178=Tap aksjer |
| 83xx | Skattekostnad | |
| 88xx | Årsresultat | 8800=Årsresultat |
| 89xx | Overføringer | 8960=Overføring annen egenkapital |

---

## Critical: Depreciation Account Pairs

In NS 4102, there are **NO separate accumulated depreciation accounts** (no 1209, 1219, etc.) in the default Tripletex chart. Depreciation is posted directly as expense.

| Asset Account | Depreciation Expense Account |
|--------------|----------------------------|
| 1100 Forretningsbygg | 6000 Avskr.bygninger |
| 1200 Maskiner og anlegg | 6015 Avskr.maskiner |
| 1230 Biler | 6010 Avskr.transportmidler |
| 1250 Inventar | 6017 Avskr.inventar |
| 1280 Kontormaskiner | 6017 Avskr.inventar |
| 1000-1080 Immaterielle | 6020 Avskr.immaterielle |

**If a task requires an accumulated depreciation contra-account** (e.g. "akkumulert avskrivning"), it must be CREATED with POST /ledger/account. The convention is asset number + 9 (e.g. 1209 for 1200, 1259 for 1250).

---

## Suggested System Prompt Changes

### 1. Expand Chart of Accounts (HIGH — saves ~68 calls)
Replace the single-line chart with a structured reference covering all 8 classes. The LLM needs to know:
- Depreciation expense accounts (60xx) and their asset pairs
- Periodization accounts (17xx, 29xx) for month-end/year-end closing
- Financial accounts (80xx, 81xx) for agio/disagio
- That accumulated depreciation accounts DON'T exist by default — must be created

### 2. Batch Account Lookup Rule (HIGH — saves ~50 calls)
Add: "If you need an account not in the chart above, do ONE call: GET /ledger/account?count=1000 to see ALL accounts. Use IDs from that response. Do NOT probe accounts one at a time."

### 3. Stronger No-Verification Rule (MEDIUM — saves ~10 calls)
Current rule 10 already says this but LLM still verifies. Make more explicit:
"After POST/PUT succeeds, do NOT call GET on the same resource, balance sheet, or postings to verify. The task is done — move to next step or finish."

---

## Sandbox Validation Notes

- GET /ledger/account?count=2000 returns all 531 accounts in ONE call (200 OK) ✅
- POST /ledger/account/list can batch-create new accounts (201) ✅
- Sandbox chart matches NS 4102 standard exactly
- No accumulated depreciation accounts exist by default — confirmed
