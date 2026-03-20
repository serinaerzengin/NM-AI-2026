"""Handles file attachments from the /solve request.

Files arrive as: {"filename": "faktura.pdf", "content_base64": "...", "mime_type": "application/pdf"}
This module decodes them and prepares them for the LLM (vision input) or Tripletex API (upload).
"""

import base64


def decode_files(files: list[dict]) -> list[dict]:
    """Decode base64 file content. Returns list of processed file dicts.

    Each result has:
      - filename, mime_type (from input)
      - content_bytes (decoded raw bytes)
      - is_image (bool)
      - is_pdf (bool)
    """
    result = []
    for f in files:
        raw = base64.b64decode(f["content_base64"])
        mime = f.get("mime_type", "")
        result.append({
            "filename": f["filename"],
            "mime_type": mime,
            "content_bytes": raw,
            "is_image": mime.startswith("image/"),
            "is_pdf": mime == "application/pdf",
        })
    return result


def files_for_llm(files: list[dict]) -> list[dict]:
    """Prepare decoded files as LLM content blocks (OpenAI format).

    Images/PDFs → text label + inline base64 image_url content blocks.
    Text-based files (txt, csv, json, xml, etc.) → text content blocks.
    """
    parts = []
    for f in files:
        if f["is_image"] or f["is_pdf"]:
            mime = f["mime_type"]
            b64 = base64.b64encode(f["content_bytes"]).decode()
            parts.append({"type": "text", "text": f"[File: {f['filename']}]"})
            parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{b64}"},
            })
        else:
            # Text-based file — decode and include as text
            try:
                text_content = f["content_bytes"].decode("utf-8")
            except UnicodeDecodeError:
                text_content = f["content_bytes"].decode("latin-1")
            parts.append({
                "type": "text",
                "text": f"[File: {f['filename']}]\n{text_content}",
            })

    return parts


def files_for_upload(files: list[dict]) -> list[tuple[str, bytes, str]]:
    """Prepare decoded files for Tripletex multipart upload.

    Returns list of (filename, content_bytes, mime_type) tuples.
    """
    return [(f["filename"], f["content_bytes"], f["mime_type"]) for f in files]
