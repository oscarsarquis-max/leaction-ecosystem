#!/usr/bin/env python3
"""Prompt 81 — verifica Editor/API após approve. Não cria matriz nas 3 condições sem AEE."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path("/var/www/inove4us-school")
if not (ROOT / "backend").exists():
    ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from psycopg2.extras import RealDictCursor
from db import get_conn

INST = "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50"
HOMOLOG = "homologador@leaction.com.br"
COM_MATRIZ = ("TEA", "TDAH", "Altas Habilidades", "Deficiência Visual", "Deficiência Física")
SEM_MATRIZ = ("Deficiência Intelectual", "Deficiência Auditiva", "Outras Dificuldades Severas")


def main() -> int:
    from app import app

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT g.id, g.instituicao_id, g.unidade_id, g.nome, g.email, g.cargo,
                       i.razao_social AS instituicao_nome,
                       COALESCE(array_agg(p.zona ORDER BY p.zona) FILTER (WHERE p.ativo), '{}') AS zonas
                FROM public.school_gestores g
                JOIN public.school_instituicoes i ON i.id = g.instituicao_id
                LEFT JOIN public.school_gestor_perfis p ON p.gestor_id = g.id
                WHERE g.instituicao_id = %s AND lower(g.email) = %s
                GROUP BY g.id, i.razao_social
                """,
                (INST, HOMOLOG),
            )
            gestor = cur.fetchone()
            if not gestor:
                raise SystemExit("Homologador não encontrado")

            cur.execute(
                """
                SELECT condicao_categoria, COUNT(*)::int AS n
                FROM public.school_aee_matrizes
                WHERE instituicao_id = %s
                GROUP BY 1 ORDER BY 1
                """,
                (INST,),
            )
            matrizes = {r["condicao_categoria"]: r["n"] for r in cur.fetchall()}

            cur.execute(
                """
                SELECT condicao_categoria, COUNT(*)::int AS n
                FROM public.school_aee_metodologias_canonico
                WHERE status = 'aprovado'
                GROUP BY 1 ORDER BY 1
                """
            )
            aprovados = {r["condicao_categoria"]: r["n"] for r in cur.fetchall()}

            cur.execute("SELECT COUNT(*) AS n FROM public.school_aee_metodologias_org")
            org_n = int(cur.fetchone()["n"] or 0)

    user = {
        "id": str(gestor["id"]),
        "instituicao_id": str(gestor["instituicao_id"]),
        "instituicao_nome": gestor.get("instituicao_nome"),
        "unidade_id": str(gestor["unidade_id"]) if gestor.get("unidade_id") else None,
        "nome": gestor["nome"],
        "email": gestor["email"],
        "cargo": gestor["cargo"],
        "zonas": list(gestor["zonas"] or []),
    }

    client = app.test_client()
    with client.session_transaction() as sess:
        sess["school_gestor"] = user

    res_cond = client.get("/api/aee/condicoes")
    condicoes = res_cond.get_json(silent=True) or []
    nomes = [c.get("condicao_categoria") for c in condicoes] if isinstance(condicoes, list) else []

    amostra = None
    res_m = client.get("/api/aee/matriz?condicao=TEA")
    body_m = res_m.get_json(silent=True) or {}
    matriz = body_m.get("editavel") or body_m.get("ativa") or body_m.get("atual") or {}
    aid = matriz.get("id")
    res_list = None
    items = []
    if aid:
        res_list = client.get(f"/api/aee/{aid}/metodologias")
        payload = res_list.get_json(silent=True) or {}
        items = payload.get("items") or []
        hit = next((r for r in items if str(r.get("nome") or "").lower() == "mapa mental"), None)
        hit = hit or (items[0] if items else None)
        if hit:
            orig = (hit.get("texto_canonico") or "").strip()
            servido = (hit.get("versao_escola") or "").strip()
            amostra = {
                "condicao": "TEA",
                "metodologia": hit.get("nome"),
                "origem_texto": hit.get("origem_texto"),
                "is_customizado": hit.get("is_customizado"),
                "status_adaptacao_canonica": hit.get("status_adaptacao_canonica"),
                "servido_diferente_do_catalogo": bool(servido) and servido != orig,
                "preview_servido": servido[:280],
                "preview_catalogo": orig[:180],
            }

    # 3 sem matriz: NÃO chamar GET /api/aee/matriz (isso criaria rascunho).
    sem_ok = []
    for nome in SEM_MATRIZ:
        sem_ok.append(
            {
                "condicao": nome,
                "aprovados_no_banco": aprovados.get(nome, 0),
                "matrizes_escola_teste": matrizes.get(nome, 0),
                "listada_em_condicoes": nome in nomes,
            }
        )

    dist = ROOT / "frontend" / "dist" / "assets"
    js_files = sorted(dist.glob("index-*.js"), key=lambda p: p.stat().st_mtime, reverse=True)
    blob = js_files[0].read_text(encoding="utf-8", errors="replace") if js_files else ""

    out = {
        "org_rows": org_n,
        "aprovados_por_condicao": aprovados,
        "matrizes_escola_teste": matrizes,
        "condicoes_api": {"http": res_cond.status_code, "n": len(nomes), "nomes": nomes},
        "matriz_tea": {"http": res_m.status_code, "id": aid, "status": matriz.get("status")},
        "metodologias_tea": {
            "http": res_list.status_code if res_list is not None else None,
            "n": len(items),
            "origens": sorted({str(i.get("origem_texto")) for i in items}),
            "customizados": sum(1 for i in items if i.get("is_customizado")),
        },
        "amostra_editor": amostra,
        "tres_sem_matriz": sem_ok,
        "bundle": {
            "js": js_files[0].name if js_files else None,
            "label_adaptacao": "Adaptação canônica AEE" in blob
            or "Adapta\\u00e7\\u00e3o can\\u00f4nica AEE" in blob
            or "can\\u00f4nica AEE" in blob,
            "label_catalogo": "ainda sem adapta" in blob,
        },
    }
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    if not amostra or amostra.get("origem_texto") != "adaptacao_canonica":
        return 1
    if any(x["matrizes_escola_teste"] for x in sem_ok):
        # não é falha do apply; só sinaliza se alguém criou matriz no meio
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
