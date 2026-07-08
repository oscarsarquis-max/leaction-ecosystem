"""Garante consultor@paneldx.com.br com senha e vínculo em contrato."""

import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from werkzeug.security import check_password_hash, generate_password_hash

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "LeAction_SysF" / ".env")

EMAIL = "consultor@paneldx.com.br"
SENHA = "Consultor@2026"
PWD_HASH = generate_password_hash(SENHA)

conn = psycopg2.connect(
    host=os.getenv("DB_HOST", "127.0.0.1"),
    port=os.getenv("DB_PORT", "5432"),
    dbname=os.getenv("DB_NAME", "LeAction_SysF"),
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASS", ""),
)
conn.autocommit = False
cur = conn.cursor()

cur.execute(
    """
    SELECT id_usuario, email, password_hash, system_role, ativo
    FROM public.paneldx_usuarios
    WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s));
    """,
    (EMAIL,),
)
user = cur.fetchone()
if user:
    uid = user[0]
    cur.execute(
        """
        UPDATE public.paneldx_usuarios
        SET nome = 'Consultor Demo PanelDX',
            password_hash = %s,
            system_role = 'consultor',
            ativo = TRUE
        WHERE id_usuario = %s;
        """,
        (PWD_HASH, uid),
    )
    print(f"Usuario atualizado: id_usuario={uid}")
else:
    cur.execute(
        """
        INSERT INTO public.paneldx_usuarios (email, nome, password_hash, system_role, ativo)
        VALUES (LOWER(%s), 'Consultor Demo PanelDX', %s, 'consultor', TRUE)
        RETURNING id_usuario;
        """,
        (EMAIL, PWD_HASH),
    )
    uid = int(cur.fetchone()[0])
    print(f"Usuario criado: id_usuario={uid}")

cur.execute("SELECT id FROM public.dx_consultores WHERE user_id = %s;", (uid,))
row = cur.fetchone()
if row:
    consultor_id = int(row[0])
    cur.execute(
        """
        UPDATE public.dx_consultores
        SET tipo = 'individual', id_agencia_pai = NULL, ativo = TRUE, atualizado_em = NOW()
        WHERE id = %s;
        """,
        (consultor_id,),
    )
else:
    cur.execute(
        """
        INSERT INTO public.dx_consultores
            (user_id, tipo, taxa_comissao_venda, taxa_comissao_tecnica, ativo)
        VALUES (%s, 'individual', 10.00, 15.00, TRUE)
        RETURNING id;
        """,
        (uid,),
    )
    consultor_id = int(cur.fetchone()[0])
print(f"Consultor id={consultor_id}")

cur.execute(
    """
    SELECT id FROM public.dx_planos
    WHERE LOWER(TRIM(nome)) LIKE '%premium%' AND COALESCE(tipo_plano, 'base') = 'base'
    ORDER BY id LIMIT 1;
    """
)
premium = cur.fetchone()
id_plano_premium = int(premium[0]) if premium else None

cur.execute(
    """
    SELECT id, id_clie FROM public.dx_contratos
    WHERE status IN ('ativo', 'trial')
    ORDER BY id ASC
    LIMIT 1;
    """
)
contrato = cur.fetchone()
if contrato:
    contrato_id, id_clie = int(contrato[0]), int(contrato[1])
    sets = ["id_consultor_origem = %s", "id_consultor_tecnico = %s", "atualizado_em = NOW()"]
    params: list = [consultor_id, consultor_id]
    if id_plano_premium:
        sets.insert(0, "id_plano = %s")
        params.insert(0, id_plano_premium)
    params.append(contrato_id)
    cur.execute(
        f"UPDATE public.dx_contratos SET {', '.join(sets)} WHERE id = %s;",
        tuple(params),
    )
    print(f"Contrato {contrato_id} (clie={id_clie}) vinculado a consultor@paneldx.com.br (origem+técnico)")
else:
    print("AVISO: nenhum contrato ativo para vincular.")

conn.commit()

cur.execute(
    "SELECT password_hash FROM public.paneldx_usuarios WHERE id_usuario = %s;",
    (uid,),
)
ph = cur.fetchone()[0]
ok = check_password_hash(ph, SENHA)
print(f"Senha valida: {ok}")

cur.execute(
    """
    SELECT 1 FROM public.paneldx_usuarios
    WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s)) AND ativo = TRUE;
    """,
    (EMAIL,),
)
print(f"check-email encontraria usuario: {bool(cur.fetchone())}")

cur.close()
conn.close()
print("Pronto. Login: consultor@paneldx.com.br / Consultor@2026")
