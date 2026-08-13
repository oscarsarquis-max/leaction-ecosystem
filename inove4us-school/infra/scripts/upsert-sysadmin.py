#!/usr/bin/env python3
"""Upsert sysadmin do School (todas as zonas RBAC).

Uso:
  python upsert-sysadmin.py
  # env: DATABASE_URL ou DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASS
  #      SCHOOL_SYSADMIN_EMAIL (default admin@i4uschool.com.br)
  #      SCHOOL_SYSADMIN_PASSWORD (obrigatório se não gerar)
  #      SCHOOL_SYSADMIN_GENERATE=1  → gera senha e imprime só em stdout uma vez
"""
from __future__ import annotations

import os
import secrets
import string
import sys
import urllib.parse

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("psycopg2 necessário", file=sys.stderr)
    sys.exit(1)

from werkzeug.security import generate_password_hash

EMAIL = (os.environ.get("SCHOOL_SYSADMIN_EMAIL") or "admin@i4uschool.com.br").strip().lower()
NOME = (os.environ.get("SCHOOL_SYSADMIN_NOME") or "Sysadmin inove4us School").strip()
# cargo = rótulo; autorização = zonas (todas)
CARGO = "Outro"
ZONAS = ("administrativo", "operacional", "pedagogico")
DEV_INST = "a1111111-1111-4111-8111-111111111111"


def connect():
    url = (os.environ.get("DATABASE_URL") or "").strip()
    if url:
        p = urllib.parse.urlparse(url)
        return psycopg2.connect(
            dbname=(p.path or "/inove4us_school").lstrip("/") or "inove4us_school",
            user=p.username,
            password=urllib.parse.unquote(p.password or ""),
            host=p.hostname,
            port=p.port or 5432,
            sslmode="require" if "sslmode=require" in url or "rds.amazonaws" in (p.hostname or "") else "prefer",
        )
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        port=int(os.environ.get("DB_PORT", "5433")),
        dbname=os.environ.get("DB_NAME", "inove4us_school"),
        user=os.environ.get("DB_USER", "admin"),
        password=os.environ.get("DB_PASS", "password123"),
        sslmode=os.environ.get("DB_SSLMODE", "prefer"),
    )


def main() -> None:
    password = (os.environ.get("SCHOOL_SYSADMIN_PASSWORD") or "").strip()
    generated = False
    if not password:
        if os.environ.get("SCHOOL_SYSADMIN_GENERATE", "").strip() in ("1", "true", "yes"):
            alphabet = string.ascii_letters + string.digits
            password = "I4u!" + "".join(secrets.choice(alphabet) for _ in range(14))
            generated = True
        else:
            print("Defina SCHOOL_SYSADMIN_PASSWORD ou SCHOOL_SYSADMIN_GENERATE=1", file=sys.stderr)
            sys.exit(1)

    senha_hash = generate_password_hash(password)
    conn = connect()
    conn.autocommit = True
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id FROM school_instituicoes ORDER BY created_at NULLS LAST LIMIT 1")
            inst = cur.fetchone()
            if not inst:
                cur.execute(
                    """
                    INSERT INTO school_instituicoes (id, razao_social, cnpj, dominio_email, status)
                    VALUES (%s, %s, %s, %s, 'ativa')
                    ON CONFLICT (cnpj) WHERE cnpj IS NOT NULL DO NOTHING
                    RETURNING id
                    """,
                    (DEV_INST, "inove4us School (sysadmin)", "00.000.000/0001-00", "i4uschool.com.br"),
                )
                row = cur.fetchone()
                if row:
                    instituicao_id = row["id"]
                else:
                    cur.execute("SELECT id FROM school_instituicoes LIMIT 1")
                    instituicao_id = cur.fetchone()["id"]
            else:
                instituicao_id = inst["id"]

            cur.execute(
                """
                INSERT INTO school_gestores (
                    instituicao_id, nome, email, senha_hash, cargo, ativo
                ) VALUES (%s, %s, %s, %s, %s, TRUE)
                ON CONFLICT (email) DO UPDATE SET
                    nome = EXCLUDED.nome,
                    senha_hash = EXCLUDED.senha_hash,
                    cargo = EXCLUDED.cargo,
                    ativo = TRUE,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id, email
                """,
                (str(instituicao_id), NOME, EMAIL, senha_hash, CARGO),
            )
            gestor = cur.fetchone()
            gestor_id = gestor["id"]

            for zona in ZONAS:
                cur.execute(
                    """
                    INSERT INTO school_gestor_perfis (gestor_id, zona, ativo)
                    VALUES (%s, %s, TRUE)
                    ON CONFLICT (gestor_id, zona) DO UPDATE SET
                        ativo = TRUE,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (str(gestor_id), zona),
                )

            cur.execute(
                """
                SELECT g.email, g.nome, g.cargo, array_agg(p.zona ORDER BY p.zona) AS zonas
                FROM school_gestores g
                JOIN school_gestor_perfis p ON p.gestor_id = g.id AND p.ativo
                WHERE g.id = %s
                GROUP BY g.email, g.nome, g.cargo
                """,
                (str(gestor_id),),
            )
            info = cur.fetchone()
            print(
                f"OK sysadmin email={info['email']} cargo={info['cargo']} "
                f"zonas={info['zonas']} instituicao_id={instituicao_id}"
            )
            if generated:
                # Uma linha dedicada para o wrapper gravar em arquivo seguro
                print(f"GENERATED_PASSWORD={password}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
