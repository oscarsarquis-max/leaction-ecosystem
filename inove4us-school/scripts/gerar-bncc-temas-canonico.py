#!/usr/bin/env python3
"""Recorte Escola Teste: temas canônicos BNCC (pendente_revisao) + relatório.

Não marca aprovado. Não altera ementa da escola.
Rótulo do tema vem de campo oficial do import (objeto único ou unidade temática).

Uso:
  python scripts/gerar-bncc-temas-canonico.py
  python scripts/gerar-bncc-temas-canonico.py --report-only
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from bncc_oficial import (  # noqa: E402
    DATASET_VERSAO,
    MAPA_DISCIPLINA,
    ORIGEM,
    STATUS_PENDENTE,
    cache_dir,
    flatten_dataset,
    rotulo_tema,
    skill_matches_filter,
)
from psycopg2.extras import RealDictCursor  # noqa: E402

INST = "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50"
OUT_DIR = ROOT / "var" / "bncc-temas-revisao"
JSON_OUT = OUT_DIR / "lote.json"
CSV_OUT = OUT_DIR / "relatorio-disciplina-ano-tema-habilidade.csv"
HTML_OUT = OUT_DIR / "relatorio-revisao.html"
README_OUT = OUT_DIR / "README.md"

FALLBACK_ESCOPO = [
    {"curso_nome": "Ensino Fundamental II", "curso_ano": "6º ano", "etapa": "EF", "ano_num": 6,
     "disciplinas": ["Matemática", "Língua Portuguesa", "Ciências", "História", "Geografia", "Inglês", "Arte", "Educação Física"]},
    {"curso_nome": "Ensino Médio", "curso_ano": "1ª série", "etapa": "EM", "ano_num": None,
     "disciplinas": ["Matemática", "Língua Portuguesa", "História", "Geografia", "Inglês", "Arte", "Educação Física", "Biologia"]},
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_oficial_rows() -> list[dict]:
    data_dir = cache_dir(ROOT)
    if (data_dir / "ensino-fundamental.json").exists():
        return flatten_dataset(data_dir)
    from db import get_conn

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT codigo, etapa, componente_id, componente_nome, area_id, area_nome,
                       anos, unidade_tematica, objetos_conhecimento, texto
                FROM public.bncc_habilidades_oficial
                """
            )
            rows = [dict(r) for r in cur.fetchall()]
    for r in rows:
        objs = str(r.get("objetos_conhecimento") or "")
        r["objetos_nomes"] = [p.strip() for p in objs.split(";") if p.strip()]
    return rows


def load_escopo_escola() -> tuple[list[dict], str]:
    try:
        from db import get_conn

        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT c.id AS curso_id, c.nome AS curso_nome, c.nivel,
                           t.nome AS turma_nome, t.serie_ano
                    FROM public.school_cursos c
                    JOIN public.school_periodos_letivos p ON p.id = c.periodo_letivo_id
                    LEFT JOIN public.school_turmas t ON t.curso_id = c.id
                    WHERE p.instituicao_id = %s
                    ORDER BY c.nome, t.nome
                    """,
                    (INST,),
                )
                cursos = [dict(r) for r in cur.fetchall()]
                cur.execute(
                    """
                    SELECT d.id, d.nome, d.ementa, c.id AS curso_id, c.nome AS curso_nome, c.nivel
                    FROM public.school_disciplinas d
                    JOIN public.school_curso_disciplinas cd ON cd.disciplina_id = d.id
                    JOIN public.school_cursos c ON c.id = cd.curso_id
                    JOIN public.school_periodos_letivos p ON p.id = c.periodo_letivo_id
                    WHERE p.instituicao_id = %s AND d.ativo IS NOT FALSE
                    ORDER BY c.nome, d.nome
                    """,
                    (INST,),
                )
                discs = [dict(r) for r in cur.fetchall()]
        if not discs:
            return FALLBACK_ESCOPO, "fallback_seed70_sem_disciplinas"
        by_curso: dict[str, dict] = {}
        for d in discs:
            key = str(d["curso_id"])
            slot = by_curso.setdefault(
                key,
                {
                    "curso_id": key,
                    "curso_nome": d["curso_nome"],
                    "nivel": d.get("nivel") or "",
                    "disciplinas": [],
                    "disciplina_ids": {},
                    "turmas": [],
                },
            )
            nome = str(d["nome"]).strip()
            if nome not in slot["disciplinas"]:
                slot["disciplinas"].append(nome)
            slot["disciplina_ids"][nome] = str(d["id"])
        for c in cursos:
            key = str(c["curso_id"])
            if key in by_curso and c.get("turma_nome"):
                by_curso[key]["turmas"].append(
                    {"nome": c["turma_nome"], "serie_ano": c.get("serie_ano")}
                )
        escopo = []
        for slot in by_curso.values():
            nivel = str(slot.get("nivel") or "").lower()
            nome_curso = str(slot["curso_nome"] or "")
            if "fundamental" in nivel or "fundamental" in nome_curso.lower():
                etapa, curso_ano, ano_num = "EF", "6º ano", 6
            elif "medio" in nivel or "médio" in nome_curso.lower():
                etapa, curso_ano, ano_num = "EM", "1ª série", None
            else:
                continue
            escopo.append(
                {
                    "curso_id": slot["curso_id"],
                    "curso_nome": slot["curso_nome"],
                    "curso_ano": curso_ano,
                    "etapa": etapa,
                    "ano_num": ano_num,
                    "disciplinas": slot["disciplinas"],
                    "disciplina_ids": slot["disciplina_ids"],
                    "turmas": slot["turmas"],
                }
            )
        if escopo:
            return escopo, "escola_teste_prod"
    except Exception as exc:
        print(f"[gerar] DB indisponível ({exc}); usando fallback seed 70.", file=sys.stderr)
    return FALLBACK_ESCOPO, "fallback_seed70"


def build_temas(oficial: list[dict], escopo: list[dict]) -> list[dict]:
    out = []
    for bloco in escopo:
        etapa = bloco["etapa"]
        for disc in bloco["disciplinas"]:
            spec_all = MAPA_DISCIPLINA.get(disc) or {}
            spec = spec_all.get(etapa)
            if not spec:
                out.append(
                    {
                        "disciplina_nome": disc,
                        "disciplina_id": (bloco.get("disciplina_ids") or {}).get(disc),
                        "curso_id": bloco.get("curso_id"),
                        "curso_nome": bloco.get("curso_nome"),
                        "curso_ano": bloco["curso_ano"],
                        "etapa": etapa,
                        "tema": None,
                        "habilidade_codigo": None,
                        "texto_oficial": None,
                        "agrupamento_fonte": None,
                        "desvio": f"sem mapeamento BNCC para {disc} {etapa}",
                    }
                )
                continue
            hits = [
                r
                for r in oficial
                if r.get("etapa") == etapa
                and skill_matches_filter(r, spec, ano=bloco.get("ano_num"))
            ]
            for r in hits:
                tema, fonte = rotulo_tema(r)
                out.append(
                    {
                        "disciplina_nome": disc,
                        "disciplina_id": (bloco.get("disciplina_ids") or {}).get(disc),
                        "curso_id": bloco.get("curso_id"),
                        "curso_nome": bloco.get("curso_nome"),
                        "curso_ano": bloco["curso_ano"],
                        "etapa": etapa,
                        "tema": tema,
                        "habilidade_codigo": r["codigo"],
                        "texto_oficial": r["texto"],
                        "unidade_tematica": r.get("unidade_tematica"),
                        "objetos_conhecimento": r.get("objetos_conhecimento"),
                        "agrupamento_fonte": fonte,
                        "desvio": None,
                    }
                )
    return out


def write_report(items: list[dict], escopo: list[dict], origem_escopo: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ok = [i for i in items if i.get("habilidade_codigo")]
    payload = {
        "gerado_em": _utc(),
        "dataset_versao": DATASET_VERSAO,
        "origem_escopo": origem_escopo,
        "status": STATUS_PENDENTE,
        "escopo": escopo,
        "contagem": {
            "temas": len(ok),
            "disciplinas_ano": len({(i["disciplina_nome"], i["curso_ano"]) for i in ok}),
        },
        "items": ok,
        "sem_mapeamento": [i for i in items if not i.get("habilidade_codigo")],
    }
    JSON_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    with CSV_OUT.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(
            [
                "disciplina",
                "curso",
                "ano",
                "tema",
                "habilidade_codigo",
                "texto_oficial",
                "agrupamento_fonte",
            ]
        )
        for i in ok:
            w.writerow(
                [
                    i["disciplina_nome"],
                    i.get("curso_nome") or "",
                    i["curso_ano"],
                    i["tema"],
                    i["habilidade_codigo"],
                    i["texto_oficial"],
                    i["agrupamento_fonte"],
                ]
            )

    rows_html = []
    for i in ok:
        rows_html.append(
            "<tr>"
            f"<td>{html.escape(i['disciplina_nome'])}</td>"
            f"<td>{html.escape(i.get('curso_nome') or '')}</td>"
            f"<td>{html.escape(i['curso_ano'])}</td>"
            f"<td>{html.escape(i['tema'])}</td>"
            f"<td><code>{html.escape(i['habilidade_codigo'])}</code></td>"
            f"<td>{html.escape(i['texto_oficial'])}</td>"
            "</tr>"
        )
    HTML_OUT.write_text(
        f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<title>Revisão BNCC temas — Escola Teste</title>
<style>
body {{ font-family: sans-serif; margin: 24px; color: #1a1a1a; }}
table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
th, td {{ border: 1px solid #ccc; padding: 6px 8px; vertical-align: top; }}
th {{ background: #f4f1ea; position: sticky; top: 0; }}
code {{ font-size: 12px; }}
.note {{ background: #fff8e6; padding: 12px; border-radius: 8px; }}
</style></head><body>
<h1>Catálogo canônico BNCC — revisão (prompt 85)</h1>
<p class="note">Status: <strong>pendente_revisao</strong>. Não publica no Dia a Dia até
<code>python scripts/aplicar-bncc-temas-canonico.py --approve</code>.
Texto e código das habilidades vêm de <code>{html.escape(DATASET_VERSAO)}</code>
(bncc-dev/bncc-dados). O tema é rótulo extraído de campo oficial (objeto único ou
unidade temática / competência específica), sem paráfrase do enunciado.
Ementa livre da escola não foi alterada.</p>
<p>{len(ok)} temas · {payload['contagem']['disciplinas_ano']} pares disciplina×ano · escopo {html.escape(origem_escopo)}</p>
<table>
<thead><tr><th>Disciplina</th><th>Curso</th><th>Ano</th><th>Tema</th><th>Habilidade</th><th>Texto oficial</th></tr></thead>
<tbody>
{''.join(rows_html)}
</tbody></table>
</body></html>
""",
        encoding="utf-8",
    )
    README_OUT.write_text(
        f"""# Revisão — temas BNCC (prompt 85)

Status: **pendente_revisao**. Abrir `{HTML_OUT.name}` ou a planilha CSV.

Fonte oficial: bncc-dev/bncc-dados `{DATASET_VERSAO}`.

Depois do OK do Oscar:

```
python scripts/aplicar-bncc-temas-canonico.py --approve
```

Isso marca `school_bncc_temas_canonico.status = aprovado`. O seletor do Dia a Dia
passa a oferecer esses temas **além** da ementa livre da escola.
""",
        encoding="utf-8",
    )


def upsert_temas(items: list[dict]) -> int:
    from db import get_conn

    ok = [i for i in items if i.get("habilidade_codigo")]
    sql = """
        INSERT INTO public.school_bncc_temas_canonico (
            disciplina_nome, disciplina_id, curso_id, curso_ano, etapa,
            tema, habilidade_codigo, origem, status, agrupamento_fonte,
            gerado_em, updated_at
        ) VALUES (
            %(disciplina_nome)s, %(disciplina_id)s, %(curso_id)s, %(curso_ano)s, %(etapa)s,
            %(tema)s, %(habilidade_codigo)s, %(origem)s, %(status)s, %(agrupamento_fonte)s,
            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        )
        ON CONFLICT (disciplina_nome, curso_ano, habilidade_codigo) DO UPDATE SET
            tema = EXCLUDED.tema,
            disciplina_id = COALESCE(EXCLUDED.disciplina_id, school_bncc_temas_canonico.disciplina_id),
            curso_id = COALESCE(EXCLUDED.curso_id, school_bncc_temas_canonico.curso_id),
            agrupamento_fonte = EXCLUDED.agrupamento_fonte,
            updated_at = CURRENT_TIMESTAMP
        WHERE school_bncc_temas_canonico.status = 'pendente_revisao'
    """
    payload = [
        {
            "disciplina_nome": i["disciplina_nome"],
            "disciplina_id": i.get("disciplina_id"),
            "curso_id": i.get("curso_id"),
            "curso_ano": i["curso_ano"],
            "etapa": i["etapa"],
            "tema": i["tema"],
            "habilidade_codigo": i["habilidade_codigo"],
            "origem": ORIGEM,
            "status": STATUS_PENDENTE,
            "agrupamento_fonte": i["agrupamento_fonte"],
        }
        for i in ok
    ]
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(sql, payload)
    return len(payload)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report-only", action="store_true")
    args = ap.parse_args()

    oficial = load_oficial_rows()
    print(f"==> oficial {len(oficial)}", flush=True)
    escopo, origem = load_escopo_escola()
    print(f"==> escopo {origem} cursos={len(escopo)}", flush=True)
    for b in escopo:
        print(f"    {b.get('curso_nome')} / {b['curso_ano']}: {', '.join(b['disciplinas'])}")
    items = build_temas(oficial, escopo)
    write_report(items, escopo, origem)
    ok = [i for i in items if i.get("habilidade_codigo")]
    print(f"==> relatorio {len(ok)} temas -> {HTML_OUT}")
    if args.report_only:
        return 0
    n = upsert_temas(items)
    print(f"==> gravados pendente_revisao={n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
