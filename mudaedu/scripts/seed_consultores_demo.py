"""Seed de consultores demo + vínculos em contratos para validar conciliação."""

from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / "LeAction_SysF" / ".env")

SENHA_DEMO = "Consultor@2026"
PWD_HASH = generate_password_hash(SENHA_DEMO)

PERFIS = [
    {
        "email": "consultor.agencia.alpha@leaction.com.br",
        "nome": "Agência Alpha",
        "tipo": "agencia",
        "id_agencia_pai": None,
    },
    {
        "email": "consultor.joao@leaction.com.br",
        "nome": "Consultor João",
        "tipo": "individual",
        "id_agencia_pai_ref": "agencia_alpha",
    },
    {
        "email": "consultor.maria@leaction.com.br",
        "nome": "Consultor Independente Maria",
        "tipo": "individual",
        "id_agencia_pai_ref": None,
    },
    {
        "email": "consultor@paneldx.com.br",
        "nome": "Consultor Demo PanelDX",
        "tipo": "individual",
        "id_agencia_pai_ref": None,
    },
]


def upsert_usuario(cur, email: str, nome: str) -> int:
    cur.execute(
        """
        INSERT INTO public.paneldx_usuarios (email, nome, password_hash, system_role, ativo)
        VALUES (LOWER(%s), %s, %s, 'consultor', TRUE)
        ON CONFLICT DO NOTHING;
        """,
        (email, nome, PWD_HASH),
    )
    cur.execute(
        """
        UPDATE public.paneldx_usuarios
        SET nome = %s,
            password_hash = %s,
            system_role = 'consultor',
            ativo = TRUE
        WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s))
        RETURNING id_usuario;
        """,
        (nome, PWD_HASH, email),
    )
    row = cur.fetchone()
    if row:
        return int(row[0])
    cur.execute(
        "SELECT id_usuario FROM public.paneldx_usuarios WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s));",
        (email,),
    )
    return int(cur.fetchone()[0])


def upsert_consultor(cur, user_id: int, tipo: str, id_agencia_pai: int | None) -> int:
    cur.execute("SELECT id FROM public.dx_consultores WHERE user_id = %s;", (user_id,))
    row = cur.fetchone()
    if row:
        cur.execute(
            """
            UPDATE public.dx_consultores
            SET tipo = %s,
                id_agencia_pai = %s,
                taxa_comissao_venda = 10.00,
                taxa_comissao_tecnica = 15.00,
                ativo = TRUE,
                atualizado_em = NOW()
            WHERE user_id = %s
            RETURNING id;
            """,
            (tipo, id_agencia_pai, user_id),
        )
        return int(cur.fetchone()[0])
    cur.execute(
        """
        INSERT INTO public.dx_consultores
            (user_id, tipo, id_agencia_pai, taxa_comissao_venda, taxa_comissao_tecnica, ativo)
        VALUES (%s, %s, %s, 10.00, 15.00, TRUE)
        RETURNING id;
        """,
        (user_id, tipo, id_agencia_pai),
    )
    return int(cur.fetchone()[0])


def assert_seed_environment() -> None:
    host = (os.getenv("DB_HOST") or "127.0.0.1").lower()
    is_local = host in ("127.0.0.1", "localhost", "::1")
    if is_local:
        return
    if os.getenv("SEED_DEV_ALLOW", "").strip() != "1":
        raise SystemExit(
            f"Abortado: DB_HOST={host!r} não é local. Defina SEED_DEV_ALLOW=1 para RDS."
        )
    confirm = os.getenv("SEED_PROD_CONFIRM", "").strip()
    if confirm not in ("paneldx-demo-consultores", "paneldx-demo-reset"):
        raise SystemExit(
            "Abortado: RDS exige SEED_PROD_CONFIRM=paneldx-demo-consultores"
        )
    if "rds.amazonaws.com" in host and (os.getenv("DB_SSLMODE") or "disable") == "disable":
        os.environ["DB_SSLMODE"] = "require"


assert_seed_environment()

conn = psycopg2.connect(
    host=os.getenv("DB_HOST", "127.0.0.1"),
    port=os.getenv("DB_PORT", "5432"),
    dbname=os.getenv("DB_NAME", "LeAction_SysF"),
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASS", ""),
    sslmode=os.getenv("DB_SSLMODE", "disable"),
)
conn.autocommit = False
cur = conn.cursor()

ids: dict[str, int] = {}

for perfil in PERFIS:
    uid = upsert_usuario(cur, perfil["email"], perfil["nome"])
    pai = None
    if perfil.get("id_agencia_pai_ref") == "agencia_alpha":
        pai = ids.get("agencia_alpha")
    key = (
        "agencia_alpha"
        if perfil["tipo"] == "agencia"
        else "joao"
        if "joao" in perfil["email"]
        else "paneldx"
        if perfil["email"] == "consultor@paneldx.com.br"
        else "maria"
    )
    if perfil["tipo"] != "agencia" and perfil.get("id_agencia_pai_ref") == "agencia_alpha" and not pai:
        raise RuntimeError("Agência Alpha deve ser criada antes de João.")
    cid = upsert_consultor(cur, uid, perfil["tipo"], pai)
    ids[key] = cid
    print(f"Consultor {perfil['nome']}: id={cid}, user_id={uid}, email={perfil['email']}")

if ids.get("joao") and ids.get("agencia_alpha"):
    cur.execute(
        """
        UPDATE public.dx_consultores
        SET id_agencia_pai = %s, atualizado_em = NOW()
        WHERE id = %s;
        """,
        (ids["agencia_alpha"], ids["joao"]),
    )

cur.execute(
    """
    SELECT id, id_clie, id_plano
    FROM public.dx_contratos
    WHERE status IN ('ativo', 'trial')
    ORDER BY id ASC
    LIMIT 10;
    """
)
contratos = list(cur.fetchall())

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
    SELECT id FROM public.dx_planos
    WHERE COALESCE(tipo_plano, 'base') = 'base'
      AND LOWER(TRIM(nome)) NOT LIKE '%premium%'
    ORDER BY valor_mensal ASC, id ASC
    LIMIT 1;
    """
)
basico = cur.fetchone()
id_plano_basico = int(basico[0]) if basico else None

if len(contratos) < 2:
    cur.execute(
        """
        SELECT id_clie FROM public.ctdi_clie
        WHERE LOWER(TRIM(mail_clie)) = LOWER('cliente.demo.maria@leaction.com.br')
        LIMIT 1;
        """
    )
    demo_row = cur.fetchone()
    if demo_row:
        id_clie_extra = int(demo_row[0])
    else:
        cur.execute(
            """
            INSERT INTO public.ctdi_clie (nome_clie, mail_clie, init_role, has_active_project)
            VALUES ('Colégio Demo Maria', 'cliente.demo.maria@leaction.com.br', 'GENERAL', FALSE)
            RETURNING id_clie;
            """
        )
        id_clie_extra = int(cur.fetchone()[0])
        print(f"Cliente demo criado: id_clie={id_clie_extra}")

    plano_extra = id_plano_premium or id_plano_basico
    if plano_extra:
        cur.execute(
            "SELECT id FROM public.dx_contratos WHERE id_clie = %s AND status IN ('ativo','trial') LIMIT 1;",
            (id_clie_extra,),
        )
        if not cur.fetchone():
            cur.execute(
                "SELECT valor_mensal FROM public.dx_planos WHERE id = %s;",
                (plano_extra,),
            )
            valor_extra = float(cur.fetchone()[0])
            inicio = date.today()
            fim = inicio + timedelta(days=365)
            cur.execute(
                """
                INSERT INTO public.dx_contratos
                    (id_clie, id_plano, valor_negociado, status, data_inicio, data_vencimento)
                VALUES (%s, %s, %s, 'ativo', %s, %s)
                RETURNING id, id_clie, id_plano;
                """,
                (id_clie_extra, plano_extra, valor_extra, inicio, fim),
            )
            contratos.append(cur.fetchone())
            print(f"Contrato demo Maria criado para clie={id_clie_extra}.")
        else:
            cur.execute(
                """
                SELECT id, id_clie, id_plano FROM public.dx_contratos
                WHERE id_clie = %s AND status IN ('ativo','trial')
                ORDER BY id DESC LIMIT 1;
                """,
                (id_clie_extra,),
            )
            row = cur.fetchone()
            if row and row not in contratos:
                contratos.append(row)

if len(contratos) >= 1 and ids.get("paneldx"):
    c1_id, c1_clie, c1_plano = contratos[0]
    plano_alvo = id_plano_premium or c1_plano
    cur.execute(
        """
        UPDATE public.dx_contratos
        SET id_plano = %s,
            id_consultor_origem = %s,
            id_consultor_tecnico = %s,
            atualizado_em = NOW()
        WHERE id = %s;
        """,
        (plano_alvo, ids["paneldx"], ids["paneldx"], c1_id),
    )
    print(
        f"Contrato {c1_id} (clie={c1_clie}): consultor@paneldx.com.br origem+técnico, plano_id={plano_alvo}"
    )

if len(contratos) >= 2 and ids.get("joao"):
    cj_id, cj_clie, cj_plano = contratos[1]
    plano_alvo = id_plano_basico or cj_plano
    cur.execute(
        """
        UPDATE public.dx_contratos
        SET id_plano = %s,
            id_consultor_origem = %s,
            id_consultor_tecnico = NULL,
            atualizado_em = NOW()
        WHERE id = %s;
        """,
        (plano_alvo, ids["joao"], cj_id),
    )
    print(
        f"Contrato {cj_id} (clie={cj_clie}): João origem, plano_id={plano_alvo} (roll-up agência)"
    )

if len(contratos) >= 2 and ids.get("maria"):
    cm_id, cm_clie, cm_plano = contratos[1]
    plano_alvo = id_plano_premium or cm_plano
    cur.execute(
        """
        UPDATE public.dx_contratos
        SET id_plano = %s,
            id_consultor_origem = %s,
            id_consultor_tecnico = %s,
            atualizado_em = NOW()
        WHERE id = %s;
        """,
        (plano_alvo, ids["maria"], ids["maria"], cm_id),
    )
    print(
        f"Contrato {cm_id} (clie={cm_clie}): Maria origem+técnico, plano_id={plano_alvo} (comissão independente)"
    )
elif len(contratos) == 1 and ids.get("maria"):
    print("Aviso: apenas 1 contrato ativo — vincule Maria manualmente no CRM Admin.")

if ids.get("joao") and contratos:
    id_clie_demo = contratos[0][1]
    cur.execute(
        """
        INSERT INTO public.dx_demandas_consultor (id_clie, id_consultor, titulo, descricao, status)
        SELECT %s, %s, v.titulo, v.descricao, v.status
        FROM (VALUES
            ('Revisão do roadmap Q3', 'Cliente solicita alinhamento estratégico do trimestre.', 'aberta'),
            ('Workshop de OKRs', 'Agendar sessão com o time de liderança.', 'em_andamento')
        ) AS v(titulo, descricao, status)
        WHERE NOT EXISTS (
            SELECT 1 FROM public.dx_demandas_consultor d
            WHERE d.id_consultor = %s AND d.titulo = v.titulo
        );
        """,
        (id_clie_demo, ids["joao"], ids["joao"]),
    )

conn.commit()
cur.close()
conn.close()

print("\n--- Credenciais de teste (senha para todos) ---")
print(f"Senha: {SENHA_DEMO}")
for p in PERFIS:
    print(f"  • {p['email']}")
print("\nSeed consultores demo concluído.")
