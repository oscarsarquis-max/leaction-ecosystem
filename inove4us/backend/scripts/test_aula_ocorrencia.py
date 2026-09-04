"""União de objetivos do card — campo `objetivo` do Kanban, não PEI."""

from aula_ocorrencia import (
    eh_proxima,
    mesma_cadeia,
    mesmo_assunto,
    normalize_ocorrencia_tipo,
    objetivos_dos_cards,
    resolucao_ao_fechar,
    unir_objetivos_kanban,
)


def test_objetivo_e_campo_do_card():
    ks = {
        "tarefas": [
            {"id": 1, "objetivo": "Treinar síntese em 60s."},
            {"id": 2, "objetivo": "  "},
        ]
    }
    assert objetivos_dos_cards(ks) == ["Treinar síntese em 60s."]


def test_unir_nao_substitui_objetivo_atual():
    dest = {"tarefas": [{"id": "a", "objetivo": "Fechar o ciclo."}]}
    origem = {"tarefas": [{"id": "b", "objetivo": "Mapear a dor."}]}
    merged = unir_objetivos_kanban(dest, origem)
    assert "Fechar o ciclo." in merged["tarefas"][0]["objetivo"]
    assert "Mapear a dor." in merged["tarefas"][0]["objetivo"]


def test_cadeia_mesma_turma_disciplina():
    a = {"turma": "7A", "disciplina_id": 3}
    b = {"turma": "7a", "disciplina_id": 3}
    c = {"turma": "7A", "disciplina_id": 9}
    assert mesma_cadeia(a, b) is True
    assert mesma_cadeia(a, c) is False


def test_mesmo_assunto_respeita_plano():
    base = {"turma": "7A", "disciplina_id": 3, "plano_session": "abc"}
    ok = {**base, "data_evento": "2026-09-02"}
    outro = {**base, "plano_session": "zzz", "data_evento": "2026-09-02"}
    assert mesmo_assunto(base, ok) is True
    assert mesmo_assunto(base, outro) is False


def test_eh_proxima_por_data():
    pend = {
        "id_evento": 1,
        "turma": "7A",
        "disciplina_id": 3,
        "plano_session": "abc",
        "data_evento": "2026-09-01T08:00:00",
    }
    next_ok = {
        "id_evento": 2,
        "turma": "7A",
        "disciplina_id": 3,
        "plano_session": "abc",
        "data_evento": "2026-09-03T08:00:00",
    }
    meio = {
        "id_evento": 9,
        "turma": "7A",
        "disciplina_id": 3,
        "plano_session": "abc",
        "data_evento": "2026-09-02T08:00:00",
    }
    assert eh_proxima(pend, next_ok, []) is True
    assert eh_proxima(pend, next_ok, [meio]) is False


def test_resolucao_so_interrompida():
    assert resolucao_ao_fechar("concluida", False) is None
    assert resolucao_ao_fechar("interrompida", False) == "aguardando_continuacao"
    assert resolucao_ao_fechar("interrompida", True) == "agendada_continuacao"
    assert normalize_ocorrencia_tipo("xyz") == "concluida"


if __name__ == "__main__":
    test_objetivo_e_campo_do_card()
    test_unir_nao_substitui_objetivo_atual()
    test_cadeia_mesma_turma_disciplina()
    test_mesmo_assunto_respeita_plano()
    test_eh_proxima_por_data()
    test_resolucao_so_interrompida()
    print("ok")
