"""Step 3: do not blindly trust the AI. Check the numbers and flag problems."""
import re
from datetime import datetime

GSTIN_PATTERN = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")


def is_valid_date(value):
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False


def amount_in_text(amount, text):
    """Is this amount really written somewhere in the document?"""
    text = text.replace(",", "")
    return f"{amount:.2f}" in text or str(int(amount)) in text


def check_invoice(data, raw_text=""):
    """Return a list of problems. An empty list means it looks fine."""
    notes = []

    if not data.get("vendor"):
        notes.append("Vendor is missing.")
    if not data.get("invoice_number"):
        notes.append("Invoice number is missing.")
    if not is_valid_date(data.get("invoice_date")):
        notes.append("Invoice date is missing or not in YYYY-MM-DD format.")
    if data.get("due_date") and not is_valid_date(data["due_date"]):
        notes.append("Due date is not in YYYY-MM-DD format.")

    total = data.get("total") or 0
    subtotal = data.get("subtotal") or 0
    tax = data.get("tax") or 0

    if total <= 0:
        notes.append("Total must be greater than 0.")
    else:
        if subtotal > 0 and abs(subtotal + tax - total) > 1:
            notes.append(f"Subtotal + tax ({subtotal + tax:.2f}) does not match total ({total:.2f}).")
        if raw_text and not amount_in_text(total, raw_text):
            notes.append("Total was not found in the document text. The AI may have misread it.")

    gstin = data.get("gstin")
    if gstin and not GSTIN_PATTERN.match(gstin):
        notes.append("GSTIN does not look valid.")

    if abs((data.get("cgst") or 0) - (data.get("sgst") or 0)) > 0.01:
        notes.append("CGST and SGST are normally equal.")

    return notes
