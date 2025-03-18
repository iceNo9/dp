import os
from pathlib import Path

def get_data_dir():
    docs_dir = Path.home() / "Documents" / "dp" / "data"
    docs_dir.mkdir(parents=True, exist_ok=True)
    return docs_dir

DATA_DIR = get_data_dir()
PASSWORDS_FILE = DATA_DIR / "passwords.json"