"""Testes puros do Radar home — cobertura BNCC, metodologia, PEI, extração de código."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from radar_home import (  # noqa: E402
    agregar_metodologias,
    aula_tem_adaptacao_pei,
    extract_habilidade_codigos,
    montar_cobertura,
    montar_inclusao,
    normalize_curso_ano,
    pei_aluno_id_da_mesa,
    tema_aula_legivel,
    _row_aula,
)


def test_extract_codes_from_86_label():
    mesa = {
        "titulo": "Dia a Dia · EF06MA01 — Números racionais · 6º Ano A",
        "ementa_topico": "EF06MA01 — Números racionais",
    }
    assert extract_habilidade_codigos(mesa) == ["EF06MA01"]


def test_extract_ignores_noise():
    assert extract_habilidade_codigos("aula sem habilidade") == []
    assert extract_habilidade_codigos({"titulo": "EM13MAT101 e EF67EF01"}) == [
        "EM13MAT101",
        "EF67EF01",
    ]


def test_normalize_curso_ano():
    assert normalize_curso_ano("6º Ano", "6º Ano A") == "6º ano"
    assert normalize_curso_ano("6º ano") == "6º ano"
    assert normalize_curso_ano("1ª Série", "1ª Série B") == "1ª série"
    assert normalize_curso_ano(None, "7º Ano C") == "7º ano"


def test_metodologias_agregado_sem_vazio():
    got = agregar_metodologias(["Estação", "Estação", None, "Roda", "  "])
    assert got == [
        {"nome": "Estação", "aulas": 2},
        {"nome": "Roda", "aulas": 1},
    ]


def test_cobertura_disciplina_ano():
    catalogo = [
        {"disciplina_nome": "Matemática", "curso_ano": "6º ano", "habilidade_codigo": "EF06MA01"},
        {"disciplina_nome": "Matemática", "curso_ano": "6º ano", "habilidade_codigo": "EF06MA02"},
        {"disciplina_nome": "Matemática", "curso_ano": "6º ano", "habilidade_codigo": "EF06MA03"},
        {"disciplina_nome": "Língua Portuguesa", "curso_ano": "6º ano", "habilidade_codigo": "EF06LP01"},
    ]
    aulas = [
        {
            "disciplina_nome": "Matemática",
            "serie_ano": "6º Ano",
            "turma_nome": "6º Ano A",
            "habilidade_codigos": ["EF06MA01", "EF06MA02"],
        },
        {
            "disciplina_nome": "Matemática",
            "serie_ano": "6º Ano",
            "turma_nome": "6º Ano B",
            "habilidade_codigos": [],
        },
    ]
    got = montar_cobertura(catalogo, aulas)
    assert got["aulas_no_recorte"] == 2
    assert got["aulas_com_tema_bncc"] == 1
    assert len(got["itens"]) == 1
    item = got["itens"][0]
    assert item["disciplina_nome"] == "Matemática"
    assert item["curso_ano"] == "6º ano"
    assert item["temas_catalogo"] == 3
    assert item["temas_cobertos"] == 2
    assert item["percentual"] == 67


def test_cobertura_uma_aula_tres_temas():
    catalogo = [
        {"disciplina_nome": "Matemática", "curso_ano": "6º ano", "habilidade_codigo": "EF06MA07"},
        {"disciplina_nome": "Matemática", "curso_ano": "6º ano", "habilidade_codigo": "EF06MA08"},
        {"disciplina_nome": "Matemática", "curso_ano": "6º ano", "habilidade_codigo": "EF06MA09"},
        {"disciplina_nome": "Matemática", "curso_ano": "6º ano", "habilidade_codigo": "EF06MA10"},
    ]
    aulas = [
        {
            "disciplina_nome": "Matemática",
            "serie_ano": "6º Ano",
            "turma_nome": "6º Ano A",
            "habilidade_codigos": ["EF06MA07", "EF06MA08", "EF06MA09"],
        }
    ]
    got = montar_cobertura(catalogo, aulas)
    item = got["itens"][0]
    assert item["temas_cobertos"] == 3
    assert item["temas_catalogo"] == 4
    assert item["percentual"] == 75


def test_extract_array_habilidade_codigos():
    mesa = {
        "habilidade_codigo": "EF06MA07",
        "habilidade_codigos": ["EF06MA07", "EF06MA08", "EF06MA09"],
        "titulo": "Dia a Dia · Frações",
    }
    assert extract_habilidade_codigos(mesa) == [
        "EF06MA07",
        "EF06MA08",
        "EF06MA09",
    ]
    row = _row_aula(
        {
            "mesa_payload_json": mesa,
            "conteudo_resumo": "Dia a Dia",
            "disciplina_nome": "Matemática",
            "serie_ano": "6º Ano",
            "turma_nome": "6º Ano A",
            "metodologia_nome": "Sala",
        }
    )
    assert row["habilidade_codigos"] == ["EF06MA07", "EF06MA08", "EF06MA09"]


def test_regressao_92_um_codigo():
    mesa = {
        "titulo": "Dia a Dia · EF06MA07 — Frações no cotidiano · 6º Ano A",
        "habilidade_codigo": "EF06MA07",
    }
    assert extract_habilidade_codigos(mesa) == ["EF06MA07"]
    row = _row_aula(
        {
            "mesa_payload_json": mesa,
            "conteudo_resumo": mesa["titulo"],
            "disciplina_nome": "Matemática",
            "serie_ano": "6º Ano",
            "turma_nome": "6º Ano A",
            "metodologia_nome": "Sala de aula invertida",
        }
    )
    assert row["habilidade_codigos"] == ["EF06MA07"]


def test_cobertura_vazia():
    got = montar_cobertura([], [])
    assert got == {"itens": [], "aulas_no_recorte": 0, "aulas_com_tema_bncc": 0}


def test_inclusao_limites():
    got = montar_inclusao(
        alunos_pei_ativos=3,
        alunos_com_adaptacao=1,
        aulas_com_adaptacao=2,
        aulas_no_recorte=10,
    )
    assert got["alunos_pei_ativos"] == 3
    assert got["alunos_com_adaptacao"] == 1
    assert got["percentual"] == 33
    empty = montar_inclusao(
        alunos_pei_ativos=0,
        alunos_com_adaptacao=0,
        aulas_com_adaptacao=0,
        aulas_no_recorte=0,
    )
    assert empty["percentual"] == 0


def test_pei_flags():
    assert aula_tem_adaptacao_pei({"has_pei_adaptations": True})
    assert aula_tem_adaptacao_pei({"pei_adaptation_text": "card TDAH"})
    assert not aula_tem_adaptacao_pei({})
    assert pei_aluno_id_da_mesa({"pei_aluno_id": "abc"}) == "abc"
    assert pei_aluno_id_da_mesa({}) is None


def test_tema_aula_legivel_catalogo_nao_codigo():
    assert (
        tema_aula_legivel(
            "Dia a Dia · EF06MA10",
            catalog_tema="Frações: significados e representações",
        )
        == "Frações: significados e representações"
    )
    assert (
        tema_aula_legivel(
            "Dia a Dia · EF06MA07 — Frações no cotidiano · 6º Ano A"
        )
        == "Frações no cotidiano"
    )
    assert tema_aula_legivel("EF06MA10") == ""
    assert tema_aula_legivel("Dia a Dia · Frações: significados…") == (
        "Frações: significados…"
    )


def test_payload_nao_tem_chave_professor():
    """Contrato: agregadores não carregam identificação docente."""
    mets = agregar_metodologias(["A"])
    assert "professor" not in str(mets).casefold()
    cob = montar_cobertura([], [])
    assert "professor" not in str(cob).casefold()
    inc = montar_inclusao(
        alunos_pei_ativos=1,
        alunos_com_adaptacao=0,
        aulas_com_adaptacao=0,
        aulas_no_recorte=1,
    )
    assert "professor" not in str(inc).casefold()


if __name__ == "__main__":
    test_extract_codes_from_86_label()
    test_extract_ignores_noise()
    test_normalize_curso_ano()
    test_metodologias_agregado_sem_vazio()
    test_cobertura_disciplina_ano()
    test_cobertura_uma_aula_tres_temas()
    test_extract_array_habilidade_codigos()
    test_regressao_92_um_codigo()
    test_cobertura_vazia()
    test_inclusao_limites()
    test_pei_flags()
    test_tema_aula_legivel_catalogo_nao_codigo()
    test_payload_nao_tem_chave_professor()
    print("ok")
