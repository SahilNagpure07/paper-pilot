"""Step 1: read the text from a digital PDF."""
import fitz  # PyMuPDF


def extract_text(file_bytes):
    """Return the text found in the first 3 pages of a PDF."""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = "".join(page.get_text() for page in list(doc)[:3])

    if len(text.strip()) < 30:
        raise ValueError("No readable text found. Scanned PDFs are not supported, please upload a digital PDF.")
    return text
