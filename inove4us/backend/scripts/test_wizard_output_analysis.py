"""Testes do helper de análise de output — sem AWS."""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.wizard_output_analysis import (  # noqa: E402
    aggregate_field_stats,
    analisar_output_estruturar,
    format_output_analysis_report,
    medir_texto,
)

m = medir_texto("Uma frase. Outra frase!")
assert m["chars"] > 0
assert m["words"] >= 4
assert m["sentence_count"] == 2

sample = {
    "trecho_relato_usado": "desperdício de água na escola",
    "causas": [
        {"titulo": "A", "descricao": "Falta mapear onde a água é desperdiçada."},
        {"titulo": "B", "descricao": "Turma passiva em atividades teóricas."},
        {"titulo": "C", "descricao": "Sem evidência clara para a gestão."},
    ],
    "A": {
        "id_metodologia": "criativa_pbl_projetos",
        "gancho_adaptacao": "Use o desperdício de água para abrir o projeto.",
        "hipotese_teste": "Se a turma mapear perdas, você observa evidência na entrega.",
    },
    "B": {
        "id_metodologia": "agil_canvas_mania",
        "gancho_adaptacao": "Organize papéis curtos em torno da água.",
        "hipotese_teste": "Se usarem canvas, a proposta fica testável em quatro aulas.",
    },
    "C": {
        "id_metodologia": "analitica_diagnostico_coletivo",
        "gancho_adaptacao": "Diagnostiquem juntos os pontos de vazamento.",
        "hipotese_teste": "Se coletarem evidências, a priorização fica compartilhada.",
    },
}

a = analisar_output_estruturar(sample)
assert a["json_chars"] > 0
assert a["trecho_relato_usado"]["chars"] == len("desperdício de água na escola")
assert len(a["causas"]) == 3
assert a["causas_total"]["chars"] > 0
assert a["ganchos_total"]["chars"] > 0
assert a["hipoteses_total"]["chars"] > 0
assert a["maior_consumidor_chars"] in (
    "trecho",
    "causas",
    "ganchos",
    "hipoteses",
    "json_estrutural",
)
# Relatório não deve conter o texto das causas
report = format_output_analysis_report(a, output_tokens=200, stop_reason="end_turn")
assert "desperdício" not in report
assert "OUTPUT ANALYSIS" in report
assert "stop_reason: end_turn" in report

stats = aggregate_field_stats([a, a])
assert stats["trecho"]["n"] == 2
assert stats["causa"]["n"] == 6
assert stats["gancho"]["n"] == 6
assert stats["hipotese"]["n"] == 6

# Ausência de campos não quebra
empty = analisar_output_estruturar({})
assert empty["json_chars"] >= 2
assert empty["causas_total"]["chars"] == 0

print("OK test_wizard_output_analysis")
