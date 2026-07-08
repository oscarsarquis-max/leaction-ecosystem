from sqlalchemy import text
from database.models import get_engine

with get_engine().connect() as c:
    r = c.execute(
        text("SELECT content_value FROM ui_content WHERE content_key = 'assets.logo'")
    ).fetchone()
    print("assets.logo:", r[0] if r else None)
