# 🧾 PaperPilot: Invoice & Expense Assistant

PaperPilot reads PDF invoices with **Gemma, an open-weight AI model**, checks the results,
and organises everything into searchable records and CSV exports.
Built for freelancers, consultants, and small agencies.

## Features
- Upload digital PDF invoices (scanned or image files are not supported)
- Gemma extracts vendor, dates, subtotal, tax and total
- **India GST support:** GSTIN, CGST / SGST / IGST, HSN / SAC codes
- **Duplicate invoice detection**
- **Overdue payment flags** based on due date
- **Bank statement matching:** upload a CSV and mark paid invoices automatically
- **Safety checks:** totals that do not add up, bad GSTINs, or amounts missing from the document are flagged for review
- Search, filter, and CSV export

## Why an open model?
- **Open weights:** Gemma's weights are public, so the same model can later be self-hosted by anyone who needs full control.
- **Low cost:** hosted Gemma is inexpensive to call, which suits a small side-hustle product. Check Google's current pricing and free tier.
- **Swappable:** change one line (`PAPERPILOT_MODEL`) to try a different Gemma model.

## Privacy and trade-offs
- Personal details (emails, phone numbers, PAN, Aadhaar, bank account numbers) are removed from the text by `src/privacy.py` before it is sent to the model.
- Redaction is pattern-based and not perfect. Use sample or fake invoices for demos.
- A small model can misread messy receipts, so every invoice goes through a human review step and validation checks before saving.

## Setup
1. Install [Python 3.10+](https://www.python.org/downloads/)
2. Install the Python packages:
   ```
   pip install -r requirements.txt
   ```
3. Get a free API key and put it in the `.env` file:
   ```
   GEMINI_API_KEY=your-key-here
   ```
4. Run:
   ```
   streamlit run app.py
   ```
