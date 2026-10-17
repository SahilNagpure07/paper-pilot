import os

from dotenv import load_dotenv

load_dotenv()  # reads GEMINI_API_KEY from the .env file

MODEL = os.getenv("PAPERPILOT_MODEL", "gemma-4-26b-a4b-it")

DB_PATH = "data/paperpilot.db"
DOCS_DIR = "data/documents"

CATEGORIES = [
    "Office Supplies", "Software", "Travel", "Food", "Utilities",
    "Rent", "Marketing", "Professional Services", "Hardware", "Other",
]
