#!/usr/bin/env python3
"""Confere espelho 95 + regressão EF06MA07. Sem senhas."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path("/var/www/inove4us-school")
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)
from db import get_conn
from psycopg2.extras import RealDictCursor

from radar_home import _row_aula, montar_cobertura

INST = "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50"

with get_conn() as conn:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT p.id, p.conteudo_resumo, p.mesa_payload_json, p.updated_at
              FROM public.school_planos_aula_espelhados p
             WHERE p.mesa_payload_json::text ILIKE %s
                OR p.conteudo_resumo ILIKE %s
             ORDER BY p.updated_at DESC NULLS LAST
             LIMIT 5
            """,
            ("%Cobertura 95%", "%Cobertura 95%"),
        )
        prova = [dict(r) for r in cur.fetchall()]
        cur.execute(
            """
            SELECT COUNT(*) AS n
              FROM public.school_planos_aula_espelhados p
             WHERE p.instituicao_id = %s
               AND (
                    p.mesa_payload_json->>'habilidade_codigo' = %s
                 OR p.mesa_payload_json::text ILIKE %s
               )
            """,
            (INST, "EF06MA07", "%EF06MA07%"),
        )
        n_ef06 = cur.fetchone()["n"]
        cur.execute(
            """
            SELECT disciplina_nome, curso_ano, habilidade_codigo
              FROM public.school_bncc_temas_canonico
             WHERE status = 'aprovado'
               AND disciplina_nome = 'Matemática'
               AND curso_ano = '6º ano'
            """
        )
        catalogo = [dict(r) for r in cur.fetchall()]

aulas = [_row_aula(r) for r in prova]
codes = []
if aulas:
    codes = aulas[0].get("habilidade_codigos") or []
cob = montar_cobertura(catalogo, aulas) if aulas else {}

print(
    json.dumps(
        {
            "espelhos_prova95": len(prova),
            "codigos_espelho": codes,
            "mesa_habilidade_codigos": (prova[0]["mesa_payload_json"] or {}).get("habilidade_codigos")
            if prova
            else None,
            "mesa_habilidade_codigo": (prova[0]["mesa_payload_json"] or {}).get("habilidade_codigo")
            if prova
            else None,
            "cobertura_itens": cob.get("itens"),
            "aulas_com_ef06ma07": n_ef06,
        },
        ensure_ascii=False,
        indent=2,
        default=str,
    )
)
