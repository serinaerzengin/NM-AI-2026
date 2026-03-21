import base64
import csv
import io


async def process_files(files: list) -> list:
    """Process files into OpenAI-compatible content parts."""
    parts = []
    for f in files:
        filename = f.get("filename", "unknown")
        content_b64 = f.get("content_base64", "")
        mime_type = f.get("mime_type", "application/octet-stream")

        if not content_b64:
            continue

        lower = filename.lower()

        if lower.endswith(".csv"):
            try:
                raw = base64.b64decode(content_b64).decode("utf-8", errors="replace")
                reader = csv.reader(io.StringIO(raw))
                rows = list(reader)
                # Format as text table
                if rows:
                    text = f"=== CSV File: {filename} ===\n"
                    for i, row in enumerate(rows[:200]):  # cap at 200 rows
                        text += " | ".join(str(c) for c in row) + "\n"
                    if len(rows) > 200:
                        text += f"... ({len(rows) - 200} more rows)\n"
                    parts.append({"type": "text", "text": text})
            except Exception as e:
                parts.append({"type": "text", "text": f"Error reading CSV {filename}: {e}"})

        elif lower.endswith(".xlsx") or lower.endswith(".xls"):
            try:
                import openpyxl
                raw = base64.b64decode(content_b64)
                wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True)
                text = f"=== Excel File: {filename} ===\n"
                for sheet_name in wb.sheetnames:
                    ws = wb[sheet_name]
                    text += f"\n--- Sheet: {sheet_name} ---\n"
                    for i, row in enumerate(ws.iter_rows(values_only=True)):
                        if i >= 200:
                            text += "... (more rows)\n"
                            break
                        text += " | ".join(str(c) if c is not None else "" for c in row) + "\n"
                wb.close()
                parts.append({"type": "text", "text": text})
            except Exception as e:
                parts.append({"type": "text", "text": f"Error reading Excel {filename}: {e}"})

        elif mime_type.startswith("image/") or lower.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
            data_url = f"data:{mime_type};base64,{content_b64}"
            parts.append({"type": "image_url", "image_url": {"url": data_url}})

        elif lower.endswith(".pdf") or mime_type == "application/pdf":
            # Send PDF as image for Gemini vision
            data_url = f"data:application/pdf;base64,{content_b64}"
            parts.append({"type": "image_url", "image_url": {"url": data_url}})

        else:
            # Try as text
            try:
                raw = base64.b64decode(content_b64).decode("utf-8", errors="replace")
                parts.append({"type": "text", "text": f"=== File: {filename} ===\n{raw[:5000]}"})
            except Exception:
                parts.append({"type": "text", "text": f"[Binary file: {filename}, cannot display]"})

    return parts
