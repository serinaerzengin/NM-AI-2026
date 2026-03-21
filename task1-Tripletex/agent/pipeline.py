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
from datetime import date
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
INDEX_MD = (SPECS_DIR / "index_slim.md").read_text()
REGISTRY_PATH = SPECS_DIR / "registry.json"
KNOWLEDGE_BASE = (Path(__file__).parent / "knowledgebase.md").read_text()


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


# ── Step 1+2: Translate & Rewrite (merged) ───────────────────────────────────

translate_rewrite_agent = Agent(
    name="TranslateRewrite",
    model=model,
    instructions=(
        "You translate and clarify accounting task prompts.\n\n"
        "The input may be in Norwegian, Nynorsk, English, Spanish, Portuguese, German, or French.\n\n"
        "Do TWO things in one step:\n"
        "1. Translate the instruction words to English (keep data values unchanged)\n"
        "2. Clarify the result into a structured format\n\n"
        "CRITICAL — Data values must NEVER be translated or changed:\n"
        "- Names in quotes ('Buchhaltung', 'Servicio de Consultoría') → keep EXACTLY\n"
        "- Person names, company names, product names, department names → keep EXACTLY\n"
        "- Emails, numbers, dates, currency amounts, org numbers → keep EXACTLY\n"
        "- Norwegian characters (æ, ø, å) → keep EXACTLY\n\n"
        "Output format:\n"
        "Task: [one sentence summary in English]\n"
        "Entities: [entity type (field: \"value\", ...), ...]\n"
        "Actions: [what needs to happen]\n"
        "Prerequisites: [what must exist first, or \"none\"]"
    ),
)


async def step1_translate_rewrite(raw_prompt: str, trace: PipelineTrace) -> str:
    """Translate and clarify in one LLM call. Sees ONLY the raw prompt."""
    start = time.monotonic()
    result = await Runner.run(translate_rewrite_agent, input=raw_prompt)
    clarified = result.final_output
    trace.add(StepTrace(
        step=1,
        name="TRANSLATE_REWRITE",
        input=raw_prompt,
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
        "1. FIRST: Check the KNOWLEDGE BASE below — it has proven workflows for common task types.\n"
        "   If the task matches a known workflow, FOLLOW IT EXACTLY.\n"
        "2. If no knowledge base match, scan the endpoint index to identify relevant endpoints.\n"
        "3. Use the lookup_endpoint tool to check schemas for fields and _ref dependencies.\n"
        "4. Build a MINIMAL plan — only the steps actually needed.\n\n"
        "<knowledge_base>\n"
        f"{KNOWLEDGE_BASE}\n"
        "</knowledge_base>\n\n"
        "<endpoint_index>\n"
        f"{INDEX_MD}\n"
        "</endpoint_index>\n\n"
        "Rules:\n"
        f"- Today's date is {date.today().isoformat()}. Use this for all date fields unless the task specifies otherwise.\n"
        "- FOLLOW the knowledge base workflows when they match the task\n"
        "- For employee creation: ONLY plan GET /department + POST /employee + PUT entitlement + POST employment (if startDate). Do NOT add GET /country or GET /employee/category.\n"
        "- Only add prerequisite GET steps for _ref fields that are actually needed\n"
        "- Each step must map to exactly ONE API call\n"
        "- Include the HTTP method and path for each step\n"
        "- Mark dependencies with 'depends on: Step N'\n"
        "- Do NOT include authentication details\n"
        "- KEEP THE PLAN MINIMAL — fewer API calls = higher score\n\n"
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
    result = await Runner.run(decomposer_agent, input=clarified_text, max_turns=5)
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
    """Run Steps 1-3: translate+rewrite → decompose → format.

    No credentials or files touch this function — those go straight to the executor.
    """
    trace = PipelineTrace()

    clarified = await step1_translate_rewrite(prompt, trace)
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
