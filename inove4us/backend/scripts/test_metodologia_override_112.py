"""Prompt 112 — precedência escola→canônico no retrieval Dia a Dia.

Sem DB. Wizard (apply_override_to_caminho) permanece injeção, não substituição.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.methodology_override_service import (  # noqa: E402
    apply_override_to_caminho,
    apply_override_to_dinamica,
    _passos_from_diretriz,
)

CANON_PASSOS = [
    {
        "ordem": 1,
        "titulo": "Aquecer",
        "objetivo": "entrar no tema",
        "como_executar": "Passo canônico 1 detalhado",
        "dica_de_facilitacao": "",
        "foco": "",
        "duracao_minutos": 5,
    },
    {
        "ordem": 2,
        "titulo": "Produzir",
        "objetivo": "",
        "como_executar": "Passo canônico 2 detalhado",
        "dica_de_facilitacao": "",
        "foco": "",
        "duracao_minutos": 10,
    },
]


def test_sem_override_cai_no_canonico():
    item = {"id": "criativa_world_cafe", "nome": "World Café", "passos": list(CANON_PASSOS)}
    out = apply_override_to_dinamica(item, None)
    assert out["passos"][0]["como_executar"] == "Passo canônico 1 detalhado"
    assert "escola_override" not in out


def test_override_vazio_cai_no_canonico():
    item = {"id": "x", "passos": list(CANON_PASSOS)}
    out = apply_override_to_dinamica(item, {"diretriz_customizada": "  ", "is_active": True})
    assert out["passos"] == CANON_PASSOS
    assert not out.get("escola_override")


def test_override_substitui_passos_pela_versao_escola():
    item = {
        "id": "criativa_sala_invertida",
        "nome": "Sala de aula invertida",
        "passos": list(CANON_PASSOS),
        "roteiro_literal": "canônico longo",
    }
    ov = {
        "diretriz_customizada": "111-escola-sala\nVer vídeo em casa.",
        "versao": 99,
        "metodologia_key": "criativa_sala_invertida",
        "metodologia_nome": "Sala de aula invertida",
    }
    out = apply_override_to_dinamica(item, ov)
    blob = " ".join(p["como_executar"] for p in out["passos"])
    assert "111-escola-sala" in blob
    assert "Passo canônico 1 detalhado" not in blob
    assert out["roteiro_literal"] == ov["diretriz_customizada"]
    assert out["escola_override"]["ativa"] is True
    assert out["escola_override"]["fonte"] == "versao_escola"
    # original não mutado
    assert item["passos"][0]["como_executar"] == "Passo canônico 1 detalhado"


def test_wizard_continua_injetando_nao_substituindo():
    caminho = {
        "por_que_usar": "motivo canônico",
        "plano_eduscrum": {
            "missao": "missão",
            "cards": [{"mecanica_passo_a_passo": "mecânica original"}],
        },
    }
    ov = {"diretriz_customizada": "regra da escola XYZ", "versao": 1, "metodologia_key": "x"}
    out = apply_override_to_caminho(caminho, ov)
    assert "DIRETRIZ DA ESCOLA" in out["por_que_usar"]
    assert "motivo canônico" in out["por_que_usar"]
    assert "mecânica original" in out["plano_eduscrum"]["cards"][0]["mecanica_passo_a_passo"]
    assert "regra da escola XYZ" in out["plano_eduscrum"]["cards"][0]["mecanica_passo_a_passo"]


def test_passos_from_diretriz_uma_linha_longa():
    passos = _passos_from_diretriz("x" * 90)
    assert len(passos) == 1
    assert passos[0]["titulo"] == "Versão da escola"
    assert passos[0]["como_executar"] == "x" * 90


def main() -> int:
    tests = [
        test_sem_override_cai_no_canonico,
        test_override_vazio_cai_no_canonico,
        test_override_substitui_passos_pela_versao_escola,
        test_wizard_continua_injetando_nao_substituindo,
        test_passos_from_diretriz_uma_linha_longa,
    ]
    for fn in tests:
        fn()
        print("ok", fn.__name__)
    print("112 override retrieval", len(tests), "ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
