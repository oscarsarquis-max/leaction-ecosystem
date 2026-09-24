"""Testes do cache/montagem do roteiro 86 — sem Bedrock."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.roteiro_conteudo_service import (  # noqa: E402
    cache_key,
    gerar_exige_bncc,
    identidade_tema,
    montar_passos_com_conteudo,
    montar_texto,
)
from prompts.roteiro_conteudo import build_user_prompt  # noqa: E402


def test_chave_bncc_igual_entre_professores():
    a = cache_key(fonte="bncc", identidade="EF06MA01", nivel_turma="6º ano")
    b = cache_key(fonte="bncc", identidade="ef06ma01", nivel_turma="6º ano")
    assert a == b
    assert a != cache_key(fonte="bncc", identidade="EF06MA01", nivel_turma="1ª série")


def test_identidade_bncc_usa_codigo():
    assert identidade_tema(fonte="bncc", habilidade_codigo="EF06MA01", tema="longo") == "EF06MA01"
    assert identidade_tema(fonte="enem", habilidade_codigo="ENEM-CN-H17", tema="longo") == "ENEM-CN-H17"
    assert "fracoes" in identidade_tema(
        fonte="ementa", habilidade_codigo="", tema=" Fracoes  "
    ).lower()
    assert cache_key(fonte="enem", identidade="ENEM-CN-H17", nivel_turma="1ª série") != cache_key(
        fonte="bncc", identidade="ENEM-CN-H17", nivel_turma="1ª série"
    )


def test_gerar_exige_bncc():
    assert gerar_exige_bncc("EF06MA07") is True
    assert gerar_exige_bncc("") is False
    assert gerar_exige_bncc("  ") is False


def test_montar_texto_tem_as_setes_partes():
    txt = montar_texto(
        {
            "pontos_chave": ["A", "B"],
            "vocabulario": ["n"],
            "equivoco_comum": "confundir",
            "analogia": "como uma receita",
            "pergunta_abertura": "o que é um número?",
            "perguntas_alunos": [{"pergunta": "por quê?", "resposta": "porque a base é 10"}],
            "checklist_material": ["quadro"],
        }
    )
    assert "Pontos-chave" in txt
    assert "Vocabulário" in txt
    assert "Equívoco" in txt
    assert "Analogia" in txt
    assert "Pergunta de abertura" in txt
    assert "Perguntas prováveis" in txt
    assert "Checklist" in txt


def test_passos_so_montagem():
    passos = montar_passos_com_conteudo(
        [{"titulo": "Início", "como_executar": "fale"}],
        {"analogia": "bolo", "pergunta_abertura": "quem já viu?"},
    )
    assert "bolo" in passos[0]["neste_tema"]
    assert passos[0]["como_executar"] == "fale"


def test_prompt_enem_nao_e_tema():
    txt = build_user_prompt(
        tema="CN · C5",
        nivel_turma="1ª série",
        disciplina="Biologia",
        habilidade_codigo="ENEM-CN-H17",
        texto_oficial="Relacionar informações...",
        fonte="enem",
    )
    assert "habilidade/competência avaliada" in txt.lower() or "Habilidade ENEM" in txt
    assert "Habilidade BNCC" not in txt


if __name__ == "__main__":
    test_chave_bncc_igual_entre_professores()
    test_identidade_bncc_usa_codigo()
    test_gerar_exige_bncc()
    test_montar_texto_tem_as_setes_partes()
    test_passos_so_montagem()
    test_prompt_enem_nao_e_tema()
    print("ok")
