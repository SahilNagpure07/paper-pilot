"""Remove personal details from text BEFORE it is sent to any hosted AI.
The original document and the full text stay on this computer.
"""
import re

# Order matters: emails first, then phones, then ID numbers.
PATTERNS = [
    (r"[\w.+-]+@[\w-]+\.[\w.-]+", "[EMAIL]"),
    (r"(?:\+91[\s-]?)?\b[6-9]\d{9}\b", "[PHONE]"),
    (r"\b\d{4}\s\d{4}\s\d{4}\b", "[AADHAAR]"),           # 12 digits written in groups of 4
    (r"\b[A-Z]{5}\d{4}[A-Z]\b", "[PAN]"),                # PAN card number
    (r"(?i)(a/c|account)\s*(no\.?|number)?\s*[:\-]?\s*\d{9,18}", "[BANK ACCOUNT]"),
]


def redact(text):
    for pattern, label in PATTERNS:
        text = re.sub(pattern, label, text)
    return text
