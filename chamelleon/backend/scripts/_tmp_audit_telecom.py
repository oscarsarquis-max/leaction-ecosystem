import os
from collections import defaultdict
from urllib.parse import unquote, urlparse

import psycopg2
from psycopg2.extras import RealDictCursor

CANONICAL_DOMAINS = ("ds", "bm", "ic", "dc", "cc", "dg", "dp", "cap", "dm")

url = os.getenv("DATABASE_URL", "postgresql://postgres:Cmgv6190!%40@127.0.0.1:5432/chamelleon")
p = urlparse(url)
conn = psycopg2.connect(
    host=p.hostname,
    port=5432,
    dbname=p.path.lstrip("/").split("?")[0],
    user=unquote(p.username or "postgres"),
    password=unquote(p.password or ""),
)
cur = conn.cursor(cursor_factory=RealDictCursor)

cur.execute(
    "SELECT id, name FROM frameworks WHERE id ILIKE '%telecom%' OR industry ILIKE '%telecom%' ORDER BY id"
)
frameworks = cur.fetchall()
print("Frameworks telecom:", frameworks)

for fw in frameworks:
    fw_id = fw["id"]
    print("\n===", fw_id, fw["name"], "===")
    cur.execute(
        """
        SELECT item_metadata->>'legacy_id_dime' as dime,
               item_metadata->>'dimension_key' as dkey,
               item_metadata->>'domain_key' as dom,
               item_metadata->>'prefu_ques' as prefu,
               id::text as id,
               left(question_text, 80) as q
        FROM assessment_items
        WHERE framework_id = %s
        ORDER BY dkey, dime, dom, prefu
        """,
        (fw_id,),
    )
    rows = cur.fetchall()
    print("Total:", len(rows))

    by_dim = defaultdict(lambda: {"P": set(), "F": set(), "items": []})
    for r in rows:
        dim = (r["dkey"] or r["dime"] or "?").upper()
        dom = (r["dom"] or "?").lower()
        prefu = (r["prefu"] or "P").upper()
        if prefu in ("P", "F") and dom:
            by_dim[dim][prefu].add(dom)
        by_dim[dim]["items"].append(r)

    for dim in sorted(by_dim.keys()):
        p = by_dim[dim]["P"]
        f = by_dim[dim]["F"]
        print(f"  {dim}: P={len(p)} F={len(f)} total={len(p)+len(f)}")
        missing_p = set(CANONICAL_DOMAINS) - p
        missing_f = set(CANONICAL_DOMAINS) - f
        if missing_p:
            print(f"    FALTA Presente: {sorted(missing_p)}")
        if missing_f:
            print(f"    FALTA Futuro: {sorted(missing_f)}")

    # cross-check all expected slots
    all_slots = set()
    for dim, data in by_dim.items():
        for prefu in ("P", "F"):
            for dom in data[prefu]:
                all_slots.add((dim, dom, prefu))
    print("Slots cobertos:", len(all_slots), "esperado: 90")

cur.close()
conn.close()
