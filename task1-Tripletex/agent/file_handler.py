"""Handles file attachments from /solve requests (PDFs, images, text files)."""

import base64


def decode_files(files: list[dict]) -> list[dict]:
    """Decode base64 file content into processed file dicts."""
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
    """Prepare decoded files as LLM content blocks (OpenAI vision format)."""
    parts = []
    for f in files:
        if f["is_image"] or f["is_pdf"]:
            b64 = base64.b64encode(f["content_bytes"]).decode()
            parts.append({"type": "text", "text": f"[File: {f['filename']}]"})
            parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:{f['mime_type']};base64,{b64}"},
            })
        else:
            try:
                text = f["content_bytes"].decode("utf-8")
            except UnicodeDecodeError:
                text = f["content_bytes"].decode("latin-1")
            parts.append({"type": "text", "text": f"[File: {f['filename']}]\n{text}"})
    return parts
