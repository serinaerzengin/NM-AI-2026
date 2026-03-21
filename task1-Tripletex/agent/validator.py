"""Pre-validates payloads against registry schemas before sending to Tripletex."""

from agent.context import get_endpoint

TYPE_CHECKS = {
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "int64": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
}


def _validate_fields(payload: dict, properties: dict, required: list | None,
                     path: str, errors: list, warnings: list):
    if required:
        for field in required:
            if field in properties and field not in payload:
                fp = f"{path}.{field}" if path else field
                errors.append(f"'{fp}': required field missing")

    for field, value in payload.items():
        fp = f"{path}.{field}" if path else field

        if field not in properties:
            warnings.append(f"'{fp}': unknown field")
            continue

        schema = properties[field]
        expected = schema.get("type")
        if not expected:
            continue

        # Skip unresolved $placeholders
        if isinstance(value, str) and value.startswith("$"):
            continue

        checker = TYPE_CHECKS.get(expected)
        if checker and not checker(value):
            errors.append(f"'{fp}': expected {expected}, got {type(value).__name__}")
            continue

        enum_values = schema.get("enum")
        if enum_values and isinstance(value, str) and value not in enum_values:
            errors.append(f"'{fp}': '{value}' not in {enum_values}")

        if expected == "object" and isinstance(value, dict) and "properties" in schema:
            _validate_fields(value, schema["properties"], schema.get("required"),
                             fp, errors, warnings)

        if expected == "array" and isinstance(value, list) and "items" in schema:
            items_schema = schema["items"]
            if isinstance(items_schema, dict) and items_schema.get("type") == "object" \
               and "properties" in items_schema:
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        _validate_fields(item, items_schema["properties"],
                                         items_schema.get("required"),
                                         f"{fp}[{i}]", errors, warnings)


def validate_payload(registry: dict, method: str, path: str, payload: dict) -> dict:
    """Validate request payload. Returns {"errors": [...], "warnings": [...]}."""
    endpoint = get_endpoint(registry, method, path)
    if not endpoint:
        return {"errors": [f"Unknown endpoint: {method} {path}"], "warnings": []}

    body_schema = endpoint.get("request_body")
    if not body_schema or "properties" not in body_schema:
        if body_schema and body_schema.get("content_type") == "multipart/form-data":
            return {"errors": ["Endpoint uses multipart — use file upload, not JSON"], "warnings": []}
        return {"errors": [], "warnings": []}

    errors: list[str] = []
    warnings: list[str] = []
    _validate_fields(payload, body_schema["properties"], body_schema.get("required"),
                     "", errors, warnings)
    return {"errors": errors, "warnings": warnings}
