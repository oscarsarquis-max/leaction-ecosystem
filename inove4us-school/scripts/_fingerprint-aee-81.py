"""Fingerprint catálogo / AEE / org — conferir que o apply não os toca."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from db import get_conn
from psycopg2.extras import RealDictCursor


def fingerprint() -> dict:
    out: dict = {}
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT codigo, nome,
                       md5(COALESCE(passos_execucao::text, '')) AS passos_md5,
                       md5(COALESCE(descricao, '')) AS desc_md5
                FROM public.school_metodologias_catalogo
                WHERE ativo AND origem = 'padrao'
                ORDER BY codigo
                """
            )
            cats = cur.fetchall()
            blob = "|".join(f"{r['codigo']}:{r['passos_md5']}:{r['desc_md5']}" for r in cats)
            out["catalogo"] = {
                "n": len(cats),
                "hash": hashlib.sha256(blob.encode()).hexdigest()[:16],
            }

            cur.execute(
                """
                SELECT id::text, instituicao_id::text, condicao_categoria, versao,
                       status::text,
                       md5(COALESCE(texto_escola, '')) AS t_md5,
                       md5(COALESCE(campos_experiencia_metodologica, '')) AS c_md5
                FROM public.school_aee_matrizes
                ORDER BY instituicao_id, condicao_categoria, versao
                """
            )
            mats = cur.fetchall()
            blob_m = "|".join(
                f"{r['id']}:{r['condicao_categoria']}:{r['versao']}:{r['status']}:{r['t_md5']}:{r['c_md5']}"
                for r in mats
            )
            out["matrizes"] = {
                "n": len(mats),
                "por_condicao": {},
                "hash": hashlib.sha256(blob_m.encode()).hexdigest()[:16],
            }
            for r in mats:
                k = r["condicao_categoria"]
                out["matrizes"]["por_condicao"][k] = out["matrizes"]["por_condicao"].get(k, 0) + 1

            cur.execute(
                """
                SELECT COUNT(*) AS n,
                       COALESCE(md5(string_agg(id::text || COALESCE(passos_customizados, ''), ','
                         ORDER BY id::text)), 'empty') AS hash
                FROM public.school_aee_metodologias_org
                """
            )
            org = cur.fetchone()
            out["org"] = {"n": int(org["n"] or 0), "hash": org["hash"]}

            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name = 'school_aee_metodologias_canonico'
                ) AS exists
                """
            )
            if cur.fetchone()["exists"]:
                cur.execute(
                    """
                    SELECT status, COUNT(*) AS n
                    FROM public.school_aee_metodologias_canonico
                    GROUP BY 1 ORDER BY 1
                    """
                )
                out["canonico"] = [dict(r) for r in cur.fetchall()]
            else:
                out["canonico"] = None
    return out


if __name__ == "__main__":
    print(json.dumps(fingerprint(), ensure_ascii=False, indent=2))
