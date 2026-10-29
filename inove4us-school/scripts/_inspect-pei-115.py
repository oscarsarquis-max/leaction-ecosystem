#!/usr/bin/env python3
"""115 — snapshot PEI/AEE Escola Teste. Sem senhas."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path("/var/www/inove4us-school")
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from psycopg2.extras import RealDictCursor  # noqa: E402
from db import get_conn  # noqa: E402

INST = "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50"


def slim(rows, keys):
    out = []
    for r in rows or []:
        item = {}
        for k in keys:
            v = r.get(k)
            item[k] = str(v) if v is not None and k.endswith("_id") or k == "id" else v
            if hasattr(v, "isoformat"):
                item[k] = v.isoformat()
            elif k in ("id", "aluno_id", "aee_matriz_id", "periodo_letivo_id", "pei_linha_id"):
                item[k] = str(v) if v else None
        out.append(item)
    return out


def main() -> int:
    out: dict = {}
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT g.email, g.nome, g.cargo, g.ativo,
                       COALESCE(array_agg(p.zona ORDER BY p.zona) FILTER (WHERE p.ativo), '{}') AS zonas
                FROM public.school_gestores g
                LEFT JOIN public.school_gestor_perfis p ON p.gestor_id = g.id
                WHERE g.instituicao_id = %s
                GROUP BY g.id
                ORDER BY g.email
                """,
                (INST,),
            )
            out["gestores"] = [
                {"email": r["email"], "nome": r["nome"], "cargo": r["cargo"], "zonas": list(r["zonas"] or [])}
                for r in cur.fetchall()
            ]
            cur.execute(
                """
                SELECT condicao_categoria, versao, status,
                       assinado_coordenador, assinado_psicopedagogo,
                       left(texto_escola, 80) AS texto_preview, id
                FROM public.school_aee_matrizes
                WHERE instituicao_id = %s
                ORDER BY condicao_categoria, versao DESC
                """,
                (INST,),
            )
            out["aee"] = [
                {
                    "id": str(r["id"]),
                    "condicao": r["condicao_categoria"],
                    "versao": r["versao"],
                    "status": str(r["status"]),
                    "coord": bool(r["assinado_coordenador"]),
                    "psico": bool(r["assinado_psicopedagogo"]),
                    "texto": r["texto_preview"],
                }
                for r in cur.fetchall()
            ]
            cur.execute(
                """
                SELECT p.id, p.nome_completo, p.status, p.versao,
                       p.assinado_coordenador, p.assinado_psicopedagogo,
                       p.periodo_letivo_id, p.aluno_id, p.aee_matriz_id,
                       m.condicao_categoria, m.versao AS aee_versao, m.status AS aee_status
                FROM public.school_pei_alunos p
                JOIN public.school_aee_matrizes m ON m.id = p.aee_matriz_id
                WHERE p.instituicao_id = %s
                ORDER BY p.created_at DESC
                LIMIT 20
                """,
                (INST,),
            )
            out["peis"] = [
                {
                    "id": str(r["id"]),
                    "aluno": r["nome_completo"],
                    "aluno_id": str(r["aluno_id"]) if r.get("aluno_id") else None,
                    "status": r["status"],
                    "versao": r["versao"],
                    "coord": bool(r["assinado_coordenador"]),
                    "psico": bool(r["assinado_psicopedagogo"]),
                    "periodo": str(r["periodo_letivo_id"]) if r.get("periodo_letivo_id") else None,
                    "aee_id": str(r["aee_matriz_id"]),
                    "condicao": r["condicao_categoria"],
                    "aee_versao": r["aee_versao"],
                    "aee_status": str(r["aee_status"]),
                }
                for r in cur.fetchall()
            ]
            cur.execute(
                """
                SELECT id, rotulo, data_inicio, data_fim
                FROM public.school_periodos_letivos
                WHERE instituicao_id = %s
                ORDER BY data_inicio DESC
                LIMIT 8
                """,
                (INST,),
            )
            out["periodos"] = [
                {
                    "id": str(r["id"]),
                    "rotulo": r["rotulo"],
                    "inicio": str(r["data_inicio"]),
                    "fim": str(r["data_fim"]),
                }
                for r in cur.fetchall()
            ]
            cur.execute(
                """
                SELECT a.id, a.nome, a.matricula, a.ativo, t.nome AS turma
                FROM public.school_alunos a
                LEFT JOIN public.school_turmas t ON t.id = a.turma_id
                WHERE a.instituicao_id = %s
                ORDER BY a.nome
                """,
                (INST,),
            )
            out["alunos"] = [
                {
                    "id": str(r["id"]),
                    "nome": r["nome"],
                    "matricula": r["matricula"],
                    "ativo": r["ativo"],
                    "turma": r["turma"],
                }
                for r in cur.fetchall()
            ]
            cur.execute(
                """
                SELECT t.id, t.nome FROM public.school_turmas t
                WHERE t.instituicao_id = %s ORDER BY t.nome LIMIT 6
                """,
                (INST,),
            )
            out["turmas"] = [{"id": str(r["id"]), "nome": r["nome"]} for r in cur.fetchall()]
    print(json.dumps(out, default=str, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
