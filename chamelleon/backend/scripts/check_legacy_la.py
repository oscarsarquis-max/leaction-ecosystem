import os
from pathlib import Path
from urllib.parse import unquote, urlparse

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
import psycopg2

url = os.getenv("LEGACY_QUEST_DATABASE_URL")
p = urlparse(url)
conn = psycopg2.connect(
    host=p.hostname,
    port=p.port or 5432,
    dbname=p.path.lstrip("/").split("?")[0],
    user=unquote(p.username or ""),
    password=unquote(p.password or ""),
)
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM leaf_bloc")
print("leaf_bloc count:", cur.fetchone()[0])
cur.execute("SELECT COUNT(*) FROM leaf_bloc WHERE id_dime=4")
print("LA blocks:", cur.fetchone()[0])
cur.execute("SELECT COUNT(*) FROM ctdi_quest WHERE id_dime=4 AND id_doma IS NOT NULL")
print("LA questions:", cur.fetchone()[0])
cur.execute("SELECT DISTINCT setor_ques FROM ctdi_quest WHERE id_dime=4 LIMIT 10")
print("LA setor_ques:", cur.fetchall())
conn.close()
