"""Testes do consolidator offline de metricas do piloto (sem AWS, sem DB)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from resumir_metricas_wizard import (  # noqa: E402
    consolidate,
    load_events,
    parse_line,
    percentile_nearest_rank,
)

FIXTURE = SCRIPTS / "fixtures" / "wizard_pilot_metrics_sample.jsonl"


# --- percentis ---
assert percentile_nearest_rank([], 50) is None
assert percentile_nearest_rank([10], 50) == 10.0
# n=5: p50 -> ceil(0.5*5)-1 = 2 -> 3o valor (0-index)
assert percentile_nearest_rank([1, 2, 3, 4, 5], 50) == 3.0
assert percentile_nearest_rank([1, 2, 3, 4, 5], 95) == 5.0
assert percentile_nearest_rank([1, 2, 3, 4, 5], 99) == 5.0


# --- parse ---
assert parse_line("") is None
assert parse_line("# comentario") is None
assert parse_line("lixo total") is None
j = parse_line(
    '{"event":"wizard_ai_metrics","request_id":"x","attempt":1,'
    '"input_tokens":10,"output_tokens":null,"retry":false}'
)
assert j is not None
assert j["input_tokens"] == 10.0
assert j["output_tokens"] is None  # ausente/null nao vira 0
assert j["retry"] is False

kv = parse_line(
    "[wizard] wizard_total_metrics request_id=abc total_latency_ms=12.5 "
    "bedrock_calls=1 retry=false fallback=true"
)
assert kv is not None
assert kv["event"] == "wizard_total_metrics"
assert kv["fallback"] is True
assert kv["total_latency_ms"] == 12.5


# --- fixture ---
events, stats = load_events(FIXTURE)
assert stats["lines_read"] >= 10
assert stats["lines_ignored"] >= 1
assert stats["lines_valid"] >= 8

summary = consolidate(events)
summary["parse"] = stats

vol = summary["volume"]
assert vol["requests"] == 7
assert vol["requests_incomplete"] >= 1
assert vol["bedrock_calls"] >= 1
assert vol["calls_per_request"] is not None

# campo ausente nao inventa zero na media de output
out = summary["tokens"]["output"]
assert out["n"] >= 1
# req003 tem output_tokens null — nao deve inflar n com zero
assert all(
    True
    for ev in events
    if ev.get("event") == "wizard_ai_metrics"
    and ev.get("request_id") == "req003"
    and ev.get("output_tokens") is None
)

# retry / fallback
assert summary["retry"]["with_retry"] >= 1
assert summary["retry"]["pct"] is not None
assert summary["fallback"]["with_fallback"] >= 1
assert summary["fallback"]["pct"] is not None

# multiplas attempts
assert any(
    ev.get("request_id") == "req002" and ev.get("attempt") == 2 for ev in events
)
# tokens de ambas attempts entram nas listas
assert summary["tokens"]["input"]["n"] >= 2

# matcher
assert summary["matcher"]["candidate_count"]["avg"] is not None
assert summary["matcher"]["full_catalog_fallback"]["count_true"] >= 1

# stop_reason
assert "max_tokens" in summary["stop_reason"] or "end_turn" in summary["stop_reason"]

# baseline separada
assert "baseline_pre_lancamento" in summary
assert summary["baseline_pre_lancamento"]["cenarios"]["curto"]["input_tokens"] == 1076


# --- CLI --json ---
proc = subprocess.run(
    [sys.executable, str(SCRIPTS / "resumir_metricas_wizard.py"), str(FIXTURE), "--json"],
    cwd=str(BACKEND_ROOT),
    capture_output=True,
    text=True,
    check=False,
)
assert proc.returncode == 0, proc.stderr
payload = json.loads(proc.stdout)
assert payload["volume"]["requests"] == 7
assert "tokens" in payload
assert "latency_bedrock_ms" in payload

# --- CLI humana ---
proc2 = subprocess.run(
    [sys.executable, str(SCRIPTS / "resumir_metricas_wizard.py"), str(FIXTURE)],
    cwd=str(BACKEND_ROOT),
    capture_output=True,
    text=True,
    check=False,
)
assert proc2.returncode == 0, proc2.stderr
assert "WIZARD PILOT SUMMARY" in proc2.stdout
assert "BASELINE PRE-LANCAMENTO" in proc2.stdout
assert "RETRY" in proc2.stdout

print("OK test_resumir_metricas_wizard")
