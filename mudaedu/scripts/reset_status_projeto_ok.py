import psycopg2

conn = psycopg2.connect(
    host="127.0.0.1",
    port=5432,
    dbname="LeAction_SysF",
    user="postgres",
    password="Cmgv6190!@",
)
cur = conn.cursor()
cur.execute(
    """
    SELECT m.id_matu, m.id_clie, m.status_ia, c.mail_clie, c.has_active_project
    FROM ctdi_matu m
    JOIN ctdi_clie c ON c.id_clie = m.id_clie
    WHERE LOWER(c.mail_clie) = LOWER('dev@leaction.com.br')
    ORDER BY m.id_matu
    """
)
rows = cur.fetchall()
print("ANTES:", rows)

if not rows:
    raise SystemExit("Nenhum registro encontrado para dev@leaction.com.br")

for row in rows:
    id_matu = row[0]
    cur.execute("UPDATE ctdi_matu SET status_ia = %s WHERE id_matu = %s", ("PROJETO OK", id_matu))
    print(f"Atualizado id_matu={id_matu} -> PROJETO OK")

conn.commit()

cur.execute(
    """
    SELECT m.id_matu, m.id_clie, m.status_ia, c.mail_clie, c.has_active_project
    FROM ctdi_matu m
    JOIN ctdi_clie c ON c.id_clie = m.id_clie
    WHERE LOWER(c.mail_clie) = LOWER('dev@leaction.com.br')
    ORDER BY m.id_matu
    """
)
print("DEPOIS:", cur.fetchall())
conn.close()
