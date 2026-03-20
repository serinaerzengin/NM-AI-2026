#!/usr/bin/env python3
"""
build_registry.py — Extract index.md and registry.json from the Tripletex OpenAPI spec.

Reads:  specs/openapi.json
Writes: specs/index.md, specs/registry.json
"""

from __future__ import annotations

import json
import re
from pathlib import Path

SPEC_PATH = Path(__file__).parent / "openapi.json"
INDEX_OUT = Path(__file__).parent / "index.md"
REGISTRY_OUT = Path(__file__).parent / "registry.json"

HTTP_METHODS = {"get", "post", "put", "delete", "patch"}

# Server-assigned fields that should never appear in request bodies
STRIP_FIELDS = {"changes", "url", "id", "version"}

# Stub for linked entities and circular refs — Tripletex only needs {"id": <int>}
LINKED_ENTITY_STUB = {
    "type": "object",
    "properties": {
        "id": {"type": "integer", "format": "int64", "description": "ID of the linked entity"}
    },
}


def load_spec() -> dict:
    with open(SPEC_PATH) as f:
        return json.load(f)


def resolve_ref(ref: str, schemas: dict) -> tuple[dict, str]:
    name = ref.split("/")[-1]
    return schemas.get(name, {}), name


def resolve_schema(
    schema: dict,
    schemas: dict,
    depth: int = 0,
    ancestors: frozenset[str] | None = None,
) -> dict:
    """
    Resolve a JSON schema with object-vs-array branching:
      depth=0: resolve fully (root payload or array items)
      depth>=1: stub object $refs to id-only, resolve array items at depth=0
    Circular refs detected via ancestors set and stubbed to id-only.
    """
    if ancestors is None:
        ancestors = frozenset()

    if "$ref" in schema:
        resolved, ref_name = resolve_ref(schema["$ref"], schemas)

        if ref_name in ancestors:
            return {**LINKED_ENTITY_STUB, "_ref": ref_name}
        if not resolved:
            return {"type": "object", "_missing_ref": ref_name}
        if depth >= 1:
            return {**LINKED_ENTITY_STUB, "_ref": ref_name}

        return resolve_schema(resolved, schemas, depth, ancestors | {ref_name})

    result: dict = {}

    if schema.get("type"):
        result["type"] = schema["type"]
    if schema.get("format"):
        result["format"] = schema["format"]
    if schema.get("enum"):
        result["enum"] = schema["enum"]
    if schema.get("description"):
        desc = schema["description"]
        result["description"] = desc[:297] + "..." if len(desc) > 300 else desc
    # Only propagate readOnly on leaf properties, not schema-level objects
    if schema.get("readOnly") and "properties" not in schema:
        result["readOnly"] = True

    if "properties" in schema:
        props = {}
        for prop_name, prop_schema in schema["properties"].items():
            if prop_name in STRIP_FIELDS:
                continue
            props[prop_name] = resolve_schema(prop_schema, schemas, depth + 1, ancestors)
        result["properties"] = props
        if schema.get("required"):
            result["required"] = schema["required"]

    # Array items resolve at depth=0 — they're inline child creations, not entity links
    if schema.get("type") == "array" and "items" in schema:
        result["items"] = resolve_schema(schema["items"], schemas, 0, ancestors)

    for keyword in ("oneOf", "anyOf", "allOf"):
        if keyword in schema:
            result[keyword] = [resolve_schema(s, schemas, depth, ancestors) for s in schema[keyword]]

    return result


def strip_readonly(schema: dict) -> dict | None:
    """Remove readOnly properties from a resolved schema tree."""
    if schema.get("readOnly"):
        return None

    result = {}
    for k, v in schema.items():
        if k == "properties" and isinstance(v, dict):
            cleaned = {pn: ps for pn, pv in v.items() if (ps := strip_readonly(pv)) is not None}
            if cleaned:
                result["properties"] = cleaned
        elif k == "items" and isinstance(v, dict):
            stripped = strip_readonly(v)
            result["items"] = stripped if stripped is not None else v
        else:
            result[k] = v
    return result


def extract_query_params(parameters: list[dict]) -> list[dict]:
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
            param["description"] = desc[:197] + "..." if len(desc) > 200 else desc
        if p.get("required"):
            param["required"] = True
        params.append(param)
    return params


def extract_response_schema(responses: dict, schemas: dict) -> dict | None:
    for code in ("200", "201"):
        resp = responses.get(code, {})
        for _, media in resp.get("content", {}).items():
            schema = media.get("schema", {})
            resolved = resolve_schema(schema, schemas)
            props = resolved.get("properties", {})
            ref_name = schema.get("$ref", "").split("/")[-1] if "$ref" in schema else None
            if "value" in props:
                return {"type": "single", "schema_ref": ref_name}
            if "values" in props:
                return {"type": "list", "schema_ref": ref_name}
            return resolved
    return None


def build_index_and_registry(spec: dict) -> tuple[str, dict]:
    paths = spec.get("paths", {})
    schemas = spec.get("components", {}).get("schemas", {})

    index_lines = [
        "# Tripletex API — Endpoint Index",
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
            summary = details.get("summary", details.get("description", "")).replace("\n", " ").strip()
            if len(summary) > 200:
                summary = summary[:197] + "..."

            key = f"{method.upper()} {path}"
            index_lines.append(f"| {method.upper()} | `{path}` | {summary} |")

            entry: dict = {"summary": summary}
            if details.get("tags"):
                entry["tags"] = details["tags"]

            query_params = extract_query_params(details.get("parameters", []))
            if query_params:
                entry["query_params"] = query_params

            if "requestBody" in details:
                content = details["requestBody"].get("content", {})

                if "multipart/form-data" in content:
                    form_schema = content["multipart/form-data"].get("schema", {})
                    form_props = {}
                    for prop_name, prop_val in form_schema.get("properties", {}).items():
                        if prop_val.get("format") == "binary":
                            form_props[prop_name] = {"type": "binary", "description": prop_val.get("description", "File upload")}
                        else:
                            field: dict = {}
                            if prop_val.get("type"):
                                field["type"] = prop_val["type"]
                            if prop_val.get("description"):
                                field["description"] = prop_val["description"]
                            if prop_val.get("enum"):
                                field["enum"] = prop_val["enum"]
                            form_props[prop_name] = field
                    if form_props:
                        entry["request_body"] = {"content_type": "multipart/form-data", "properties": form_props}
                        if form_schema.get("required"):
                            entry["request_body"]["required"] = form_schema["required"]
                else:
                    for _, media in content.items():
                        resolved = resolve_schema(media.get("schema", {}), schemas)
                        cleaned = strip_readonly(resolved)
                        if cleaned:
                            entry["request_body"] = cleaned
                        break

            if "responses" in details:
                resp_info = extract_response_schema(details["responses"], schemas)
                if resp_info:
                    entry["response"] = resp_info

            registry[key] = entry

    return "\n".join(index_lines) + "\n", registry


def main():
    spec = load_spec()
    index_md, registry = build_index_and_registry(spec)

    INDEX_OUT.write_text(index_md)
    registry_json = json.dumps(registry, indent=2, ensure_ascii=False)
    REGISTRY_OUT.write_text(registry_json)

    total = len(registry)
    with_body = sum(1 for v in registry.values() if "request_body" in v)
    with_params = sum(1 for v in registry.values() if "query_params" in v)
    print(f"index.md — {len(index_md.splitlines())} lines")
    print(f"registry.json — {total} endpoints, {len(registry_json) / 1024:.0f} KB")
    print(f"  {with_body} with request_body, {with_params} with query_params")
    print(f"  stubs: {registry_json.count('\"_ref\"')} | enums: {len(re.findall('\"enum\":', registry_json))} | missing: {registry_json.count('\"_missing_ref\"')}")


if __name__ == "__main__":
    main()
