"""Step 2: ask Gemma (an open-weight model, hosted via the Gemini API) to turn invoice text into fields."""
import json
import os
import re

from google import genai
from google.genai import types

from config import MODEL
from src.privacy import redact

PROMPT = """Extract invoice details from the text below.
Reply with ONLY a JSON object with exactly these keys:
vendor, invoice_number, invoice_date, due_date, gstin, hsn_sac, subtotal, cgst, sgst, igst, tax, total, category

Rules:
- Dates must be YYYY-MM-DD.
- Amounts must be plain numbers (no currency symbols or commas).
- Use "" for missing text and 0 for missing numbers.
- vendor is the company that SENT the invoice.
- gstin is the vendor's 15-character GST number.
- tax is the total tax (CGST + SGST + IGST).

Invoice text:
{text}
"""

NUMBER_KEYS = ["subtotal", "cgst", "sgst", "igst", "tax", "total"]
TEXT_KEYS = ["vendor", "invoice_number", "invoice_date", "due_date", "gstin", "hsn_sac", "category"]
GSTIN_REGEX = r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b"


def extract_fields(text):
    """Return a dict of invoice fields. Raises an error if the API call fails."""
    prompt = redact(PROMPT.format(text=text[:3000]))  # personal details removed before sending
    return clean_up(parse_json(ask_gemma(prompt)), text)


def ask_gemma(prompt):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "paste-your-key-here":
        raise RuntimeError("GEMINI_API_KEY is missing. Add it to the .env file.")
    client = genai.Client(api_key=api_key)

    try:  # ask for JSON mode first
        config = types.GenerateContentConfig(temperature=0, response_mime_type="application/json")
        response = client.models.generate_content(model=MODEL, contents=prompt, config=config)
    except Exception:  # some models do not support JSON mode, so retry with a plain request
        config = types.GenerateContentConfig(temperature=0)
        response = client.models.generate_content(model=MODEL, contents=prompt, config=config)
    return response.text


def parse_json(answer):
    """Models sometimes wrap JSON in ```json fences or add a sentence. Pull out the {...} part."""
    start, end = answer.find("{"), answer.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("The model did not return JSON")
    return json.loads(answer[start:end + 1])


def clean_up(data, text):
    """Small fixes that do not need AI."""
    result = {}
    for key in TEXT_KEYS:
        result[key] = str(data.get(key) or "").strip()
    for key in NUMBER_KEYS:
        try:
            result[key] = float(str(data.get(key) or 0).replace(",", ""))
        except ValueError:
            result[key] = 0.0

    # A regex finds the GSTIN more reliably than a model.
    if not result["gstin"]:
        found = re.search(GSTIN_REGEX, text)
        result["gstin"] = found.group(0) if found else ""

    # If the model gave CGST/SGST/IGST but no total tax, add them up.
    if not result["tax"]:
        result["tax"] = round(result["cgst"] + result["sgst"] + result["igst"], 2)

    return result
