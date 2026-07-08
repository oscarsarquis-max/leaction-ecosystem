import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "Cmgv6190!@")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "prodinx")

DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:{quote_plus(POSTGRES_PASSWORD)}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

JSON_IMPORT_DIR = Path(os.getenv("JSON_IMPORT_DIR", PROJECT_ROOT / "jsonfiles"))
JSON_PROCESSED_DIR = Path(os.getenv("JSON_PROCESSED_DIR", JSON_IMPORT_DIR / "processados"))
JSON_FAILED_DIR = Path(os.getenv("JSON_FAILED_DIR", JSON_IMPORT_DIR / "falhas"))
