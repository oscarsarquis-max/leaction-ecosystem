"""Lista estruturada de códigos BNCC (prompt 95)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bncc_codigos import (  # noqa: E402
    extract_bncc_codigos,
    habilidades_bncc_da_aula,
    normalize_habilidades_bncc,
)


def test_normalize_lista_e_json():
    assert normalize_habilidades_bncc(["EF06MA07", "ef06ma08", "EF06MA09"]) == [
        "EF06MA07",
        "EF06MA08",
        "EF06MA09",
    ]
    assert normalize_habilidades_bncc('["EF06MA07","EF06MA08"]') == [
        "EF06MA07",
        "EF06MA08",
    ]
    assert normalize_habilidades_bncc(
        [{"habilidade_codigo": "EF06MA07"}, {"codigo": "EF06MA08"}]
    ) == ["EF06MA07", "EF06MA08"]


def test_json_sobrevive_titulo_255():
    rotulos = [
        f"Unidade temática muito longa sobre números racionais e frações — EF06MA{i:02d}"
        for i in range(1, 10)
    ]
    tema = " · ".join(rotulos)[:255]
    codes = ["EF06MA01", "EF06MA02", "EF06MA03"]
    got = habilidades_bncc_da_aula({"tema_aula": tema, "habilidades_bncc": codes})
    assert got == codes
    from_titulo = extract_bncc_codigos(tema)
    assert len(from_titulo) < 9


def test_fallback_aula_antiga_um_codigo():
    row = {"tema_aula": "EF06MA07 — Frações no cotidiano", "ementa_topico": None}
    assert habilidades_bncc_da_aula(row) == ["EF06MA07"]


def test_montar_tema_rotulo_codigo_e_descritivo():
    from bncc_codigos import montar_tema_rotulo

    got = montar_tema_rotulo(
        "EF06MA30",
        catalog_tema="Problemas com números racionais",
        habilidade_codigo="EF06MA30",
    )
    assert got["habilidade_codigo"] == "EF06MA30"
    assert got["tema_legivel"] == "Problemas com números racionais"
    assert got["tema_rotulo"] == "EF06MA30 — Problemas com números racionais"
    so_codigo = montar_tema_rotulo("EF06MA30", habilidade_codigo="EF06MA30")
    assert so_codigo["tema_rotulo"] == "EF06MA30"


if __name__ == "__main__":
    test_normalize_lista_e_json()
    test_json_sobrevive_titulo_255()
    test_fallback_aula_antiga_um_codigo()
    test_montar_tema_rotulo_codigo_e_descritivo()
    print("ok")
