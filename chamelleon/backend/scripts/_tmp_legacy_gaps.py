import os
from urllib.parse import unquote, urlparse
import psycopg2
from psycopg2.extras import RealDictCursor

DIME = {1: "SV", 2: "HC", 3: "FS", 5: "DA"}
DOMA = {1: "ds", 2: "bm", 3: "ic", 4: "dc", 5: "cc", 6: "dg", 7: "dp", 8: "cap", 9: "dm"}

url = "postgresql://postgres:Cmgv6190!%40@127.0.0.1:5432/LeAction_SysF"
p = urlparse(url)
conn = psycopg2.connect(host=p.hostname, port=5432, dbname="LeAction_SysF", user="postgres", password="Cmgv6190!@")
cur = conn.cursor(cursor_factory=RealDictCursor)
cur.execute(
    """
    SELECT id_dime, id_doma, prefu_ques, setor_ques, id_ques
    FROM ctdi_quest
    WHERE id_dime IN (1,2,3,5) AND id_doma IS NOT NULL
    ORDER BY id_dime, id_doma, prefu_ques, id_ques
    """
)
rows = cur.fetchall()
conn.close()

geral = set()
for r in rows:
    setor = (r["setor_ques"] or "GERAL").upper()
    if setor in ("GERAL", "") and setor != "EDUCACAO":
        if setor == "GERAL" or not r["setor_ques"]:
            key = (r["id_dime"], r["id_doma"], r["prefu_ques"])
            if (r.get("setor_ques") or "GERAL").upper() == "GERAL":
                geral.add(key)

# rebuild properly
from collections import defaultdict
slots = defaultdict(list)
for r in rows:
    setor = (r["setor_ques"] or "GERAL").strip().upper()
    if setor == "EDUCACAO" or setor == "EDUCAÇÃO":
        continue
    if setor != "GERAL":
        continue
    slots[(r["id_dime"], r["id_doma"], r["prefu_ques"])].append(r["id_ques"])

missing_f = []
for dime in (1, 2, 3, 5):
    for doma in range(1, 10):
        for prefu in ("P", "F"):
            if (dime, doma, prefu) not in slots:
                missing_f.append((DIME[dime], DOMA[doma], prefu))

print("Missing GERAL slots in legacy:", len(missing_f))
for m in missing_f:
    print(" ", m)
