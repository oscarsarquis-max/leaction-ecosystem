import os
from pathlib import Path

from dotenv import load_dotenv

from app import create_app

BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(BACKEND_DIR.parent / ".env")

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", os.getenv("FLASK_PORT", "5010")))
    app.run(host="0.0.0.0", port=port, debug=app.config.get("DEBUG", True))
