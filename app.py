"""PaperPilot: a private invoice and expense assistant.
Run with:  streamlit run app.py
"""
import os

import pandas as pd
import streamlit as st

from config import CATEGORIES, DOCS_DIR, MODEL
from src import database, expenses
from src.extractor import extract_text
from src.llm import extract_fields
from src.validator import check_invoice

st.set_page_config(page_title="PaperPilot", page_icon="🧾", layout="wide")
database.init_db()
os.makedirs(DOCS_DIR, exist_ok=True)


def load_rows():
    return expenses.add_status(database.get_all())


# ---------------------------------------------------------------- Dashboard
def dashboard_page():
    st.header("Dashboard")
    rows = load_rows()
    s = expenses.summary(rows)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Invoices", s["count"])
    c2.metric("Total recorded", f"₹{s['total']:,.2f}")
    c3.metric("GST paid", f"₹{s['gst']:,.2f}")
    c4.metric("Still unpaid", f"₹{s['unpaid']:,.2f}")
    c5.metric("Overdue", s["overdue"])

    overdue = [r for r in rows if r["status"] == "Overdue"]
    if overdue:
        st.subheader("🔴 Overdue invoices")
        st.dataframe(pd.DataFrame(overdue)[["id", "vendor", "invoice_number", "due_date", "total"]],
                     hide_index=True, use_container_width=True)

    if s["review"]:
        st.warning(f"{s['review']} invoice(s) are flagged for review. See the Records page.")
    if not rows:
        st.info("No invoices yet. Go to 'Upload & Review' to add your first one.")


# ----------------------------------------------------------- Upload & Review
def upload_page():
    st.header("Upload & Review")
    st.caption(f"Powered by {MODEL}, an open-weight model. Personal details are redacted before text is sent.")

    file = st.file_uploader("Invoice or receipt (PDF)", type=["pdf"])
    col1, col2, _ = st.columns([1, 1, 4])

    if file and col1.button("Extract with AI"):
        with st.spinner("Reading document..."):
            try:
                text = extract_text(file.getvalue())
                st.session_state["text"] = text
                st.session_state["draft"] = extract_fields(text)
                st.session_state["draft_id"] = st.session_state.get("draft_id", 0) + 1
            except Exception as error:
                st.error(f"Could not extract: {error}. Make sure it is a digital PDF and GEMINI_API_KEY is set in the .env file. You can also type the details manually.")

    if col2.button("Enter manually"):
        st.session_state["text"] = ""
        st.session_state["draft"] = {}
        st.session_state["draft_id"] = st.session_state.get("draft_id", 0) + 1

    if "draft" in st.session_state:
        review_form(st.session_state["draft"], file)


def review_form(draft, file):
    key = st.session_state["draft_id"] 
    text = st.session_state.get("text", "")

    if text:
        with st.expander("Text read from the document"):
            st.text(text)

    st.subheader("Check the details, fix any mistakes, then save")
    with st.form("review_form"):
        c1, c2, c3 = st.columns(3)
        vendor = c1.text_input("Vendor", draft.get("vendor", ""), key=f"vendor{key}")
        number = c2.text_input("Invoice number", draft.get("invoice_number", ""), key=f"number{key}")
        gstin = c3.text_input("Vendor GSTIN", draft.get("gstin", ""), key=f"gstin{key}")

        c1, c2, c3 = st.columns(3)
        invoice_date = c1.text_input("Invoice date (YYYY-MM-DD)", draft.get("invoice_date", ""), key=f"idate{key}")
        due_date = c2.text_input("Due date (YYYY-MM-DD)", draft.get("due_date", ""), key=f"ddate{key}")
        hsn = c3.text_input("HSN / SAC code", draft.get("hsn_sac", ""), key=f"hsn{key}")

        c1, c2, c3, c4, c5 = st.columns(5)
        subtotal = c1.number_input("Subtotal", value=float(draft.get("subtotal") or 0), key=f"sub{key}")
        cgst = c2.number_input("CGST", value=float(draft.get("cgst") or 0), key=f"cgst{key}")
        sgst = c3.number_input("SGST", value=float(draft.get("sgst") or 0), key=f"sgst{key}")
        igst = c4.number_input("IGST", value=float(draft.get("igst") or 0), key=f"igst{key}")
        total = c5.number_input("Total", value=float(draft.get("total") or 0), key=f"total{key}")

        c1, c2 = st.columns(2)
        category = c1.selectbox("Category", CATEGORIES,
                                index=CATEGORIES.index(draft["category"]) if draft.get("category") in CATEGORIES else len(CATEGORIES) - 1,
                                key=f"cat{key}")
        payment = c2.selectbox("Payment status", ["Unpaid", "Paid"], key=f"pay{key}")

        save_anyway = st.checkbox("Save even if it looks like a duplicate")
        submitted = st.form_submit_button("Save invoice")

    if submitted:
        gst_sum = round(cgst + sgst + igst, 2)  # for non-GST receipts, fall back to the AI's tax value
        record = {
            "vendor": vendor, "invoice_number": number, "invoice_date": invoice_date,
            "due_date": due_date, "gstin": gstin.strip().upper(), "hsn_sac": hsn,
            "subtotal": subtotal, "cgst": cgst, "sgst": sgst, "igst": igst,
            "tax": gst_sum or float(draft.get("tax") or 0),
            "total": total, "category": category, "payment_status": payment,
            "file_name": file.name if file else "manual entry",
        }
        save_record(record, text, file, save_anyway)


def save_record(record, text, file, save_anyway):
    duplicate = expenses.find_duplicate(record, database.get_all())
    if duplicate and not save_anyway:
        st.error(f"⚠️ Possible duplicate of invoice #{duplicate['id']} "
                 f"({duplicate['vendor']}, {duplicate['invoice_number']}). Tick the box to save anyway.")
        return

    notes = check_invoice(record, text)
    record["needs_review"] = 1 if notes else 0
    record["review_notes"] = " | ".join(notes)
    database.add_invoice(record)

    if file:  # keep a copy of the original document on this computer
        with open(os.path.join(DOCS_DIR, file.name), "wb") as f:
            f.write(file.getvalue())

    st.success("Saved!")
    if notes:
        st.warning("Saved, but flagged for review:\n\n" + "\n".join(f"- {n}" for n in notes))
    del st.session_state["draft"]


# ------------------------------------------------------------------ Records
def records_page():
    st.header("Records")
    rows = load_rows()

    c1, c2, c3 = st.columns(3)
    text = c1.text_input("Search vendor or invoice number")
    category = c2.selectbox("Category", ["All"] + CATEGORIES)
    status = c3.selectbox("Status", ["All", "Unpaid", "Overdue", "Paid"])
    rows = expenses.search(rows, text, category, status)

    if not rows:
        st.info("No matching invoices.")
        return

    df = pd.DataFrame(rows)
    show = ["id", "vendor", "invoice_number", "invoice_date", "due_date", "total", "tax", "category", "status", "review_notes"]
    st.dataframe(df[show], hide_index=True, use_container_width=True)

    st.download_button("⬇️ Download CSV", expenses.to_csv(rows), "paperpilot_expenses.csv", "text/csv")

    st.subheader("Update an invoice")
    c1, c2, c3 = st.columns([1, 1, 4])
    invoice_id = c1.number_input("Invoice ID", min_value=1, step=1)
    if c2.button("Mark as paid"):
        database.mark_paid(invoice_id)
        st.rerun()
    if c3.button("Delete invoice"):
        database.delete_invoice(invoice_id)
        st.rerun()


# --------------------------------------------------------------- Bank match
def bank_page():
    st.header("Bank statement match")
    st.write("Upload your bank statement as CSV. Unpaid invoices whose total appears in it can be marked as paid.")

    file = st.file_uploader("Bank statement CSV", type=["csv"])
    if not file:
        return

    bank = pd.read_csv(file)
    column = st.selectbox("Which column holds the amounts?", bank.columns)
    amounts = pd.to_numeric(bank[column].astype(str).str.replace(",", ""), errors="coerce").dropna().abs().tolist()

    rows = load_rows()
    matched_ids = expenses.match_bank_amounts(rows, amounts)
    matched = [r for r in rows if r["id"] in matched_ids]

    if not matched:
        st.info("No unpaid invoices matched the statement.")
        return

    st.success(f"Found {len(matched)} matching invoice(s):")
    st.dataframe(pd.DataFrame(matched)[["id", "vendor", "invoice_number", "total"]], hide_index=True)
    if st.button("Mark all as paid"):
        for invoice_id in matched_ids:
            database.mark_paid(invoice_id)
        st.rerun()


# --------------------------------------------------------------------- Menu
st.sidebar.title("🧾 PaperPilot")
page = st.sidebar.radio("Go to", ["Dashboard", "Upload & Review", "Records", "Bank Match"])

if page == "Dashboard":
    dashboard_page()
elif page == "Upload & Review":
    upload_page()
elif page == "Records":
    records_page()
else:
    bank_page()
