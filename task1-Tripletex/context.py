"""Loads the API registry and provides endpoint lookup for the LLM."""

import json
from pathlib import Path

REGISTRY_PATH = Path(__file__).parent / "specs" / "registry.json"
INDEX_PATH = Path(__file__).parent / "specs" / "index.md"
DOMAIN_PATH = Path(__file__).parent / "specs" / "domain.md"


def load_registry(path: Path = REGISTRY_PATH) -> dict:
    """Load the full registry from disk."""
    with open(path) as f:
        return json.load(f)


def load_index() -> str:
    """Load the full endpoint index for the LLM planning phase."""
    return INDEX_PATH.read_text()


def load_domain() -> str:
    """Load domain knowledge for the LLM planning phase."""
    return DOMAIN_PATH.read_text()


def find_endpoints(registry: dict, query: str, limit: int = 15) -> list[dict]:
    """Search endpoints by keyword in key, summary, or tags. Returns ranked matches.

    Ranking: exact path match > key match > summary match > tag match.
    Limited to `limit` results (default 15).
    """
    query_lower = query.lower()
    scored = []
    for key, entry in registry.items():
        tags_str = " ".join(entry.get("tags", []))
        summary = entry.get("summary", "").lower()

        # Score by match quality
        if query_lower in key.lower().split()[-1]:  # exact path segment match
            score = 3
        elif query_lower in key.lower():
            score = 2
        elif query_lower in summary:
            score = 1
        elif query_lower in tags_str.lower():
            score = 0
        else:
            continue

        scored.append((score, key, entry))

    scored.sort(key=lambda x: -x[0])
    return [{"key": k, **e} for _, k, e in scored[:limit]]


def get_endpoint(registry: dict, method: str, path: str) -> dict | None:
    """Get a specific endpoint entry by method and path.

    e.g. get_endpoint(registry, "POST", "/customer")
    """
    key = f"{method.upper()} {path}"
    entry = registry.get(key)
    if entry:
        return {"key": key, **entry}
    return None


def _format_field(name: str, info: dict, indent: int = 4) -> list[str]:
    """Format a single field, recursing into objects and array items."""
    prefix = " " * indent
    ftype = info.get("type", "?")
    ref = info.get("_ref")
    enum = info.get("enum")

    if enum:
        if len(enum) <= 5:
            ftype = f"enum[{','.join(enum)}]"
        else:
            ftype = f"enum[{','.join(enum[:5])},... +{len(enum)-5} more]"
    if ref:
        ftype = f"object → {ref}"

    desc = info.get("description")
    if desc:
        parts = [f"{prefix}{name} ({ftype}) — {desc}"]
    else:
        parts = [f"{prefix}{name} ({ftype})"]

    # Show nested object properties
    if ftype.startswith("object") and "properties" in info:
        for sub_name, sub_info in info["properties"].items():
            parts.extend(_format_field(sub_name, sub_info, indent + 2))

    # Show array item properties
    if info.get("type") == "array" and "items" in info:
        items = info["items"]
        if isinstance(items, dict) and "properties" in items:
            arr_label = f"{prefix}{name} (array of objects)"
            if desc:
                arr_label += f" — {desc}"
            parts[0] = arr_label
            for sub_name, sub_info in items["properties"].items():
                parts.extend(_format_field(sub_name, sub_info, indent + 2))

    return parts


def schema_for_prompt(endpoint: dict) -> str:
    """Format an endpoint's schema as a readable string for LLM context."""
    lines = [endpoint["key"]]
    lines.append(f"  Summary: {endpoint.get('summary', 'N/A')}")

    body = endpoint.get("request_body")
    if body and "properties" in body:
        lines.append("  Body:")
        for name, info in body["properties"].items():
            lines.extend(_format_field(name, info))

    params = endpoint.get("query_params")
    if params:
        pfields = [f"{p['name']} ({p.get('type', '?')})" for p in params]
        lines.append(f"  Query: {', '.join(pfields)}")

    return "\n".join(lines)

