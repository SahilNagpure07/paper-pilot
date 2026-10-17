"""Step 5: the useful stuff. Duplicates, overdue flags, search, bank matching, CSV."""
import csv
import io
from datetime import date


def _clean(text):
    return (text or "").strip().lower()


def find_duplicate(record, existing_rows):
    """Return the saved invoice that looks the same as this one, or None."""
    for row in existing_rows:
        same_vendor = _clean(row["vendor"]) == _clean(record["vendor"])
        if not same_vendor:
            continue
        same_number = record["invoice_number"] and _clean(row["invoice_number"]) == _clean(record["invoice_number"])
        same_details = row["total"] == record["total"] and row["invoice_date"] == record["invoice_date"]
        if same_number or same_details:
            return row
    return None


def add_status(rows, today=None):
    """Add a 'status' field: Paid, Overdue or Unpaid."""
    today = (today or date.today()).isoformat()
    for row in rows:
        if row["payment_status"] == "Paid":
            row["status"] = "Paid"
        elif row["due_date"] and row["due_date"] < today:  # ISO dates compare correctly as text
            row["status"] = "Overdue"
        else:
            row["status"] = "Unpaid"
    return rows


def search(rows, text="", category="All", status="All"):
    text = _clean(text)
    result = []
    for row in rows:
        if text and text not in _clean(row["vendor"]) and text not in _clean(row["invoice_number"]):
            continue
        if category != "All" and row["category"] != category:
            continue
        if status != "All" and row["status"] != status:
            continue
        result.append(row)
    return result


def summary(rows):
    """Numbers for the dashboard. Rows must already have 'status'."""
    return {
        "count": len(rows),
        "total": sum(r["total"] or 0 for r in rows),
        "gst": sum(r["tax"] or 0 for r in rows),
        "unpaid": sum(r["total"] or 0 for r in rows if r["status"] != "Paid"),
        "overdue": sum(1 for r in rows if r["status"] == "Overdue"),
        "review": sum(1 for r in rows if r["needs_review"]),
    }


def match_bank_amounts(rows, amounts):
    """Find unpaid invoices whose total appears in the bank statement.
    Each bank amount can only match one invoice."""
    remaining = list(amounts)
    matched_ids = []
    for row in rows:
        if row["status"] == "Paid":
            continue
        for amount in remaining:
            if abs(amount - (row["total"] or 0)) < 0.01:
                matched_ids.append(row["id"])
                remaining.remove(amount)
                break
    return matched_ids


def to_csv(rows):
    if not rows:
        return ""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()
