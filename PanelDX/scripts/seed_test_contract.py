"""Garante contrato ativo de teste para E2E de add-ons."""

import os
from datetime import date, timedelta
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "LeAction_SysF" / ".env")

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASS"),
)
conn.autocommit = True
cur = conn.cursor()

cur.execute("SELECT id_clie FROM public.ctdi_clie ORDER BY id_clie DESC LIMIT 1")
row = cur.fetchone()
if not row:
    raise SystemExit("Nenhum cliente em ctdi_clie.")
id_clie = int(row[0])

cur.execute(
    """
    SELECT id FROM public.dx_contratos
    WHERE id_clie = %s AND status = 'ativo'
    LIMIT 1;
    """,
    (id_clie,),
)
if cur.fetchone():
    print(f"Contrato ativo já existe para id_clie={id_clie}")
else:
    cur.execute("SELECT id FROM public.dx_planos WHERE tipo_plano = 'base' AND ativo = TRUE ORDER BY id LIMIT 1")
    id_plano = int(cur.fetchone()[0])
    cur.execute("SELECT valor_mensal FROM public.dx_planos WHERE id = %s", (id_plano,))
    valor = cur.fetchone()[0]
    inicio = date.today()
    fim = inicio + timedelta(days=365)
    cur.execute(
        """
        INSERT INTO public.dx_contratos
            (id_clie, id_plano, valor_negociado, status, data_inicio, data_vencimento)
        VALUES (%s, %s, %s, 'ativo', %s, %s)
        RETURNING id;
        """,
        (id_clie, id_plano, valor, inicio, fim),
    )
    id_contrato = cur.fetchone()[0]
    print(f"Contrato de teste criado: id={id_contrato}, id_clie={id_clie}, id_plano={id_plano}")

cur.close()
conn.close()
