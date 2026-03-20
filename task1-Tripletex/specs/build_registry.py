#!/usr/bin/env python3
"""
build_registry.py — Generate index.md and registry.json from the Tripletex OpenAPI spec.

Generates two files:

1. index.md (The Index): markdown table of ALL endpoints (method, path, one-line summary).
   
2. registry.json (The Registry): structured JSON file keyed by "METHOD /path" (e.g. "POST /employee").
   Each value contains the fully resolved request body schema (field names, types, formats, enums, nested objects)
    and query parameters — everything needed to construct a valid API call without guessing.

Usage:
    python specs/build_registry.py

Reads:  specs/openapi.json
Writes: specs/index.md, specs/registry.json
"""

from __future__ import annotations

import json
from pathlib import Path

SPEC_PATH = Path(__file__).parent / "openapi.json"
INDEX_OUT = Path(__file__).parent / "index.md"
REGISTRY_OUT = Path(__file__).parent / "registry.json"

HTTP_METHODS = {"get", "post", "put", "delete", "patch"}

# Fields that are meta/internal and never useful in request bodies.
# id and version are server-assigned but NOT marked readOnly in the spec,
# so we strip them explicitly to avoid confusing the agent.
STRIP_FIELDS = {"changes", "url", "id", "version"}


def load_spec() -> dict:
    with open(SPEC_PATH) as f:
        return json.load(f)


# ── Schema resolver ──────────────────────────────────────────────────
# The OpenAPI spec uses $ref pointers everywhere (e.g. "$ref": "#/components/schemas/Employee").
# We need to follow these pointers and inline the actual schema so the registry
# is self-contained — the agent should never need to look up a reference.


def resolve_ref(ref: str, schemas: dict) -> tuple[dict, str]:
    """Resolve a $ref string like '#/components/schemas/Employee' to its schema dict."""
    name = ref.split("/")[-1]
    return schemas.get(name, {}), name


def resolve_schema(
    schema: dict,
    schemas: dict,
    depth: int = 0,
    max_depth: int = 3,
    seen: set | None = None,
) -> dict:
    """
    Recursively resolve a JSON schema into a flat, self-contained dict.

    - Follows $ref pointers up to max_depth (3) to avoid infinite recursion
      on circular references (e.g. Employee -> Department -> Employee)
    - Preserves: type, format, enum, description, nested properties
    - For array items with $ref, resolves the item schema
    - Beyond max_depth, leaves a stub with just the ref name
    """
    if seen is None:
        seen = set()

    # Follow $ref pointer
    if "$ref" in schema:
        resolved, ref_name = resolve_ref(schema["$ref"], schemas)
        if ref_name in seen or depth >= max_depth:
            # Circular or too deep — leave a reference stub
            return {"type": "object", "$ref": ref_name, "_note": "circular/deep — ref only"}
        seen = seen | {ref_name}
        return resolve_schema(resolved, schemas, depth + 1, max_depth, seen)

    result: dict = {}

    if schema.get("type"):
        result["type"] = schema["type"]
    if schema.get("format"):
        result["format"] = schema["format"]
    if schema.get("enum"):
        result["enum"] = schema["enum"]
    if schema.get("description"):
        desc = schema["description"]
        if len(desc) > 300:
            desc = desc[:297] + "..."
        result["description"] = desc
    if schema.get("readOnly"):
        result["readOnly"] = True

    # Object with properties — resolve each property recursively
    if "properties" in schema:
        props = {}
        for prop_name, prop_schema in schema["properties"].items():
            if prop_name in STRIP_FIELDS:
                continue
            props[prop_name] = resolve_schema(prop_schema, schemas, depth + 1, max_depth, seen)
        result["properties"] = props
        if schema.get("required"):
            result["required"] = schema["required"]

    # Array items — resolve the item schema
    if schema.get("type") == "array" and "items" in schema:
        result["items"] = resolve_schema(schema["items"], schemas, depth + 1, max_depth, seen)

    # Union types
    for keyword in ("oneOf", "anyOf", "allOf"):
        if keyword in schema:
            result[keyword] = [
                resolve_schema(s, schemas, depth + 1, max_depth, seen)
                for s in schema[keyword]
            ]

    return result


def strip_readonly(schema: dict) -> dict | None:
    """
    Remove readOnly properties from a resolved schema tree.
    readOnly fields are server-generated (id, version, displayName, etc.)
    and must never be sent in POST/PUT request bodies.
    Stripping them gives the agent a clean view of only the fields it can set.
    """
    if schema.get("readOnly"):
        return None

    result = {}
    for k, v in schema.items():
        if k == "properties" and isinstance(v, dict):
            cleaned = {}
            for prop_name, prop_schema in v.items():
                stripped = strip_readonly(prop_schema)
                if stripped is not None:
                    cleaned[prop_name] = stripped
            if cleaned:
                result["properties"] = cleaned
        elif k == "items" and isinstance(v, dict):
            stripped = strip_readonly(v)
            result["items"] = stripped if stripped is not None else v
        else:
            result[k] = v

    return result


# ── Query parameter extraction ───────────────────────────────────────


def extract_query_params(parameters: list[dict]) -> list[dict]:
    """
    Extract query parameters from an endpoint's parameter list.
    These are the ?key=value params used for filtering/searching on GET endpoints
    (e.g. GET /employee?firstName=Ola&fields=id,firstName,lastName).
    """
    params = []
    for p in parameters:
        if p.get("in") != "query":
            continue
        param: dict = {"name": p["name"]}
        s = p.get("schema", {})
        if s.get("type"):
            param["type"] = s["type"]
        if s.get("format"):
            param["format"] = s["format"]
        if s.get("enum"):
            param["enum"] = s["enum"]
        if s.get("default") is not None:
            param["default"] = s["default"]
        desc = p.get("description", "")
        if desc:
            if len(desc) > 200:
                desc = desc[:197] + "..."
            param["description"] = desc
        if p.get("required"):
            param["required"] = True
        params.append(param)
    return params


# ── Response schema extraction ───────────────────────────────────────


def extract_response_schema(responses: dict, schemas: dict) -> dict | None:
    """
    Extract a lightweight description of the success response (200/201).
    Tripletex wraps responses in ResponseWrapper* (single entity) or
    ListResponse* (list of entities). We record the pattern so the agent
    knows whether to expect .value or .values in the response.
    """
    for code in ("200", "201"):
        resp = responses.get(code, {})
        content = resp.get("content", {})
        for content_type, media in content.items():
            schema = media.get("schema", {})
            resolved = resolve_schema(schema, schemas, depth=0, max_depth=1)
            props = resolved.get("properties", {})
            ref_name = schema.get("$ref", "").split("/")[-1] if "$ref" in schema else None
            if "value" in props:
                return {"type": "single", "schema_ref": ref_name}
            elif "values" in props:
                return {"type": "list", "schema_ref": ref_name}
            return resolved
    return None


# ── Main builders ────────────────────────────────────────────────────


def build_index_and_registry(spec: dict) -> tuple[str, dict]:
    paths = spec.get("paths", {})
    schemas = spec.get("components", {}).get("schemas", {})

    index_lines = [
        "# Tripletex API — Endpoint Index",
        "",
        "Lightweight lookup table of every API endpoint.",
        "Use this to identify which endpoints are needed for a task,",
        "then pull detailed schemas from registry.json.",
        "",
        "| Method | Path | Summary |",
        "|--------|------|---------|",
    ]

    registry: dict = {}

    for path in sorted(paths.keys()):
        methods = paths[path]
        for method in sorted(methods.keys()):
            if method not in HTTP_METHODS:
                continue
            details = methods[method]
            summary = details.get("summary", details.get("description", ""))
            summary = summary.replace("\n", " ").strip()
            if len(summary) > 120:
                summary = summary[:117] + "..."

            key = f"{method.upper()} {path}"

            # ── Index: one line per endpoint ──
            index_lines.append(f"| {method.upper()} | `{path}` | {summary} |")

            # ── Registry: full structured detail ──
            entry: dict = {"summary": summary}

            if details.get("tags"):
                entry["tags"] = details["tags"]

            # Query parameters (for GET, DELETE, etc.)
            params = details.get("parameters", [])
            query_params = extract_query_params(params)
            if query_params:
                entry["query_params"] = query_params

            # Request body schema (for POST, PUT, PATCH)
            # Resolved inline with readOnly fields stripped
            if "requestBody" in details:
                content = details["requestBody"].get("content", {})
                for content_type, media in content.items():
                    body_schema = media.get("schema", {})
                    resolved = resolve_schema(body_schema, schemas, depth=0, max_depth=3)
                    cleaned = strip_readonly(resolved)
                    if cleaned:
                        entry["request_body"] = cleaned
                    break

            # Response shape (single vs list, schema ref name)
            if "responses" in details:
                resp_info = extract_response_schema(details["responses"], schemas)
                if resp_info:
                    entry["response"] = resp_info

            registry[key] = entry

    index_md = "\n".join(index_lines) + "\n"
    return index_md, registry


def main():
    print(f"Loading spec from {SPEC_PATH}...")
    spec = load_spec()

    print("Building index and registry...")
    index_md, registry = build_index_and_registry(spec)

    INDEX_OUT.write_text(index_md)
    print(f"  index.md — {len(index_md.splitlines())} lines")

    registry_json = json.dumps(registry, indent=2, ensure_ascii=False)
    REGISTRY_OUT.write_text(registry_json)

    total = len(registry)
    with_body = sum(1 for v in registry.values() if "request_body" in v)
    with_params = sum(1 for v in registry.values() if "query_params" in v)
    size_kb = len(registry_json) / 1024

    print(f"  registry.json — {total} endpoints, {size_kb:.0f} KB")
    print(f"    {with_body} with request_body, {with_params} with query_params")


if __name__ == "__main__":
    main()
