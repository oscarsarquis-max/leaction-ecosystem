"""Consulta roteiros recentes e envios de e-mail."""
from sqlalchemy import text

from database.models import get_engine

engine = get_engine()

with engine.connect() as conn:
    rows = conn.execute(
        text(
            """
            SELECT r.id,
                   r.status,
                   r.email_automatico_enviado_em,
                   r.data_geracao,
                   p.email
              FROM roteiros r
              JOIN desafios d ON d.id = r.desafio_id
              JOIN professores p ON p.id = d.professor_id
          ORDER BY r.id DESC
             LIMIT 20
            """
        )
    ).fetchall()
    for row in rows:
        print(row)

    print("--- duplicates by email in last 2 hours ---")
    dups = conn.execute(
        text(
            """
            SELECT p.email, COUNT(*) AS total
              FROM roteiros r
              JOIN desafios d ON d.id = r.desafio_id
              JOIN professores p ON p.id = d.professor_id
             WHERE r.data_geracao > CURRENT_TIMESTAMP - INTERVAL '2 hours'
          GROUP BY p.email
            HAVING COUNT(*) > 1
          ORDER BY total DESC
            """
        )
    ).fetchall()
    for row in dups:
        print(row)
