"""Step 4: save invoices in a SQLite file."""
import os
import sqlite3

from config import DB_PATH

FIELDS = [
    "vendor", "invoice_number", "invoice_date", "due_date", "gstin", "hsn_sac",
    "subtotal", "cgst", "sgst", "igst", "tax", "total",
    "category", "payment_status", "needs_review", "review_notes", "file_name",
]


def connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us read rows like dictionaries
    return conn


def init_db():
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor TEXT, invoice_number TEXT, invoice_date TEXT, due_date TEXT,
                gstin TEXT, hsn_sac TEXT,
                subtotal REAL, cgst REAL, sgst REAL, igst REAL, tax REAL, total REAL,
                category TEXT, payment_status TEXT, needs_review INTEGER,
                review_notes TEXT, file_name TEXT
            )
        """)


def add_invoice(record):
    columns = ", ".join(FIELDS)
    placeholders = ", ".join("?" for _ in FIELDS)
    values = [record.get(f) for f in FIELDS]
    with connect() as conn:
        conn.execute(f"INSERT INTO invoices ({columns}) VALUES ({placeholders})", values)


def get_all():
    with connect() as conn:
        rows = conn.execute("SELECT * FROM invoices ORDER BY id DESC").fetchall()
    return [dict(row) for row in rows]


def mark_paid(invoice_id):
    with connect() as conn:
        conn.execute("UPDATE invoices SET payment_status = 'Paid' WHERE id = ?", (invoice_id,))


def delete_invoice(invoice_id):
    with connect() as conn:
        conn.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
