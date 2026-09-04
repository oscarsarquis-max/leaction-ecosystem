"""Recorte por período do PEI + isolamento de aluno."""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pei_dossie import (  # noqa: E402
    aula_do_aluno,
    aula_no_periodo,
    gerar_pdf_bytes,
    montar_dossie,
)


def test_periodo_por_aluno():
    pei_a = {
        "id": "pei-a",
        "aluno_id": "alu-a",
        "nome_completo": "Ana TEA",
        "matricula": "1",
        "condicao_categoria": "TEA",
    }
    pei_b = {
        "id": "pei-b",
        "aluno_id": "alu-b",
        "nome_completo": "Bruno TDAH",
        "matricula": "2",
        "condicao_categoria": "TDAH",
    }
    aulas = [
        {
            "id": "1",
            "semana_referencia": "2026-03-10",
            "turma_nome": "7A",
            "metodologia_nome": "PBL",
            "conteudo_resumo": "Aula Ana",
            "mesa_payload_json": {"pei_aluno_id": "pei-a", "aluno_nome": "Ana TEA"},
        },
        {
            "id": "2",
            "semana_referencia": "2026-08-10",
            "turma_nome": "7A",
            "metodologia_nome": "PBL",
            "conteudo_resumo": "Aula Bruno",
            "mesa_payload_json": {"pei_aluno_id": "pei-b", "aluno_nome": "Bruno TDAH"},
        },
    ]
    da = montar_dossie(
        pei=pei_a,
        periodo={"rotulo": "1º sem", "data_inicio": "2026-02-01", "data_fim": "2026-06-30"},
        matriz={"texto_escola": "Matriz TEA"},
        aulas=aulas,
    )
    db = montar_dossie(
        pei=pei_b,
        periodo={"rotulo": "2º sem", "data_inicio": "2026-07-01", "data_fim": "2026-12-15"},
        matriz={"texto_escola": "Matriz TDAH"},
        aulas=aulas,
    )
    assert len(da["aulas"]) == 1 and da["aulas"][0]["titulo"] == "Aula Ana"
    assert len(db["aulas"]) == 1 and db["aulas"][0]["titulo"] == "Aula Bruno"
    assert da["periodo_inicio"] == "01/02/2026"
    assert db["periodo_inicio"] == "01/07/2026"


def test_aluno_sem_aula_vazio():
    dossie = montar_dossie(
        pei={"id": "x", "aluno_id": "y", "nome_completo": "Carla", "condicao_categoria": "TEA"},
        periodo={"rotulo": "Ano", "data_inicio": "2026-01-01", "data_fim": "2026-12-31"},
        matriz={"texto_escola": "Matriz"},
        aulas=[
            {
                "semana_referencia": "2026-05-01",
                "conteudo_resumo": "Outro",
                "mesa_payload_json": {"pei_aluno_id": "outro", "aluno_nome": "Outro"},
            }
        ],
    )
    assert dossie["vazio"] is True
    pdf = gerar_pdf_bytes(dossie)
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 200


def test_link_por_id_e_nome():
    mesa = {"pei_aluno_id": "abc", "aluno_nome": "Maria Silva"}
    assert aula_do_aluno(mesa, pei_id="abc", aluno_id=None, aluno_nome="X") is True
    assert aula_do_aluno(
        {"aluno_nome": "Maria Silva"}, pei_id="z", aluno_id=None, aluno_nome="Maria Silva"
    )
    assert aula_do_aluno(mesa, pei_id="outro", aluno_id=None, aluno_nome="João") is False
    assert aula_no_periodo("2026-03-01", date(2026, 2, 1), date(2026, 6, 30)) is True
    assert aula_no_periodo("2026-08-01", date(2026, 2, 1), date(2026, 6, 30)) is False


if __name__ == "__main__":
    test_periodo_por_aluno()
    test_aluno_sem_aula_vazio()
    test_link_por_id_e_nome()
    print("ok")
