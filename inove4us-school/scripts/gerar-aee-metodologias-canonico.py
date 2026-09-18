#!/usr/bin/env python3
"""Lote único: gera cards AEE × metodologia (terceiro artefato) para revisão humana.

Não edita o catálogo das 39 nem school_aee_matrizes.
Não marca status=aprovado (o Editor só herda depois de `aplicar-aee-metodologias-canonico.py`).
Não grava em school_aee_metodologias_org (versão da escola).

Uso:
  python scripts/gerar-aee-metodologias-canonico.py
  python scripts/gerar-aee-metodologias-canonico.py --limit 2 --allow-stub
  python scripts/gerar-aee-metodologias-canonico.py --resume
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)
_INOVE_ENV = ROOT.parent / "inove4us" / ".env"
if _INOVE_ENV.exists():
    # Credenciais Bedrock do B2C local, se o School não tiver AWS_* próprio.
    load_dotenv(_INOVE_ENV, override=False)

from aee_canonico import AEE_CANONICO, CONDICOES_ORDEM  # noqa: E402
from aee_metodologia_adaptacao import (  # noqa: E402
    STATUS_PENDENTE,
    eh_copia_identica,
    ensure_canonico_schema,
    gerar_card_adaptado,
    normalizar_para_comparacao,
    passos_to_text,
)

OUT_DIR = ROOT / "var" / "aee-adaptacoes-revisao"
CHECKPOINT = OUT_DIR / "_checkpoint.json"
JSON_OUT = OUT_DIR / "lote.json"
CSV_OUT = OUT_DIR / "relatorio-original-vs-adaptado.csv"
HTML_OUT = OUT_DIR / "relatorio-revisao.html"
AUDIT_OUT = OUT_DIR / "auditoria-org.json"
CATALOGO_JSON = BACKEND / "data" / "metodologias_padrao_39.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_catalogo() -> list[dict]:
    try:
        from db import get_conn
        from psycopg2.extras import RealDictCursor

        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT codigo, nome, categoria, passos_execucao
                    FROM public.school_metodologias_catalogo
                    WHERE ativo = TRUE AND origem = 'padrao'
                    ORDER BY categoria, nome
                    """
                )
                rows = cur.fetchall()
        if rows:
            return [dict(r) for r in rows]
    except Exception as exc:
        print(f"[lote] catálogo via DB indisponível ({exc}); usando JSON.", file=sys.stderr)

    data = json.loads(CATALOGO_JSON.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise SystemExit("Catálogo das 39 vazio.")
    return data


def _auditar_org() -> dict:
    """Não escreve em org. Só classifica cópia vs customização real."""
    out = {
        "disponivel": False,
        "total_org": 0,
        "copias_identicas_ou_vazias": 0,
        "customizados_escola": 0,
        "customizados": [],
        "erro": None,
    }
    try:
        from db import get_conn
        from psycopg2.extras import RealDictCursor

        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        org.id,
                        org.aee_matriz_id,
                        m.instituicao_id,
                        m.condicao_categoria,
                        org.metodologia_nome,
                        org.passos_customizados,
                        c.codigo AS metodologia_codigo,
                        c.passos_execucao,
                        m.campos_experiencia_metodologica
                    FROM public.school_aee_metodologias_org org
                    JOIN public.school_aee_matrizes m ON m.id = org.aee_matriz_id
                    LEFT JOIN public.school_metodologias_aliases a
                      ON a.alias_norm = LOWER(TRIM(org.metodologia_nome))
                    LEFT JOIN public.school_metodologias_catalogo c
                      ON c.codigo = a.codigo
                    """
                )
                rows = cur.fetchall()
        out["disponivel"] = True
        out["total_org"] = len(rows)
        for r in rows:
            cat = passos_to_text(r.get("passos_execucao"))
            aee = r.get("campos_experiencia_metodologica") or ""
            org_txt = r.get("passos_customizados") or ""
            if eh_copia_identica(org_txt, cat, aee):
                out["copias_identicas_ou_vazias"] += 1
            else:
                out["customizados_escola"] += 1
                out["customizados"].append(
                    {
                        "instituicao_id": str(r.get("instituicao_id") or ""),
                        "condicao_categoria": r.get("condicao_categoria"),
                        "metodologia_nome": r.get("metodologia_nome"),
                        "metodologia_codigo": r.get("metodologia_codigo"),
                        "aee_matriz_id": str(r.get("aee_matriz_id") or ""),
                    }
                )
    except Exception as exc:
        out["erro"] = str(exc)
    return out


def _load_checkpoint() -> dict:
    if not CHECKPOINT.exists():
        return {"items": {}}
    return json.loads(CHECKPOINT.read_text(encoding="utf-8"))


def _save_checkpoint(data: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CHECKPOINT.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _chave(condicao: str, codigo: str) -> str:
    return f"{condicao}||{codigo}"


def _escrever_relatorios(items: list[dict], auditoria: dict, gerado_em: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "gerado_em": gerado_em,
        "status": STATUS_PENDENTE,
        "observacao": (
            "Lote para revisão humana. Não servir no Editor até "
            "scripts/aplicar-aee-metodologias-canonico.py --approve."
        ),
        "contagens": _contagens(items),
        "auditoria_org": auditoria,
        "items": items,
    }
    JSON_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    AUDIT_OUT.write_text(json.dumps(auditoria, ensure_ascii=False, indent=2), encoding="utf-8")

    with CSV_OUT.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(
            [
                "condicao_categoria",
                "metodologia_codigo",
                "metodologia_nome",
                "categoria",
                "status_geracao",
                "original",
                "aee_campos",
                "adaptado",
                "igual_ao_original",
            ]
        )
        for it in items:
            orig = it.get("original") or ""
            adp = it.get("adaptado") or ""
            w.writerow(
                [
                    it.get("condicao_categoria"),
                    it.get("metodologia_codigo"),
                    it.get("metodologia_nome"),
                    it.get("categoria"),
                    it.get("status_geracao"),
                    orig,
                    it.get("aee_campos") or "",
                    adp,
                    "sim"
                    if normalizar_para_comparacao(orig)
                    == normalizar_para_comparacao(adp)
                    else "nao",
                ]
            )

    _escrever_html(items, auditoria, gerado_em)


def _contagens(items: list[dict]) -> dict:
    por_condicao: dict[str, int] = {}
    ok = 0
    erro = 0
    iguais = 0
    for it in items:
        cond = it.get("condicao_categoria") or "?"
        por_condicao[cond] = por_condicao.get(cond, 0) + 1
        if it.get("status_geracao") == "ok":
            ok += 1
            if normalizar_para_comparacao(it.get("original") or "") == normalizar_para_comparacao(
                it.get("adaptado") or ""
            ):
                iguais += 1
        else:
            erro += 1
    return {
        "total": len(items),
        "ok": ok,
        "erro": erro,
        "iguais_ao_original": iguais,
        "por_condicao": por_condicao,
        "metodologias": len({it.get("metodologia_codigo") for it in items}),
        "condicoes": len(por_condicao),
    }


def _escrever_html(items: list[dict], auditoria: dict, gerado_em: str) -> None:
    condicoes = sorted({it.get("condicao_categoria") or "" for it in items})
    opts = "".join(f'<option value="{html.escape(c)}">{html.escape(c)}</option>' for c in condicoes)
    rows = []
    for it in items:
        orig = html.escape(it.get("original") or "")
        adp = html.escape(it.get("adaptado") or "")
        err = html.escape(it.get("erro") or "")
        rows.append(
            "<tr data-condicao=\"{cond}\">"
            "<td>{cond}</td><td>{nome}</td><td>{st}</td>"
            "<td><pre>{orig}</pre></td><td><pre>{adp}</pre>{err}</td>"
            "</tr>".format(
                cond=html.escape(it.get("condicao_categoria") or ""),
                nome=html.escape(it.get("metodologia_nome") or ""),
                st=html.escape(it.get("status_geracao") or ""),
                orig=orig,
                adp=adp,
                err=f'<p class="err">{err}</p>' if err else "",
            )
        )
    custom_n = auditoria.get("customizados_escola") or 0
    doc = f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8"/>
<title>Revisão AEE × metodologia</title>
<style>
body {{ font-family: Georgia, serif; margin: 1.5rem; color: #1e293b; }}
h1 {{ font-size: 1.4rem; }}
.meta {{ color: #475569; font-size: 0.9rem; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #e2e8f0; vertical-align: top; padding: 0.6rem; }}
th {{ background: #f8fafc; text-align: left; }}
pre {{ white-space: pre-wrap; font-family: inherit; margin: 0; font-size: 0.85rem; }}
.err {{ color: #b91c1c; }}
td:nth-child(4), td:nth-child(5) {{ width: 38%; }}
</style></head><body>
<h1>Revisão — Adaptações metodológicas (AEE × catálogo)</h1>
<p class="meta">Gerado em {html.escape(gerado_em)}. Status: <strong>pendente de revisão</strong>.
Nada disto é servido no Editor até aprovação explícita.</p>
<p class="meta">Registros customizados pela escola (intocados): {custom_n}.</p>
<p><label>Filtrar condição:
<select id="f" onchange="filtrar()">
<option value="">Todas</option>{opts}
</select></label></p>
<table><thead><tr>
<th>Condição</th><th>Metodologia</th><th>Status</th>
<th>Original (catálogo)</th><th>Adaptado (card modificado)</th>
</tr></thead><tbody>
{''.join(rows)}
</tbody></table>
<script>
function filtrar() {{
  const v = document.getElementById('f').value;
  document.querySelectorAll('tbody tr').forEach((tr) => {{
    tr.style.display = !v || tr.dataset.condicao === v ? '' : 'none';
  }});
}}
</script>
</body></html>
"""
    HTML_OUT.write_text(doc, encoding="utf-8")


def _gravar_pendente_db(items: list[dict]) -> dict:
    """UPSERT só como pendente_revisao. Nunca aprovado. Nunca org."""
    ok = 0
    erro = None
    try:
        from db import get_conn

        with get_conn() as conn:
            ensure_canonico_schema(conn)
            with conn.cursor() as cur:
                for it in items:
                    if it.get("status_geracao") != "ok":
                        continue
                    cur.execute(
                        """
                        INSERT INTO public.school_aee_metodologias_canonico (
                            condicao_categoria, metodologia_codigo, metodologia_nome,
                            passos_adaptados, status, origem, gerado_em, updated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, 'ia_lote_2026-09-06', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        ON CONFLICT (condicao_categoria, metodologia_codigo)
                        DO UPDATE SET
                            metodologia_nome = EXCLUDED.metodologia_nome,
                            passos_adaptados = EXCLUDED.passos_adaptados,
                            status = CASE
                                WHEN public.school_aee_metodologias_canonico.status = 'aprovado'
                                THEN public.school_aee_metodologias_canonico.status
                                ELSE EXCLUDED.status
                            END,
                            origem = EXCLUDED.origem,
                            gerado_em = EXCLUDED.gerado_em,
                            updated_at = CURRENT_TIMESTAMP,
                            aprovado_em = CASE
                                WHEN public.school_aee_metodologias_canonico.status = 'aprovado'
                                THEN public.school_aee_metodologias_canonico.aprovado_em
                                ELSE NULL
                            END
                        """,
                        (
                            it["condicao_categoria"],
                            it["metodologia_codigo"],
                            it["metodologia_nome"],
                            it["adaptado"],
                            STATUS_PENDENTE,
                        ),
                    )
                    ok += 1
        return {"gravados_pendente": ok, "erro": None}
    except Exception as exc:
        return {"gravados_pendente": ok, "erro": str(exc)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="Máximo de pares (0 = todos)")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--allow-stub", action="store_true")
    ap.add_argument("--skip-db", action="store_true", help="Não UPSERT pendente no Postgres")
    ap.add_argument("--condicao", default="", help="Gerar só esta condição")
    args = ap.parse_args()

    stub = os.environ.get("PEI_LLM_STUB", "").strip().lower() in ("1", "true", "yes")
    if stub and not args.allow_stub:
        print(
            "PEI_LLM_STUB está ligado. O lote canônico precisa de Bedrock real.\n"
            "Rode com PEI_LLM_STUB=0 ou passe --allow-stub só para fumaça local.",
            file=sys.stderr,
        )
        return 2

    catalogo = _load_catalogo()
    condicoes = list(CONDICOES_ORDEM)
    if args.condicao.strip():
        alvo = args.condicao.strip()
        if alvo not in AEE_CANONICO:
            print(f"Condição desconhecida: {alvo}. Válidas: {condicoes}", file=sys.stderr)
            return 2
        condicoes = [alvo]

    pares = []
    for cond in condicoes:
        aee = AEE_CANONICO[cond]
        for met in catalogo:
            pares.append((cond, aee, met))
    if args.limit and args.limit > 0:
        pares = pares[: args.limit]

    ck = _load_checkpoint() if args.resume else {"items": {}}
    items_map: dict[str, dict] = dict(ck.get("items") or {})

    print(
        f"[lote] {len(catalogo)} metodologias × {len(condicoes)} condições "
        f"= {len(catalogo) * len(condicoes)} no universo; gerando {len(pares)} neste run.",
        flush=True,
    )

    for i, (cond, aee, met) in enumerate(pares, start=1):
        codigo = str(met.get("codigo") or "").strip()
        nome = str(met.get("nome") or "").strip()
        key = _chave(cond, codigo)
        if args.resume and key in items_map and items_map[key].get("status_geracao") == "ok":
            print(f"[lote] {i}/{len(pares)} skip {cond} × {nome}", flush=True)
            continue
        original = passos_to_text(met.get("passos_execucao"))
        campos = aee.get("campos_experiencia_metodologica_canonica") or ""
        desc = aee.get("descricao_base_canonica") or ""
        rec = {
            "condicao_categoria": cond,
            "metodologia_codigo": codigo,
            "metodologia_nome": nome,
            "categoria": met.get("categoria") or "",
            "original": original,
            "aee_campos": campos,
            "status_geracao": "ok",
            "adaptado": "",
            "erro": "",
            "gerado_em": _utc_now(),
        }
        try:
            texto = None
            last_exc: Exception | None = None
            for attempt in range(1, 4):
                try:
                    texto = gerar_card_adaptado(
                        metodologia_nome=nome,
                        condicao_categoria=cond,
                        texto_passos_catalogo=original,
                        campos_experiencia_aee=campos,
                        descricao_base_aee=desc,
                    )
                    break
                except Exception as exc:
                    last_exc = exc
                    print(
                        f"[lote] {i}/{len(pares)} tentativa {attempt} {cond} × {nome}: {exc}",
                        file=sys.stderr,
                    )
                    time.sleep(2 * attempt)
            if texto is None:
                raise last_exc or RuntimeError("falha desconhecida")
            if not (texto or "").strip():
                raise RuntimeError("IA devolveu texto vazio")
            rec["adaptado"] = texto.strip()
            print(f"[lote] {i}/{len(pares)} ok {cond} × {nome} ({len(texto)} chars)", flush=True)
        except Exception as exc:
            rec["status_geracao"] = "erro"
            rec["erro"] = str(exc)
            print(f"[lote] {i}/{len(pares)} ERRO {cond} × {nome}: {exc}", file=sys.stderr)
        items_map[key] = rec
        ck["items"] = items_map
        ck["atualizado_em"] = _utc_now()
        _save_checkpoint(ck)

    items = list(items_map.values())
    # Se --limit sem resume, só os deste run (não misturar checkpoint antigo)
    if not args.resume:
        wanted = {_chave(c, str(m.get("codigo") or "")) for c, _, m in pares}
        items = [items_map[k] for k in wanted if k in items_map]

    auditoria = _auditar_org()
    gerado_em = _utc_now()
    _escrever_relatorios(items, auditoria, gerado_em)

    db_info = {"gravados_pendente": 0, "erro": "skip-db"}
    if not args.skip_db:
        db_info = _gravar_pendente_db(items)

    print(json.dumps({
        "relatorio_csv": str(CSV_OUT),
        "relatorio_html": str(HTML_OUT),
        "lote_json": str(JSON_OUT),
        "auditoria_org": auditoria,
        "db_pendente": db_info,
        "contagens": _contagens(items),
    }, ensure_ascii=False, indent=2))
    erros = sum(1 for it in items if it.get("status_geracao") != "ok")
    return 1 if erros else 0


if __name__ == "__main__":
    raise SystemExit(main())
