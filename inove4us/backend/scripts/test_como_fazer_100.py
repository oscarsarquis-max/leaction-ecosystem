"""Prompt 100 — contrato da 2ª chamada (Como fazer). Sem Bedrock."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from prompts.inov_ativas import build_como_fazer_system_prompt  # noqa: E402
from wizard_routes import (  # noqa: E402
    aplicar_como_fazer_reescrito,
    strip_prefixo_adaptando,
    validar_contrato_como_fazer,
    _injetar_gancho_primeiro_card,
)

TITULOS = [
    "Observação da Realidade",
    "Levantamento de Pontos-Chave",
    "Teorização",
    "Hipóteses de Solução",
    "Aplicação à Realidade",
]


def _texto(i: int) -> str:
    return (
        f"Turma {i + 1} mede a área externa da Operação Campus 2.0 com trena e laser, "
        f"compara com a planta baixa desatualizada e registra o desperdício abaixo de 5% "
        f"antes de avançar para o Passo seguinte."
    )


def test_prompt_trava_titulos():
    prompt = build_como_fazer_system_prompt(
        "Abordagem problematizadora",
        [{"titulo": t, "objetivo": "obj"} for t in TITULOS],
    )
    assert "IMUTÁVEIS" in prompt
    assert "EXATAMENTE 5" in prompt
    assert "Observação da Realidade" in prompt
    assert "Adaptando para sua aula" in prompt  # proibido, citado nas regras
    assert "NÃO gere cards" not in prompt


def test_contrato_ok():
    raw = {
        "cards": [
            {"indice": i, "titulo": t, "como_executar_detalhado": _texto(i)}
            for i, t in enumerate(TITULOS)
        ]
    }
    out = validar_contrato_como_fazer(raw, TITULOS)
    assert out is not None
    assert len(out) == 5
    assert "Campus" in out[0]


def test_contrato_sexto_card_falha():
    raw = {
        "cards": [
            {"indice": i, "titulo": t, "como_executar_detalhado": _texto(i)}
            for i, t in enumerate(TITULOS)
        ]
        + [
            {
                "indice": 5,
                "titulo": "Passo extra",
                "como_executar_detalhado": _texto(5),
            }
        ]
    }
    assert validar_contrato_como_fazer(raw, TITULOS) is None


def test_contrato_titulo_trocado_falha():
    raw = {
        "cards": [
            {
                "indice": 0,
                "titulo": "Empatizar",
                "como_executar_detalhado": _texto(0),
            }
        ]
        + [
            {"indice": i, "titulo": t, "como_executar_detalhado": _texto(i)}
            for i, t in enumerate(TITULOS[1:], start=1)
        ]
    }
    assert validar_contrato_como_fazer(raw, TITULOS) is None


def test_contrato_texto_curto_falha():
    raw = {
        "cards": [
            {"indice": 0, "titulo": TITULOS[0], "como_executar_detalhado": "curto"},
        ]
        + [
            {"indice": i, "titulo": t, "como_executar_detalhado": _texto(i)}
            for i, t in enumerate(TITULOS[1:], start=1)
        ]
    }
    assert validar_contrato_como_fazer(raw, TITULOS) is None


def test_prefixo_removido_e_nao_injetado():
    cards = [
        {
            "titulo": TITULOS[0],
            "mecanica_passo_a_passo": "O professor conduz a turma a observar um recorte.",
            "como_executar_detalhado": "O professor conduz a turma a observar um recorte.",
        }
    ]
    out = _injetar_gancho_primeiro_card(cards, "Adaptação de catálogo ao trecho «Campus».")
    assert "Adaptando para sua aula" not in (out[0].get("como_executar_detalhado") or "")
    assert out[0].get("gancho_adaptacao")
    prefixado = (
        "**Adaptando para sua aula:** trecho campus.\n\n"
        "O professor conduz a turma a observar um recorte."
    )
    limpo = strip_prefixo_adaptando(prefixado)
    assert "Adaptando para sua aula" not in limpo
    assert "observar" in limpo


def test_aplicar_preserva_titulos():
    plano = {
        "tarefas_kanban": [
            {"titulo": t, "titulo_do_card": t, "como_executar_detalhado": "genérico"}
            for t in TITULOS
        ],
        "dinamica_passo_a_passo": [{"titulo_do_card": t} for t in TITULOS],
    }
    textos = [_texto(i) for i in range(5)]
    aplicar_como_fazer_reescrito(plano, textos)
    assert plano["como_fazer_reescrito"] is True
    for i, t in enumerate(TITULOS):
        assert plano["tarefas_kanban"][i]["titulo"] == t
        assert "Campus" in plano["tarefas_kanban"][i]["como_executar_detalhado"]


if __name__ == "__main__":
    test_prompt_trava_titulos()
    test_contrato_ok()
    test_contrato_sexto_card_falha()
    test_contrato_titulo_trocado_falha()
    test_contrato_texto_curto_falha()
    test_prefixo_removido_e_nao_injetado()
    test_aplicar_preserva_titulos()
    print("ok")
