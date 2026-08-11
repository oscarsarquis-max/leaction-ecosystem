#!/usr/bin/env python3
"""Consolida metricas do piloto do wizard a partir de logs locais.

Nao acessa banco. Nao chama AWS. Nao altera o wizard.

Entrada preferida: JSONL (um evento por linha).
Tambem aceita linhas stderr no formato atual:
  [wizard] wizard_ai_metrics request_id=... key=value ...
  [wizard] wizard_total_metrics request_id=... key=value ...

Uso:
  python scripts/resumir_metricas_wizard.py path/para/logs.jsonl
  python scripts/resumir_metricas_wizard.py path/para/logs.jsonl --json
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


EVENT_AI = "wizard_ai_metrics"
EVENT_TOTAL = "wizard_total_metrics"
EVENT_PREF = "metodologia_preferida_valida"

_NUMERIC_KEYS = frozenset(
    {
        "attempt",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "total_input_tokens",
        "total_output_tokens",
        "bedrock_latency_ms",
        "total_latency_ms",
        "bedrock_calls",
        "system_chars",
        "catalogo_chars",
        "ancoras_chars",
        "ancoras_count",
        "diretrizes_chars",
        "obrigatoria_chars",
        "user_chars",
        "matcher_candidate_count",
        "matcher_positive_count",
        "candidate_catalog_chars",
        "cache_creation_input_tokens",
        "cache_read_input_tokens",
        "max_tokens_config",
        "candidate_count",
    }
)
_BOOL_KEYS = frozenset(
    {
        "retry",
        "fallback",
        "full_catalog_fallback",
        "metodologia_preferida_valida",
    }
)

_KV_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=([^\s]+)")


def percentile_nearest_rank(values: list[float], p: float) -> float | None:
    """Percentil nearest-rank: index = ceil(p/100 * n) - 1, p em (0, 100]."""
    if not values:
        return None
    if p <= 0 or p > 100:
        raise ValueError(f"percentil invalido: {p}")
    n = len(values)
    if n == 1:
        return float(values[0])
    idx = int(math.ceil((p / 100.0) * n)) - 1
    idx = max(0, min(idx, n - 1))
    return float(values[idx])


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return float(sum(values) / len(values))


def _as_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _as_bool(v: Any) -> bool | None:
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in ("true", "1", "yes"):
        return True
    if s in ("false", "0", "no"):
        return False
    return None


def _coerce_event(raw: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in raw.items():
        if k in _NUMERIC_KEYS:
            out[k] = _as_float(v)
        elif k in _BOOL_KEYS:
            out[k] = _as_bool(v)
        else:
            out[k] = v
    if out.get("candidate_count") is None and out.get("matcher_candidate_count") is not None:
        out["candidate_count"] = out["matcher_candidate_count"]
    return out


def parse_kv_line(line: str) -> dict[str, Any] | None:
    text = line.strip()
    if not text or text.startswith("#"):
        return None
    if "wizard_ai_metrics" in text:
        event = EVENT_AI
    elif "wizard_total_metrics" in text:
        event = EVENT_TOTAL
    elif "metodologia_preferida_valida=" in text:
        event = EVENT_PREF
    else:
        return None
    fields = {m.group(1): m.group(2) for m in _KV_RE.finditer(text)}
    fields["event"] = event
    if event == EVENT_PREF and "metodologia_preferida_valida" not in fields:
        m = re.search(r"metodologia_preferida_valida=(true|false)", text, re.I)
        if m:
            fields["metodologia_preferida_valida"] = m.group(1).lower()
    return _coerce_event(fields)


def parse_json_line(line: str) -> dict[str, Any] | None:
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None
    event = obj.get("event") or obj.get("metric") or obj.get("type")
    if event not in (EVENT_AI, EVENT_TOTAL, EVENT_PREF):
        if "bedrock_latency_ms" in obj or "attempt" in obj:
            event = EVENT_AI
        elif "total_latency_ms" in obj or "bedrock_calls" in obj:
            event = EVENT_TOTAL
        elif "metodologia_preferida_valida" in obj:
            event = EVENT_PREF
        else:
            return None
    obj = dict(obj)
    obj["event"] = event
    return _coerce_event(obj)


def parse_line(line: str) -> dict[str, Any] | None:
    s = line.strip()
    if not s or s.startswith("#"):
        return None
    if s.startswith("{"):
        return parse_json_line(s)
    return parse_kv_line(s)


def _stat_block(values: list[float], *, percentiles: list[float]) -> dict[str, Any]:
    vals = sorted(float(v) for v in values)
    out: dict[str, Any] = {"n": len(vals), "avg": _mean(vals)}
    for p in percentiles:
        key = f"p{int(p)}" if float(p) == int(p) else f"p{p}"
        out[key] = percentile_nearest_rank(vals, p)
    return out


def _fmt(v: Any, digits: int = 1) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if abs(f - round(f)) < 1e-9:
        return str(int(round(f)))
    return f"{f:.{digits}f}"


def consolidate(events: list[dict[str, Any]]) -> dict[str, Any]:
    by_req: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"ai": [], "total": None, "pref": None}
    )
    orphan_pref_true = 0
    orphan_pref_false = 0

    for ev in events:
        rid = str(ev.get("request_id") or "").strip()
        et = ev.get("event")
        if et == EVENT_PREF:
            val = ev.get("metodologia_preferida_valida")
            if rid:
                by_req[rid]["pref"] = val
            else:
                if val is True:
                    orphan_pref_true += 1
                elif val is False:
                    orphan_pref_false += 1
            continue
        if not rid:
            continue
        if et == EVENT_AI:
            by_req[rid]["ai"].append(ev)
        elif et == EVENT_TOTAL:
            by_req[rid]["total"] = ev

    request_ids = sorted(by_req.keys())
    incomplete: list[str] = []
    complete: list[str] = []
    for rid in request_ids:
        has_ai = bool(by_req[rid]["ai"])
        has_total = by_req[rid]["total"] is not None
        if has_ai and has_total:
            complete.append(rid)
        else:
            incomplete.append(rid)

    bedrock_calls_list: list[float] = []
    for rid in request_ids:
        tot = by_req[rid]["total"]
        if tot and tot.get("bedrock_calls") is not None:
            bedrock_calls_list.append(float(tot["bedrock_calls"]))
        else:
            bedrock_calls_list.append(float(len(by_req[rid]["ai"])))

    total_requests = len(request_ids)
    total_bedrock = int(sum(bedrock_calls_list)) if request_ids else 0
    calls_per_req = (total_bedrock / total_requests) if total_requests else None

    input_tokens: list[float] = []
    output_tokens: list[float] = []
    total_tokens: list[float] = []
    bedrock_lat: list[float] = []
    stop_reasons: Counter[str] = Counter()
    candidate_counts: list[float] = []
    full_catalog_flags: list[bool] = []

    for rid in request_ids:
        for ev in by_req[rid]["ai"]:
            if ev.get("input_tokens") is not None:
                input_tokens.append(float(ev["input_tokens"]))
            if ev.get("output_tokens") is not None:
                output_tokens.append(float(ev["output_tokens"]))
            if ev.get("total_tokens") is not None:
                total_tokens.append(float(ev["total_tokens"]))
            elif (
                ev.get("input_tokens") is not None
                and ev.get("output_tokens") is not None
            ):
                total_tokens.append(
                    float(ev["input_tokens"]) + float(ev["output_tokens"])
                )
            if ev.get("bedrock_latency_ms") is not None:
                bedrock_lat.append(float(ev["bedrock_latency_ms"]))
            sr = ev.get("stop_reason")
            if sr:
                stop_reasons[str(sr)] += 1
            cc = ev.get("candidate_count")
            if cc is not None:
                candidate_counts.append(float(cc))
            fcf = ev.get("full_catalog_fallback")
            if fcf is not None:
                full_catalog_flags.append(bool(fcf))

    total_lat: list[float] = []
    retry_reqs = 0
    fallback_reqs = 0
    retry_known = 0
    fallback_known = 0
    for rid in request_ids:
        tot = by_req[rid]["total"]
        if not tot:
            ai_retry = any(
                (ev.get("retry") is True)
                or (
                    ev.get("attempt") is not None
                    and float(ev["attempt"]) >= 2
                )
                for ev in by_req[rid]["ai"]
            )
            if by_req[rid]["ai"]:
                retry_known += 1
                if ai_retry:
                    retry_reqs += 1
            continue
        if tot.get("total_latency_ms") is not None:
            total_lat.append(float(tot["total_latency_ms"]))
        if tot.get("retry") is not None:
            retry_known += 1
            if tot["retry"] is True:
                retry_reqs += 1
        if tot.get("fallback") is not None:
            fallback_known += 1
            if tot["fallback"] is True:
                fallback_reqs += 1

    pref_true = 0
    pref_false = 0
    pref_known = 0
    for rid in request_ids:
        pref = by_req[rid]["pref"]
        if pref is None:
            continue
        pref_known += 1
        if pref is True:
            pref_true += 1
        else:
            pref_false += 1

    cand_dist = Counter(int(c) for c in candidate_counts)
    full_catalog_true = sum(1 for x in full_catalog_flags if x)
    full_catalog_n = len(full_catalog_flags)

    def _rate(num: int, den: int) -> float | None:
        if den <= 0:
            return None
        return (100.0 * num) / den

    return {
        "volume": {
            "requests": total_requests,
            "requests_complete": len(complete),
            "requests_incomplete": len(incomplete),
            "bedrock_calls": total_bedrock,
            "calls_per_request": calls_per_req,
        },
        "tokens": {
            "input": _stat_block(input_tokens, percentiles=[50, 95]),
            "output": _stat_block(output_tokens, percentiles=[50, 95]),
            "total": {"n": len(total_tokens), "avg": _mean(total_tokens)},
        },
        "latency_bedrock_ms": _stat_block(
            bedrock_lat, percentiles=[50, 95, 99]
        ),
        "latency_total_ms": _stat_block(total_lat, percentiles=[50, 95, 99]),
        "retry": {
            "n_known": retry_known,
            "with_retry": retry_reqs,
            "pct": _rate(retry_reqs, retry_known),
        },
        "fallback": {
            "n_known": fallback_known,
            "with_fallback": fallback_reqs,
            "pct": _rate(fallback_reqs, fallback_known),
        },
        "matcher": {
            "candidate_count": {
                "n": len(candidate_counts),
                "avg": _mean(candidate_counts),
                "distribution": {str(k): cand_dist[k] for k in sorted(cand_dist)},
            },
            "full_catalog_fallback": {
                "n": full_catalog_n,
                "count_true": full_catalog_true,
                "pct": _rate(full_catalog_true, full_catalog_n),
            },
        },
        "metodologia_desejada": {
            "n_known_with_request_id": pref_known,
            "preferencia_valida": pref_true,
            "preferencia_false": pref_false,
            "pct_valida": _rate(pref_true, pref_known),
            "orphan_lines_without_request_id": {
                "true": orphan_pref_true,
                "false": orphan_pref_false,
                "note": (
                    "Em producao o log metodologia_preferida_valida "
                    "hoje nao inclui request_id; conte apenas se export "
                    "trouxer o campo correlacionavel."
                ),
            },
        },
        "stop_reason": dict(stop_reasons),
        "percentile_method": (
            "nearest-rank: index = ceil(p/100 * n) - 1; "
            "ausentes excluidos (nao contam como zero)"
        ),
        "baseline_pre_lancamento": {
            "source": "inove4us_docs/wizard_estruturar_benchmark.md",
            "note": "Referencia estatica; NAO misturar com estatisticas do arquivo.",
            "cenarios": {
                "curto": {
                    "input_tokens": 1076,
                    "output_tokens": 556,
                    "bedrock_latency_ms": 10423,
                },
                "medio": {
                    "input_tokens": 1454,
                    "output_tokens": 552,
                    "bedrock_latency_ms": 7459,
                },
                "longo": {
                    "input_tokens": 2242,
                    "output_tokens": 580,
                    "bedrock_latency_ms": 10846,
                },
            },
        },
    }


def load_events(path: Path) -> tuple[list[dict[str, Any]], dict[str, int]]:
    lines_read = 0
    lines_valid = 0
    lines_ignored = 0
    events: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            lines_read += 1
            parsed = parse_line(line)
            if parsed is None:
                lines_ignored += 1
                continue
            lines_valid += 1
            events.append(parsed)
    return events, {
        "lines_read": lines_read,
        "lines_valid": lines_valid,
        "lines_ignored": lines_ignored,
    }


def format_human(summary: dict[str, Any]) -> str:
    v = summary["volume"]
    tok = summary["tokens"]
    lb = summary["latency_bedrock_ms"]
    lt = summary["latency_total_ms"]
    r = summary["retry"]
    f = summary["fallback"]
    m = summary["matcher"]
    pref = summary["metodologia_desejada"]
    parse = summary.get("parse") or {}
    base = summary["baseline_pre_lancamento"]["cenarios"]

    lines = [
        "WIZARD PILOT SUMMARY",
        "",
        f"Lines read: {parse.get('lines_read', 'n/a')}",
        f"Lines valid: {parse.get('lines_valid', 'n/a')}",
        f"Lines ignored: {parse.get('lines_ignored', 'n/a')}",
        "",
        f"Requests: {_fmt(v['requests'])}",
        f"Requests complete: {_fmt(v['requests_complete'])}",
        f"Requests incomplete: {_fmt(v['requests_incomplete'])}",
        f"Bedrock calls: {_fmt(v['bedrock_calls'])}",
        f"Calls/request: {_fmt(v['calls_per_request'], 2)}",
        "",
        "INPUT TOKENS",
        f"  n={tok['input']['n']} avg={_fmt(tok['input']['avg'])} "
        f"p50={_fmt(tok['input']['p50'])} p95={_fmt(tok['input']['p95'])}",
        "OUTPUT TOKENS",
        f"  n={tok['output']['n']} avg={_fmt(tok['output']['avg'])} "
        f"p50={_fmt(tok['output']['p50'])} p95={_fmt(tok['output']['p95'])}",
        "TOTAL TOKENS (in+out ou total_tokens nativo)",
        f"  n={tok['total']['n']} avg={_fmt(tok['total']['avg'])}",
        "",
        "LATENCY BEDROCK (ms)",
        f"  n={lb['n']} avg={_fmt(lb['avg'])} p50={_fmt(lb['p50'])} "
        f"p95={_fmt(lb['p95'])} p99={_fmt(lb['p99'])}",
        "LATENCY TOTAL (ms)",
        f"  n={lt['n']} avg={_fmt(lt['avg'])} p50={_fmt(lt['p50'])} "
        f"p95={_fmt(lt['p95'])} p99={_fmt(lt['p99'])}",
        "",
        "RETRY",
        f"  with_retry={_fmt(r['with_retry'])} / n_known={_fmt(r['n_known'])} "
        f"pct={_fmt(r['pct'], 2)}%",
        "FALLBACK",
        f"  with_fallback={_fmt(f['with_fallback'])} / n_known={_fmt(f['n_known'])} "
        f"pct={_fmt(f['pct'], 2)}%",
        "",
        "MATCHER",
        f"  candidate_count avg={_fmt(m['candidate_count']['avg'], 2)} "
        f"n={m['candidate_count']['n']} "
        f"dist={m['candidate_count']['distribution']}",
        f"  full_catalog_fallback true={_fmt(m['full_catalog_fallback']['count_true'])} "
        f"/ n={_fmt(m['full_catalog_fallback']['n'])} "
        f"pct={_fmt(m['full_catalog_fallback']['pct'], 2)}%",
        "",
        "METODOLOGIA DESEJADA",
        f"  preferencia_valida={_fmt(pref['preferencia_valida'])} "
        f"/ n_known_with_request_id={_fmt(pref['n_known_with_request_id'])} "
        f"pct={_fmt(pref['pct_valida'], 2)}%",
        f"  orphan_without_request_id true={pref['orphan_lines_without_request_id']['true']} "
        f"false={pref['orphan_lines_without_request_id']['false']}",
        "",
        f"STOP_REASON: {summary.get('stop_reason') or '{}'}",
        f"Percentile method: {summary['percentile_method']}",
        "",
        "BASELINE PRE-LANCAMENTO (referencia estatica; nao misturar)",
        f"  curto  in={base['curto']['input_tokens']} "
        f"out={base['curto']['output_tokens']} "
        f"bedrock_ms={base['curto']['bedrock_latency_ms']}",
        f"  medio  in={base['medio']['input_tokens']} "
        f"out={base['medio']['output_tokens']} "
        f"bedrock_ms={base['medio']['bedrock_latency_ms']}",
        f"  longo  in={base['longo']['input_tokens']} "
        f"out={base['longo']['output_tokens']} "
        f"bedrock_ms={base['longo']['bedrock_latency_ms']}",
        "",
        "Nota: --since/--until nao implementados (logs de metrica sem timestamp).",
        "Filtre a janela temporal na exportacao (CloudWatch/arquivo) antes deste script.",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Resume metricas do piloto do wizard (offline, sem AWS)."
    )
    parser.add_argument(
        "logfile",
        type=Path,
        help="Arquivo local JSONL ou dump de linhas [wizard] wizard_*_metrics",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emite resumo estruturado em JSON",
    )
    args = parser.parse_args(argv)

    if not args.logfile.is_file():
        print(f"Arquivo nao encontrado: {args.logfile}", file=sys.stderr)
        return 2

    events, parse_stats = load_events(args.logfile)
    summary = consolidate(events)
    summary["parse"] = parse_stats

    if args.json:
        print(json.dumps(summary, ensure_ascii=True, indent=2))
    else:
        print(format_human(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
