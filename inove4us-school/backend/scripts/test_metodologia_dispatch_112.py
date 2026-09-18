"""Prompt 112 — PUT vazio desativa override B2C (não republica canônico)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metodologias_api import build_b2c_override_kwargs  # noqa: E402

INST = "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50"


def test_custom_envia_diretriz_ativa():
    merged = {
        "is_customizado": True,
        "versao_escola": "texto da escola Minute Paper",
        "nome": "Minute Paper",
        "codigo": "agil_minute_paper",
        "disponivel_dia_a_dia": True,
        "disponivel_desafio": True,
        "is_active": True,
        "updated_at": "2026-09-04T15:55:13+00:00",
        "config_id": None,
    }
    kw = build_b2c_override_kwargs(merged, INST)
    assert kw["diretriz_customizada"] == "texto da escola Minute Paper"
    assert kw["is_active"] is True
    assert kw["metodologia_codigo"] == "agil_minute_paper"
    assert kw["versao"] is not None


def test_voltar_ao_padrao_desativa_sem_canonico():
    canon = "roteiro canônico completo que não deve ir ao B2C"
    merged = {
        "is_customizado": False,
        "versao_escola": canon,  # API preenche fallback visual; não é custom
        "nome": "Pecha Kucha",
        "codigo": "agil_pecha_kucha",
        "disponivel_dia_a_dia": True,
        "disponivel_desafio": True,
        "is_active": True,
        "updated_at": None,
        "config_id": None,
    }
    kw = build_b2c_override_kwargs(merged, INST)
    assert kw["diretriz_customizada"] is None
    assert kw["is_active"] is False
    assert kw["versao"] is not None


def main() -> int:
    test_custom_envia_diretriz_ativa()
    print("ok test_custom_envia_diretriz_ativa")
    test_voltar_ao_padrao_desativa_sem_canonico()
    print("ok test_voltar_ao_padrao_desativa_sem_canonico")
    print("112 school dispatch 2 ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
