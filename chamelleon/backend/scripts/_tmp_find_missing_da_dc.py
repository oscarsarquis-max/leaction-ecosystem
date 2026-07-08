import os
from urllib.parse import unquote, urlparse

import psycopg2
from psycopg2.extras import RealDictCursor

url = os.getenv("DATABASE_URL", "postgresql://postgres:Cmgv6190!%40@127.0.0.1:5432/chamelleon")
p = urlparse(url)
conn = psycopg2.connect(
    host=p.hostname, port=5432, dbname="chamelleon",
    user=unquote(p.username or "postgres"), password=unquote(p.password or ""),
)
cur = conn.cursor(cursor_factory=RealDictCursor)

for fw in ("telecomunicacoes-v1", "educacao-v1"):
    print(f"\n=== {fw} — dimensão DA, domínio dc ===")
    cur.execute(
        """
        SELECT id::text, item_metadata->>'prefu_ques' as prefu, axis, question_text
        FROM assessment_items
        WHERE framework_id = %s
          AND (item_metadata->>'dimension_key' = 'DA' OR item_metadata->>'legacy_id_dime' = '5')
          AND item_metadata->>'domain_key' = 'dc'
        ORDER BY prefu
        """,
        (fw,),
    )
    for r in cur.fetchall():
        print(r["prefu"], r["id"][:8], r["axis"][:60])
        print(" ", r["question_text"][:120])

# Legacy PanelDX
legacy = os.getenv("LEGACY_QUEST_DATABASE_URL", "postgresql://postgres:Cmgv6190!%40@127.0.0.1:5432/LeAction_SysF")
lp = urlparse(legacy)
lconn = psycopg2.connect(
    host=lp.hostname, port=5432, dbname=lp.path.lstrip("/").split("?")[0],
    user=unquote(lp.username or "postgres"), password=unquote(lp.password or ""),
)
lcur = lconn.cursor(cursor_factory=RealDictCursor)
lcur.execute(
    """
    SELECT id_ques, id_dime, id_doma, prefu_ques, left(desc_ques, 120) as q
    FROM ctdi_quest
    WHERE id_dime = 5 AND id_doma = 4
    ORDER BY prefu_ques
    """
)
print("\n=== Legado PanelDX id_dime=5 (DA), id_doma=4 (dc) ===")
for r in lcur.fetchall():
    print(r)

cur.close()
conn.close()
lcur.close()
lconn.close()
