"""Thomas's approach: OpenAI Agents SDK + LiteLLM (Gemini) with typed OpenAPI tools + skills."""

from pathlib import Path
from agents import Agent, Runner
from agents.extensions.models.litellm_model import LitellmModel
from core.openapi_tools import make_openapi_tools

SKILLS_DIR = Path(__file__).parent / "skills"
MODEL = LitellmModel(model="gemini/gemini-3.1-pro-preview")


def _load_skill(name: str) -> str:
    p = SKILLS_DIR / f"{name}.md"
    return p.read_text() if p.exists() else ""


SYSTEM = """\
You are an accounting assistant for Tripletex. Complete the task using the provided API tools.

Rules:
- Parse the prompt FULLY before making any API call. Extract ALL entity names, field values, and relationships first
- Prompts can be in Norwegian, English, Spanish, Portuguese, Nynorsk, German, or French
- Be precise — use exact values from the prompt, do not guess
- EFFICIENCY IS CRITICAL — fewer API calls = higher score. Never search before creating unless you need an existing entity's ID
- Do NOT make GET calls to "check" if something exists before creating it — just create it directly
- Include ALL fields in a single create call — don't create then update
- If a call fails, read the error message and fix it in ONE retry
- For body params, pass a JSON string e.g. '{"firstName": "Ola", "lastName": "Nordmann"}'
- For nested objects use {"id": 123} format e.g. '{"customer": {"id": 456}}'
- For addresses: include postalAddress inline e.g. '{"name":"X","postalAddress":{"addressLine1":"Street 1","postalCode":"1234","city":"Oslo"}}'
- Supplier (leverandør) = isSupplier: true. Customer (kunde) = isCustomer: true. Can be both

Multi-step task patterns (do these in order, save IDs from each response):
1. INVOICE: create_customer → create_product → create_order (with customer ID) → create_order_line (with order ID + product ID + count + price) → create_invoice (with customer ID + order ID + dates)
2. PAYMENT: same as invoice, then → invoice_payment (with invoice ID + date + amount + payment type)
3. CREDIT NOTE: find invoice → invoice_credit_note (with invoice ID)
4. For payment type ID: search for it with search_invoices or use payment type 1 as default

""" + _load_skill("api-reference") + "\n\n" + _load_skill("languages")


async def run(prompt: str, base_url: str, session_token: str, files: list[dict] | None = None):
    tools = make_openapi_tools(base_url, session_token, skills_dir=SKILLS_DIR)
    agent = Agent(
        name="TripletexAgent",
        instructions=SYSTEM,
        tools=tools,
        model=MODEL,
    )
    await Runner.run(agent, input=prompt, max_turns=25)
