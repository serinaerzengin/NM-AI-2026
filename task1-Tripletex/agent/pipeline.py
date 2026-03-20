"""
Preprocessing pipeline: translate → rewrite → decompose → format.

Each step has strict data isolation — agents only see what they need.
Every step's input and output is logged for debugging.

Flow:
  1. Translator      (LLM)  — multilingual prompt → English
  2. Query Rewriter  (LLM)  — English → clarified, grounded NL
  3. Task Decomposer (LLM)  — clarified NL + index.md → ordered to-do list
  4. Plan Formatter  (code) — to-do list + registry.json → structured plan
  5. Executor        (TODO) — structured plan + credentials → API calls
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from agents import Agent, Runner, function_tool
from agents.extensions.models.litellm_model import LitellmModel

from agent.config import MODEL_ID
from agent.logging_config import setup_logging, write_trace

setup_logging()
logger = logging.getLogger("tripletex-agent.pipeline")

model = LitellmModel(model=MODEL_ID)

# ── Static resources ─────────────────────────────────────────────────────────

SPECS_DIR = Path(__file__).parent.parent / "specs"
INDEX_MD = (SPECS_DIR / "index.md").read_text()
REGISTRY_PATH = SPECS_DIR / "registry.json"


def _load_registry() -> dict:
    with open(REGISTRY_PATH) as f:
        return json.load(f)


# ── Trace logging ────────────────────────────────────────────────────────────


@dataclass
class StepTrace:
    """Record of one pipeline step for debugging."""

    step: int
    name: str
    input: str
    output: str
    duration_ms: float
    extra: dict = field(default_factory=dict)


@dataclass
class PipelineTrace:
    """Full trace of a pipeline run."""

    traces: list[StepTrace] = field(default_factory=list)

    def add(self, trace: StepTrace) -> None:
        self.traces.append(trace)
        logger.info(
            "STEP_%d_%s | %.0fms | input=%s | output=%s",
            trace.step,
            trace.name,
            trace.duration_ms,
            _truncate(trace.input, 200),
            _truncate(trace.output, 300),
        )
        if trace.extra:
            logger.info(
                "STEP_%d_%s_EXTRA | %s",
                trace.step,
                trace.name,
                json.dumps(trace.extra, ensure_ascii=False, default=str)[:500],
            )
        # Write full (untruncated) trace to logs/trace.jsonl
        write_trace(
            step=trace.step,
            name=trace.name,
            input_text=trace.input,
            output_text=trace.output,
            duration_ms=trace.duration_ms,
            extra=trace.extra if trace.extra else None,
        )

    def summary(self) -> str:
        lines = []
        for t in self.traces:
            lines.append(
                f"  Step {t.step} ({t.name}): {t.duration_ms:.0f}ms"
            )
        total = sum(t.duration_ms for t in self.traces)
        lines.append(f"  Total: {total:.0f}ms")
        return "\n".join(lines)


def _truncate(text: str, limit: int) -> str:
    text = text.replace("\n", " ").strip()
    return text[:limit] + "…" if len(text) > limit else text


# ── Step 1: Translator ──────────────────────────────────────────────────────

translator_agent = Agent(
    name="Translator",
    model=model,
    instructions=(
        "You are a translation specialist.\n\n"
        "The user will provide a prompt in one of these languages: "
        "Norwegian Bokmål, Nynorsk, English, Spanish, Portuguese, German, or French.\n\n"
        "Your job:\n"
        "1. If the prompt is already in English, return it unchanged.\n"
        "2. Otherwise, translate ONLY the instruction words to English.\n\n"
        "CRITICAL — Data values must NEVER be translated:\n"
        "- Entity names in quotes (e.g. 'Buchhaltung', 'Servicio de Consultoría') → keep EXACTLY as written\n"
        "- Person names → keep exactly as written\n"
        "- Company names → keep exactly as written\n"
        "- Product names → keep exactly as written\n"
        "- Department names → keep exactly as written\n"
        "- Email addresses → keep exactly as written\n"
        "- Numbers, dates, currency amounts → keep exactly as written\n"
        "- Norwegian characters (æ, ø, å) → keep exactly as written\n\n"
        "Only translate the verbs and structural words around the data values.\n\n"
        "Examples:\n"
        "  IN:  \"Opprett en avdeling med navn 'Buchhaltung'\"\n"
        "  OUT: \"Create a department named 'Buchhaltung'\"\n\n"
        "  IN:  \"Crea un producto llamado 'Servicio de Consultoría' con un precio de 2500 NOK.\"\n"
        "  OUT: \"Create a product named 'Servicio de Consultoría' with a price of 2500 NOK.\"\n\n"
        "  IN:  \"Opprett en kunde med navn 'Fjord Tech AS'\"\n"
        "  OUT: \"Create a customer named 'Fjord Tech AS'\"\n\n"
        "Return ONLY the translation — no commentary, no labels, no JSON."
    ),
)


async def step1_translate(raw_prompt: str, trace: PipelineTrace) -> str:
    """Translate multilingual prompt to English. Sees ONLY the raw prompt."""
    start = time.monotonic()
    result = await Runner.run(translator_agent, input=raw_prompt)
    english = result.final_output
    trace.add(StepTrace(
        step=1,
        name="TRANSLATE",
        input=raw_prompt,
        output=english,
        duration_ms=(time.monotonic() - start) * 1000,
    ))
    return english


# ── Step 2: Query Rewriter ──────────────────────────────────────────────────

rewriter_agent = Agent(
    name="QueryRewriter",
    model=model,
    instructions=(
        "You are a query clarification specialist for an accounting system.\n\n"
        "You receive an English task description. Rewrite it to be unambiguous and explicit.\n\n"
        "What to do:\n"
        '- Map informal terms to standard accounting entity names:\n'
        '  "worker"/"staff member" → employee\n'
        '  "bill" → invoice\n'
        '  "travel claim" → travel expense\n'
        '  "supplier"/"vendor" → supplier\n'
        '  "admin" → account administrator\n'
        "- Make implicit actions explicit (e.g. 'invoice for Acme' implies customer must exist)\n"
        "- Spell out what entities need to be created, modified, or looked up\n"
        "- Preserve ALL exact values: names, emails, amounts, dates — copy them character-for-character\n\n"
        "What NOT to do:\n"
        "- Do NOT output JSON\n"
        "- Do NOT reference specific API endpoints or paths\n"
        "- Do NOT generate an execution plan or numbered steps\n"
        "- Do NOT add information that wasn't in the original\n\n"
        "Output format — plain English text structured as:\n"
        "Task: [one sentence summary]\n"
        "Entities: [entity type (field: \"value\", field: \"value\"), ...]\n"
        "Actions: [what needs to happen in plain English]\n"
        "Prerequisites: [what must exist first, or \"none\"]"
    ),
)


async def step2_rewrite(english_text: str, trace: PipelineTrace) -> str:
    """Clarify and ground the English prompt. Sees ONLY the English text."""
    start = time.monotonic()
    result = await Runner.run(rewriter_agent, input=english_text)
    clarified = result.final_output
    trace.add(StepTrace(
        step=2,
        name="REWRITE",
        input=english_text,
        output=clarified,
        duration_ms=(time.monotonic() - start) * 1000,
    ))
    return clarified


# ── Step 3: Task Decomposer ────────────────────────────────────────────────

# Tool: let the decomposer look up endpoint details from registry.json on demand

_registry_cache: dict | None = None


def _get_registry() -> dict:
    global _registry_cache
    if _registry_cache is None:
        _registry_cache = _load_registry()
    return _registry_cache


@function_tool
def lookup_endpoint(method: str, path: str) -> str:
    """Look up the full schema for a Tripletex API endpoint.

    Use this BEFORE planning to see what fields are required, what linked entities
    (_ref) need IDs resolved, and what enum values are valid.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE)
        path: API path from the endpoint index (e.g. "/employee", "/customer")
    """
    registry = _get_registry()
    key = f"{method.upper()} {path}"
    entry = registry.get(key)
    if not entry:
        return f"No schema found for {key}"

    lines = [f"Schema for {key}:", f"  Summary: {entry.get('summary', '')}"]

    # Request body
    req_body = entry.get("request_body", {})
    props = req_body.get("properties", {})
    required = set(req_body.get("required", []))
    if props:
        lines.append("  Request body fields:")
        for fname, fschema in props.items():
            ftype = fschema.get("type", "?")
            ref = fschema.get("_ref", "")
            enum = fschema.get("enum", [])
            desc = fschema.get("description", "")
            parts = [f"    {fname}: {ftype}"]
            if fname in required:
                parts.append("REQUIRED")
            if ref:
                parts.append(f"⚠ LINKED _ref={ref} → MUST send {{\"id\": <int>}}, GET /{ref.lower()} first to get ID")
            if enum:
                parts.append(f"enum={enum}")
            if desc:
                parts.append(f"— {desc[:80]}")
            lines.append(" ".join(parts))

    # Query params
    qparams = entry.get("query_params", [])
    if qparams:
        lines.append("  Query parameters:")
        for qp in qparams:
            req_flag = " REQUIRED" if qp.get("required") else ""
            enum = qp.get("enum", [])
            desc = qp.get("description", "")
            line = f"    {qp['name']}: {qp.get('type', '?')}{req_flag}"
            if enum:
                line += f" enum={enum}"
            if desc:
                line += f" — {desc[:60]}"
            lines.append(line)

    # Response type
    resp = entry.get("response", {})
    if resp.get("type"):
        accessor = ".value" if resp["type"] == "single" else ".values"
        lines.append(f"  Response: {resp['type']} (read from {accessor})")

    return "\n".join(lines)


decomposer_agent = Agent(
    name="TaskDecomposer",
    model=model,
    tools=[lookup_endpoint],
    instructions=(
        "You are a task planning specialist for the Tripletex accounting API.\n\n"
        "You receive a clarified task description. Your job:\n"
        "1. FIRST: Scan the endpoint index below to identify which endpoints are relevant.\n"
        "2. THEN: Use the lookup_endpoint tool to check each candidate endpoint's schema —\n"
        "   see what fields it needs, which have _ref (linked entities), and what enum values are valid.\n"
        "3. FINALLY: Build a MINIMAL plan — only the steps actually needed for this task.\n\n"
        "IMPORTANT — _ref fields and efficiency:\n"
        "When you see _ref fields in a schema, NOT all of them are needed. Only add a GET step\n"
        "to resolve a _ref if:\n"
        "  - The field is explicitly mentioned in the task (e.g. task says 'in department X')\n"
        "  - The field is one of these commonly required fields that Tripletex enforces:\n"
        "    * department (for employees) — ALWAYS resolve this\n"
        "    * customer (for orders/invoices) — ALWAYS resolve if creating orders/invoices\n"
        "  - The task clearly needs it\n\n"
        "Do NOT add GET steps for every _ref field you see. Fields like phoneNumberMobileCountry,\n"
        "internationalId, address, holidayAllowanceEarned, employeeCategory, discountGroup,\n"
        "supplierProduct, deliveryAddress, etc. are OPTIONAL. Skip them unless the task mentions them.\n\n"
        "Keep the plan SHORT. Fewer API calls = higher efficiency score.\n\n"
        "<endpoint_index>\n"
        f"{INDEX_MD}\n"
        "</endpoint_index>\n\n"
        "Rules:\n"
        "- ALWAYS look up the schema for your main POST/PUT endpoints before writing the plan\n"
        "- Only add prerequisite GET steps for fields the task actually needs\n"
        "- Always resolve department for employees (Tripletex requires it)\n"
        "- Each step must map to exactly ONE API call\n"
        "- Include the HTTP method and path for each step\n"
        "- Mark dependencies with 'depends on: Step N'\n"
        "- Do NOT include authentication details\n"
        "- KEEP THE PLAN MINIMAL — only steps that are necessary\n\n"
        "Output format — numbered steps in plain text:\n\n"
        "Step 1: [description]\n"
        "  → endpoint: [METHOD /path]\n"
        "  → depends on: [none | Step N, Step M]\n\n"
        "Step 2: [description]\n"
        "  → endpoint: [METHOD /path]\n"
        "  → depends on: [Step 1]\n"
    ),
)


async def step3_decompose(clarified_text: str, trace: PipelineTrace) -> str:
    """Decompose into ordered to-do list. Sees clarified text + index.md + can look up registry."""
    start = time.monotonic()
    result = await Runner.run(decomposer_agent, input=clarified_text, max_turns=15)
    todo = result.final_output
    trace.add(StepTrace(
        step=3,
        name="DECOMPOSE",
        input=clarified_text,
        output=todo,
        duration_ms=(time.monotonic() - start) * 1000,
    ))
    return todo


# ── Step 4: Plan Formatter (code, not LLM) ─────────────────────────────────


@dataclass
class PlanStep:
    """One step in the execution plan, enriched with registry schema."""

    step: int
    action: str
    method: str
    endpoint: str
    schema: dict
    depends_on: list[int]
    condition: str = ""


@dataclass
class ExecutionPlan:
    """Structured plan ready for the executor."""

    steps: list[PlanStep]
    raw_todo: str  # original NL from decomposer (for debugging)


def _parse_todo(todo_text: str) -> list[dict]:
    """Parse the NL to-do list into step dicts."""
    steps: list[dict] = []
    current: dict | None = None

    for line in todo_text.strip().splitlines():
        line = line.strip()

        step_match = re.match(r"Step\s+(\d+):\s*(.+)", line)
        if step_match:
            if current:
                steps.append(current)
            current = {
                "step": int(step_match.group(1)),
                "action": step_match.group(2).strip(),
                "method": "",
                "endpoint": "",
                "depends_on": [],
                "condition": "",
            }
            continue

        if not current:
            continue

        # → endpoint: METHOD /path
        ep_match = re.match(
            r"[→>-]\s*endpoint:\s*(GET|POST|PUT|DELETE|PATCH)\s+(/\S+)",
            line,
            re.I,
        )
        if ep_match:
            current["method"] = ep_match.group(1).upper()
            current["endpoint"] = ep_match.group(2)
            continue

        # → depends on: Step 1, Step 3 | none
        dep_match = re.match(r"[→>-]\s*depends\s+on:\s*(.+)", line, re.I)
        if dep_match:
            dep_text = dep_match.group(1).strip()
            if dep_text.lower() == "none":
                current["depends_on"] = []
            else:
                current["depends_on"] = [
                    int(d) for d in re.findall(r"Step\s+(\d+)", dep_text)
                ]
            continue

        # Capture condition text
        if line.lower().startswith("if ") or "condition" in line.lower():
            current["condition"] = line

    if current:
        steps.append(current)

    return steps


def _enrich_with_registry(
    steps: list[dict], registry: dict
) -> list[PlanStep]:
    """Look up each endpoint in registry.json and attach its schema."""
    enriched = []
    for s in steps:
        key = f"{s['method']} {s['endpoint']}"
        schema = registry.get(key, {})
        enriched.append(
            PlanStep(
                step=s["step"],
                action=s["action"],
                method=s["method"],
                endpoint=s["endpoint"],
                schema=schema,
                depends_on=s["depends_on"],
                condition=s.get("condition", ""),
            )
        )
    return enriched


def step4_format(todo_text: str, trace: PipelineTrace) -> ExecutionPlan:
    """Parse to-do list and enrich with registry schemas. Pure code, no LLM."""
    start = time.monotonic()
    registry = _load_registry()
    parsed = _parse_todo(todo_text)
    steps = _enrich_with_registry(parsed, registry)

    # Log which endpoints were matched vs missed
    matched = [s for s in steps if s.schema]
    missed = [s for s in steps if not s.schema]

    plan = ExecutionPlan(steps=steps, raw_todo=todo_text)

    # Build a compact output summary for the trace
    step_summaries = []
    for s in steps:
        has_body = "request_body" in s.schema
        has_params = "query_params" in s.schema
        refs = [
            k for k, v in s.schema.get("request_body", {}).get("properties", {}).items()
            if isinstance(v, dict) and "_ref" in v
        ]
        step_summaries.append(
            f"Step {s.step}: {s.method} {s.endpoint}"
            f" [body={has_body}, params={has_params}"
            f"{', refs=' + ','.join(refs) if refs else ''}]"
            f" depends_on={s.depends_on}"
        )

    trace.add(StepTrace(
        step=4,
        name="FORMAT",
        input=f"{len(parsed)} steps parsed from todo",
        output="\n".join(step_summaries),
        duration_ms=(time.monotonic() - start) * 1000,
        extra={
            "matched_endpoints": len(matched),
            "missed_endpoints": len(missed),
            "missed_keys": [f"{s.method} {s.endpoint}" for s in missed],
        },
    ))

    return plan


# ── Full pipeline ────────────────────────────────────────────────────────────


@dataclass
class PipelineResult:
    """Everything the executor needs, plus the full trace for debugging."""

    plan: ExecutionPlan
    trace: PipelineTrace


async def preprocess(prompt: str) -> PipelineResult:
    """Run Steps 1-4: translate → rewrite → decompose → format.

    No credentials or files touch this function — those go straight to the executor.
    """
    trace = PipelineTrace()

    english = await step1_translate(prompt, trace)
    clarified = await step2_rewrite(english, trace)
    todo = await step3_decompose(clarified, trace)
    plan = step4_format(todo, trace)

    logger.info("PIPELINE_COMPLETE\n%s", trace.summary())

    return PipelineResult(plan=plan, trace=trace)


async def run(
    prompt: str,
    base_url: str,
    session_token: str,
    files: list | None = None,
) -> None:
    """Entry point called from api.py /solve endpoint."""

    # Steps 1-4: preprocessing (no credentials, no files)
    result = await preprocess(prompt)

    # Step 5: executor
    # Receives ONLY: result.plan, base_url, session_token, files
    # Does NOT receive: prompt, english, clarified, todo, index.md, full registry
    from agent.toolcaller import execute

    ctx = await execute(
        plan_steps=result.plan.steps,
        base_url=base_url,
        session_token=session_token,
        files=files,
    )

    logger.info(
        "RUN_COMPLETE | %d plan steps | %d API calls | %d errors",
        len(result.plan.steps),
        len(ctx.call_log),
        sum(1 for c in ctx.call_log if c["status"] >= 400),
    )
