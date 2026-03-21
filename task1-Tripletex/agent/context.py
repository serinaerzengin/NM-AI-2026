"""Registry loading and endpoint schema rendering."""

import json
from pathlib import Path

REGISTRY_PATH = Path(__file__).parent.parent / "specs" / "registry.json"


def load_registry(path: Path = REGISTRY_PATH) -> dict:
    with open(path) as f:
        return json.load(f)


def get_endpoint(registry: dict, method: str, path: str) -> dict | None:
    """Get endpoint entry by method and path, e.g. get_endpoint(reg, "POST", "/customer")."""
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
        ftype = f"enum[{','.join(enum[:5])}]" if len(enum) <= 5 else f"enum[{','.join(enum[:5])},...]"
    if ref:
        ftype = f"object → {ref}"

    desc = info.get("description")
    line = f"{prefix}{name} ({ftype})"
    if desc:
        line += f" — {desc}"
    parts = [line]

    if ftype.startswith("object") and "properties" in info:
        for sub, sub_info in info["properties"].items():
            parts.extend(_format_field(sub, sub_info, indent + 2))

    if info.get("type") == "array" and "items" in info:
        items = info["items"]
        if isinstance(items, dict) and "properties" in items:
            for sub, sub_info in items["properties"].items():
                parts.extend(_format_field(sub, sub_info, indent + 2))

    return parts


def schema_for_prompt(endpoint: dict) -> str:
    """Format an endpoint's schema as readable text for LLM context."""
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
