"""Diagnóstico de verbosidade do JSON retornado pelo Sonnet — sem alterar produção.

Mede chars/words/sentenças por campo. Nunca inclui o texto dos campos no retorno
de métricas destinado a logs (apenas números + IDs técnicos).
"""

from __future__ import annotations

import json
import re
from typing import Any


def _texto(val: object) -> str:
    return " ".join(str(val or "").split()).strip()


def _count_words(texto: str) -> int:
    t = _texto(texto)
    if not t:
        return 0
    return len(re.findall(r"\w+", t, flags=re.UNICODE))


def _count_sentences(texto: str) -> int:
    t = _texto(texto)
    if not t:
        return 0
    # Aproximação: terminações . ! ? ; também conta 1 se não houver pontuação final
    parts = re.split(r"[.!?]+\s+", t)
    parts = [p for p in parts if p.strip()]
    return max(1, len(parts)) if t else 0


def medir_texto(texto: object) -> dict[str, int]:
    t = _texto(texto)
    return {
        "chars": len(t),
        "words": _count_words(t),
        "sentence_count": _count_sentences(t) if t else 0,
    }


def _jaccard_words(a: object, b: object) -> float:
    wa = set(re.findall(r"\w+", _texto(a).casefold(), flags=re.UNICODE))
    wb = set(re.findall(r"\w+", _texto(b).casefold(), flags=re.UNICODE))
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def analisar_output_estruturar(parsed: dict | None) -> dict[str, Any]:
    """Decompõe o JSON do Sonnet em métricas numéricas por campo."""
    raw = parsed if isinstance(parsed, dict) else {}
    try:
        json_chars = len(
            json.dumps(raw, ensure_ascii=False, separators=(",", ":"))
        )
    except Exception:
        json_chars = 0

    trecho = medir_texto(raw.get("trecho_relato_usado"))
    causas = raw.get("causas") if isinstance(raw.get("causas"), list) else []
    causas_metricas = []
    for i, c in enumerate(causas[:3]):
        if not isinstance(c, dict):
            causas_metricas.append(
                {"index": i + 1, "titulo": medir_texto(""), "descricao": medir_texto("")}
            )
            continue
        causas_metricas.append(
            {
                "index": i + 1,
                "titulo": medir_texto(c.get("titulo")),
                "descricao": medir_texto(c.get("descricao")),
                "chars_total": medir_texto(
                    f"{c.get('titulo') or ''} {c.get('descricao') or ''}"
                )["chars"],
                "words_total": medir_texto(
                    f"{c.get('titulo') or ''} {c.get('descricao') or ''}"
                )["words"],
            }
        )

    opcoes = {}
    for chave in ("A", "B", "C"):
        bloco = raw.get(chave) if isinstance(raw.get(chave), dict) else {}
        opcoes[chave] = {
            "id_metodologia_chars": len(_texto(bloco.get("id_metodologia"))),
            "gancho_adaptacao": medir_texto(bloco.get("gancho_adaptacao")),
            "hipotese_teste": medir_texto(bloco.get("hipotese_teste")),
        }

    causas_chars = sum(int(c.get("chars_total") or 0) for c in causas_metricas)
    causas_words = sum(int(c.get("words_total") or 0) for c in causas_metricas)
    ganchos_chars = sum(
        int(opcoes[k]["gancho_adaptacao"]["chars"]) for k in ("A", "B", "C")
    )
    ganchos_words = sum(
        int(opcoes[k]["gancho_adaptacao"]["words"]) for k in ("A", "B", "C")
    )
    hipoteses_chars = sum(
        int(opcoes[k]["hipotese_teste"]["chars"]) for k in ("A", "B", "C")
    )
    hipoteses_words = sum(
        int(opcoes[k]["hipotese_teste"]["words"]) for k in ("A", "B", "C")
    )
    ids_chars = sum(int(opcoes[k]["id_metodologia_chars"]) for k in ("A", "B", "C"))
    content_chars = (
        trecho["chars"] + causas_chars + ganchos_chars + hipoteses_chars + ids_chars
    )
    structural_chars = max(0, json_chars - content_chars)

    # Redundância simples (Jaccard de palavras) — só scores, sem texto.
    redun = {
        "trecho_vs_causa1": 0.0,
        "ganchoA_vs_hipoteseA": 0.0,
        "ganchoB_vs_hipoteseB": 0.0,
        "ganchoC_vs_hipoteseC": 0.0,
        "ganchoA_vs_ganchoB": 0.0,
        "ganchoA_vs_ganchoC": 0.0,
        "causa1_vs_ganchoA": 0.0,
    }
    if causas and isinstance(causas[0], dict):
        c1 = f"{causas[0].get('titulo') or ''} {causas[0].get('descricao') or ''}"
        redun["trecho_vs_causa1"] = round(
            _jaccard_words(raw.get("trecho_relato_usado"), c1), 3
        )
        a = raw.get("A") if isinstance(raw.get("A"), dict) else {}
        redun["causa1_vs_ganchoA"] = round(
            _jaccard_words(c1, a.get("gancho_adaptacao")), 3
        )
    for chave, key in (("A", "ganchoA_vs_hipoteseA"), ("B", "ganchoB_vs_hipoteseB"), ("C", "ganchoC_vs_hipoteseC")):
        bloco = raw.get(chave) if isinstance(raw.get(chave), dict) else {}
        redun[key] = round(
            _jaccard_words(bloco.get("gancho_adaptacao"), bloco.get("hipotese_teste")),
            3,
        )
    a = raw.get("A") if isinstance(raw.get("A"), dict) else {}
    b = raw.get("B") if isinstance(raw.get("B"), dict) else {}
    c = raw.get("C") if isinstance(raw.get("C"), dict) else {}
    redun["ganchoA_vs_ganchoB"] = round(
        _jaccard_words(a.get("gancho_adaptacao"), b.get("gancho_adaptacao")), 3
    )
    redun["ganchoA_vs_ganchoC"] = round(
        _jaccard_words(a.get("gancho_adaptacao"), c.get("gancho_adaptacao")), 3
    )

    groups = {
        "trecho": trecho["chars"],
        "causas": causas_chars,
        "ganchos": ganchos_chars,
        "hipoteses": hipoteses_chars,
        "json_estrutural": structural_chars,
    }
    maior = max(groups, key=groups.get) if groups else "json_estrutural"

    return {
        "json_chars": json_chars,
        "trecho_relato_usado": trecho,
        "causas": causas_metricas,
        "causas_total": {"chars": causas_chars, "words": causas_words},
        "opcoes": opcoes,
        "ganchos_total": {"chars": ganchos_chars, "words": ganchos_words},
        "hipoteses_total": {"chars": hipoteses_chars, "words": hipoteses_words},
        "ids_chars": ids_chars,
        "structural_chars": structural_chars,
        "content_chars": content_chars,
        "redundancy_jaccard": redun,
        "maior_consumidor_chars": maior,
        "groups_chars": groups,
    }


def format_output_analysis_report(
    analysis: dict[str, Any],
    *,
    output_tokens: int | None = None,
    stop_reason: str | None = None,
) -> str:
    """Relatório textual só com métricas (sem conteúdo)."""
    lines = ["OUTPUT ANALYSIS"]
    if output_tokens is not None:
        lines.append(f"total_output_tokens: {output_tokens}")
    if stop_reason is not None:
        lines.append(f"stop_reason: {stop_reason}")
    lines.append(f"json_chars: {analysis.get('json_chars')}")
    lines.append(f"maior_consumidor_chars: {analysis.get('maior_consumidor_chars')}")
    tr = analysis.get("trecho_relato_usado") or {}
    lines.append("trecho_relato:")
    lines.append(f"  chars: {tr.get('chars')}")
    lines.append(f"  words: {tr.get('words')}")
    lines.append(f"  sentence_count: {tr.get('sentence_count')}")
    for c in analysis.get("causas") or []:
        d = c.get("descricao") or {}
        lines.append(f"causa_{c.get('index')}:")
        lines.append(f"  chars: {c.get('chars_total')}")
        lines.append(f"  words: {c.get('words_total')}")
        lines.append(f"  descricao_sentence_count: {d.get('sentence_count')}")
    ct = analysis.get("causas_total") or {}
    lines.append("causas_total:")
    lines.append(f"  chars: {ct.get('chars')}")
    lines.append(f"  words: {ct.get('words')}")
    for chave in ("A", "B", "C"):
        op = (analysis.get("opcoes") or {}).get(chave) or {}
        g = op.get("gancho_adaptacao") or {}
        h = op.get("hipotese_teste") or {}
        lines.append(f"{chave}.gancho_adaptacao:")
        lines.append(f"  chars: {g.get('chars')}")
        lines.append(f"  words: {g.get('words')}")
        lines.append(f"  sentence_count: {g.get('sentence_count')}")
        lines.append(f"{chave}.hipotese_teste:")
        lines.append(f"  chars: {h.get('chars')}")
        lines.append(f"  words: {h.get('words')}")
        lines.append(f"  sentence_count: {h.get('sentence_count')}")
    gt = analysis.get("ganchos_total") or {}
    ht = analysis.get("hipoteses_total") or {}
    lines.append("ganchos_total:")
    lines.append(f"  chars: {gt.get('chars')}")
    lines.append(f"  words: {gt.get('words')}")
    lines.append("hipoteses_total:")
    lines.append(f"  chars: {ht.get('chars')}")
    lines.append(f"  words: {ht.get('words')}")
    lines.append(f"structural_chars: {analysis.get('structural_chars')}")
    lines.append(f"ids_chars: {analysis.get('ids_chars')}")
    red = analysis.get("redundancy_jaccard") or {}
    lines.append("redundancy_jaccard:")
    for k, v in red.items():
        lines.append(f"  {k}: {v}")
    return "\n".join(lines)


def aggregate_field_stats(analyses: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """min/max/avg de chars por tipo de campo ao longo de vários cenários."""
    buckets: dict[str, list[int]] = {
        "trecho": [],
        "causa": [],
        "gancho": [],
        "hipotese": [],
    }
    for a in analyses:
        tr = (a.get("trecho_relato_usado") or {}).get("chars")
        if tr is not None:
            buckets["trecho"].append(int(tr))
        for c in a.get("causas") or []:
            buckets["causa"].append(int(c.get("chars_total") or 0))
        for chave in ("A", "B", "C"):
            op = (a.get("opcoes") or {}).get(chave) or {}
            buckets["gancho"].append(int((op.get("gancho_adaptacao") or {}).get("chars") or 0))
            buckets["hipotese"].append(int((op.get("hipotese_teste") or {}).get("chars") or 0))

    out: dict[str, dict[str, float]] = {}
    for name, vals in buckets.items():
        if not vals:
            out[name] = {"min": 0, "max": 0, "avg": 0, "n": 0}
            continue
        out[name] = {
            "min": min(vals),
            "max": max(vals),
            "avg": round(sum(vals) / len(vals), 1),
            "n": len(vals),
        }
    return out
