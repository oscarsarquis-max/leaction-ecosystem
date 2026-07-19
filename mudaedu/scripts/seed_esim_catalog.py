#!/usr/bin/env python3
"""
Restaura o catálogo eSIM padrão (provedor Base Mobile + 3 eventos de teste).

Idempotente — seguro rodar várias vezes (ON CONFLICT / upsert).
Produção: SEED_DEV_ALLOW=1 e SEED_PROD_CONFIRM=paneldx-esim-catalog
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CATALOG_ROWS = [
    (
        "QDA_ACESSO_PEDAG",
        "Queda de conectividade ou tráfego no acesso a plataformas de aprendizagem (LMS/LXP). "
        "Impacto direto na dimensão LA — risco de interrupção da jornada do aprendiz e perda de engajamento digital.",
        "Aprendizagem em Ação (LA)",
        "Plataformas Digitais (dp)",
        ["Portal de Integração dos Aprendizes", "Ambientes AVA/LMS", "Programas Híbridos"],
    ),
    (
        "GARGALO_ADMN_SEC",
        "Anomalia associada a autenticação, governança de acesso ou políticas de segurança. "
        "Impacto na dimensão DA — risco operacional, conformidade (LGPD) e continuidade dos serviços críticos.",
        "Arquitetura Digital (DA)",
        "Governança Digital (dg)",
        ["Segurança e Redundância", "Identidade e Autenticação", "Privacidade"],
    ),
    (
        "LENTIDAO_TI_SIST",
        "Degradação de performance ou latência em sistemas corporativos. "
        "Impacto na dimensão DA — dívida técnica, conectividade e arquitetura de plataformas digitais.",
        "Arquitetura Digital (DA)",
        "Plataformas Digitais (dp)",
        ["Conectividade e Nuvem", "Mapa de Tecnologia", "Interoperabilidade"],
    ),
]

PROVEDOR_NOME = "Base Mobile"
PROVEDOR_CONFIG = {
    "webhook_path": "/api/webhooks/esim",
    "slug": "basemobile",
}

ENSURE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS public.esim_provedores (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(120) NOT NULL UNIQUE,
    config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    criado_em TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS public.esim_eventos_catalog (
    id SERIAL PRIMARY KEY,
    codigo_evento VARCHAR(64) NOT NULL UNIQUE,
    descricao_tecnica TEXT NOT NULL,
    dimensao_fixada VARCHAR(255) NOT NULL,
    dominio_fixado VARCHAR(255) NOT NULL,
    blocos_candidatos JSONB NOT NULL DEFAULT '[]'::jsonb,
    provedor_id INTEGER NOT NULL REFERENCES public.esim_provedores(id) ON DELETE RESTRICT
);
"""


def load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for path in (ROOT / ".env", ROOT / "LeAction_SysF" / ".env"):
        if path.is_file():
            load_dotenv(path, override=False)


def get_conn():
    import psycopg2

    load_env()
    host = os.getenv("DB_HOST", "127.0.0.1")
    if host not in ("127.0.0.1", "localhost", "::1") and not os.getenv("SEED_DEV_ALLOW"):
        raise SystemExit("Produção bloqueada: defina SEED_DEV_ALLOW=1")
    if host not in ("127.0.0.1", "localhost", "::1"):
        confirm = os.getenv("SEED_PROD_CONFIRM", "")
        if confirm != "paneldx-esim-catalog":
            raise SystemExit(
                "Produção: defina SEED_PROD_CONFIRM=paneldx-esim-catalog"
            )
    return psycopg2.connect(
        host=host,
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "LeAction_SysF"),
        user=os.getenv("DB_USER") or os.getenv("DB_USERNAME", "postgres"),
        password=os.getenv("DB_PASS") or os.getenv("DB_PASSWORD", ""),
        sslmode=os.getenv("DB_SSLMODE", "prefer"),
    )


def seed_catalog(cur) -> tuple[int, int]:
    cur.execute(ENSURE_SCHEMA_SQL)

    cur.execute(
        """
        INSERT INTO public.esim_provedores (nome, config_json)
        VALUES (%s, %s::jsonb)
        ON CONFLICT (nome) DO UPDATE
        SET config_json = EXCLUDED.config_json
        RETURNING id;
        """,
        (PROVEDOR_NOME, json.dumps(PROVEDOR_CONFIG)),
    )
    provedor_id = cur.fetchone()[0]

    for codigo, desc, dim, dom, blocos in CATALOG_ROWS:
        cur.execute(
            """
            INSERT INTO public.esim_eventos_catalog
                (codigo_evento, descricao_tecnica, dimensao_fixada, dominio_fixado,
                 blocos_candidatos, provedor_id)
            VALUES (%s, %s, %s, %s, %s::jsonb, %s)
            ON CONFLICT (codigo_evento) DO UPDATE
            SET descricao_tecnica = EXCLUDED.descricao_tecnica,
                dimensao_fixada = EXCLUDED.dimensao_fixada,
                dominio_fixado = EXCLUDED.dominio_fixado,
                blocos_candidatos = EXCLUDED.blocos_candidatos,
                provedor_id = EXCLUDED.provedor_id;
            """,
            (codigo, desc, dim, dom, json.dumps(blocos), provedor_id),
        )

    cur.execute("SELECT COUNT(*) FROM public.esim_provedores;")
    n_prov = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM public.esim_eventos_catalog;")
    n_cat = cur.fetchone()[0]
    return n_prov, n_cat


def main() -> int:
    conn = get_conn()
    cur = conn.cursor()
    try:
        print("==> Restaurando catálogo eSIM (Base Mobile + 3 eventos)...")
        n_prov, n_cat = seed_catalog(cur)
        conn.commit()
        print(f"    [OK] esim_provedores: {n_prov} | esim_eventos_catalog: {n_cat}")
        return 0
    except Exception as exc:
        conn.rollback()
        print(f"    [ERRO] {exc}", file=sys.stderr)
        return 1
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
