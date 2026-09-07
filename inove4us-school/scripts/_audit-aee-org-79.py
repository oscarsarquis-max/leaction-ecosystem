from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)

from aee_metodologia_adaptacao import eh_copia_identica, passos_to_text
from db import get_conn
from psycopg2.extras import RealDictCursor

assert eh_copia_identica("", "abc")
assert eh_copia_identica("abc", "abc")
assert not eh_copia_identica("texto da escola", "abc")
print("comparacao ok")

with get_conn() as conn:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT COUNT(*) AS n FROM public.school_metodologias_catalogo
            WHERE ativo AND origem = 'padrao'
            """
        )
        print("catalogo", dict(cur.fetchone()))
        cur.execute(
            "SELECT DISTINCT condicao_categoria FROM public.school_aee_matrizes ORDER BY 1"
        )
        print("matrizes", [r["condicao_categoria"] for r in cur.fetchall()])
        cur.execute("SELECT COUNT(*) AS n FROM public.school_aee_metodologias_org")
        print("org_rows", dict(cur.fetchone()))
        cur.execute(
            """
            SELECT m.condicao_categoria, COUNT(*) AS n,
                   COUNT(*) FILTER (
                     WHERE length(trim(org.passos_customizados)) > 0
                   ) AS nonempty
            FROM public.school_aee_metodologias_org org
            JOIN public.school_aee_matrizes m ON m.id = org.aee_matriz_id
            GROUP BY 1 ORDER BY 1
            """
        )
        print("org_por_condicao", [dict(r) for r in cur.fetchall()])
        cur.execute(
            """
            SELECT
                m.instituicao_id,
                m.condicao_categoria,
                org.metodologia_nome,
                length(trim(org.passos_customizados)) AS nchars,
                c.passos_execucao,
                org.passos_customizados,
                m.campos_experiencia_metodologica
            FROM public.school_aee_metodologias_org org
            JOIN public.school_aee_matrizes m ON m.id = org.aee_matriz_id
            LEFT JOIN public.school_metodologias_aliases a
              ON a.alias_norm = LOWER(TRIM(org.metodologia_nome))
            LEFT JOIN public.school_metodologias_catalogo c
              ON c.codigo = a.codigo
            """
        )
        custom = []
        copias = 0
        for r in cur.fetchall():
            cat = passos_to_text(r.get("passos_execucao"))
            if eh_copia_identica(
                r.get("passos_customizados") or "",
                cat,
                r.get("campos_experiencia_metodologica") or "",
            ):
                copias += 1
            else:
                custom.append(
                    {
                        "instituicao_id": str(r.get("instituicao_id")),
                        "condicao": r.get("condicao_categoria"),
                        "metodologia": r.get("metodologia_nome"),
                        "nchars": r.get("nchars"),
                    }
                )
        print("copias_ou_vazias", copias)
        print("custom_escola", len(custom))
        print(json.dumps(custom, ensure_ascii=False, indent=2))
