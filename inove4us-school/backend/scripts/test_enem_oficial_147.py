"""147 — contagem e proveniência da matriz oficial do ENEM."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from enem_oficial import (  # noqa: E402
    EXPECTED_HABILIDADES,
    EXPECTED_REDAÇÃO,
    FONTE_PDF_SHA256,
    compare_enemwise,
    flatten_oficial,
)


def test_oficial_completo():
    payload = flatten_oficial(ROOT)
    habs = payload["habilidades"]
    assert len(habs) == EXPECTED_HABILIDADES
    assert len(payload["redacao"]) == EXPECTED_REDAÇÃO
    assert len(payload["eixos"]) == 5
    assert len(payload["competencias"]) == 30
    por = {k: 0 for k in ("LC", "MT", "CN", "CH")}
    for r in habs:
        por[r["area_codigo"]] += 1
    assert por == {"LC": 30, "MT": 30, "CN": 30, "CH": 30}
    h1 = next(r for r in habs if r["codigo"] == "ENEM-CH-H01")
    assert h1["texto"].startswith("Interpretar historicamente e/ou geograficamente")
    assert payload["fonte"]["sha256"] == FONTE_PDF_SHA256
    red1 = payload["redacao"][0]
    assert red1["codigo"] == "ENEM-RED-C1"
    assert "modalidade escrita formal" in red1["texto"]


def test_enemwise_nao_substitui_oficial():
    payload = flatten_oficial(ROOT)
    ew = ROOT / "var" / "enem-oficial" / "enemwise-matriz.json"
    if not ew.exists():
        return
    cmp = compare_enemwise(payload, ew)
    assert cmp["faltando_no_enemwise"] == []
    assert cmp["matched"] >= 100
    assert cmp["enemwise_tem_bloom_nao_oficial"] == 120


if __name__ == "__main__":
    test_oficial_completo()
    test_enemwise_nao_substitui_oficial()
    print("ok")
