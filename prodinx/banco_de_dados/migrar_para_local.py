"""Cria a base prodinx no PostgreSQL local e copia dados do Docker."""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.extras import Json

PASSWORD = "Cmgv6190!@"
LOCAL = dict(host="localhost", port=5432, user="postgres", password=PASSWORD)
DOCKER = dict(host="localhost", port=5435, user="postgres", password=PASSWORD, dbname="prodinx")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS indicadores (
    id SERIAL PRIMARY KEY,
    nome_metrica VARCHAR(255) NOT NULL,
    data_importacao TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    data_referencia_inicio DATE,
    data_referencia_fim DATE,
    payload_completo JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_indicadores_nome_metrica ON indicadores (nome_metrica);
CREATE INDEX IF NOT EXISTS ix_indicadores_data_referencia_inicio ON indicadores (data_referencia_inicio);
CREATE INDEX IF NOT EXISTS ix_indicadores_data_importacao ON indicadores (data_importacao);
"""


def ensure_local_database():
    conn = psycopg2.connect(dbname="postgres", **LOCAL)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = 'prodinx'")
    if not cur.fetchone():
        cur.execute("CREATE DATABASE prodinx")
        print("Base prodinx criada no PostgreSQL local (porta 5432).")
    else:
        print("Base prodinx ja existe no PostgreSQL local.")
    conn.close()


def apply_schema():
    conn = psycopg2.connect(dbname="prodinx", **LOCAL)
    cur = conn.cursor()
    cur.execute(SCHEMA_SQL)
    conn.commit()
    conn.close()
    print("Schema aplicado.")


def copy_data_from_docker():
    try:
        src = psycopg2.connect(**DOCKER)
    except Exception as exc:
        print(f"Docker indisponivel ({exc}). Dados nao copiados.")
        return 0

    dst = psycopg2.connect(dbname="prodinx", **LOCAL)
    src_cur = src.cursor()
    dst_cur = dst.cursor()

    src_cur.execute(
        """SELECT nome_metrica, data_importacao, data_referencia_inicio,
                  data_referencia_fim, payload_completo
           FROM indicadores ORDER BY id"""
    )
    rows = src_cur.fetchall()

    dst_cur.execute("TRUNCATE indicadores RESTART IDENTITY")
    for row in rows:
        nome, data_importacao, inicio, fim, payload = row
        dst_cur.execute(
            """INSERT INTO indicadores
               (nome_metrica, data_importacao, data_referencia_inicio,
                data_referencia_fim, payload_completo)
               VALUES (%s, %s, %s, %s, %s)""",
            (nome, data_importacao, inicio, fim, Json(payload)),
        )

    dst.commit()
    src.close()
    dst.close()
    print(f"{len(rows)} registos copiados do Docker para o PostgreSQL local.")
    return len(rows)


if __name__ == "__main__":
    ensure_local_database()
    apply_schema()
    copy_data_from_docker()
