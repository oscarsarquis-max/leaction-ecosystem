"""Texto do vínculo no Radar — sem tabela nova."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dashboard_api import _ocorrencia_vinculo_texto  # noqa: E402


def test_sem_ocorrencia_vazio():
    assert _ocorrencia_vinculo_texto({}) == ""
    assert _ocorrencia_vinculo_texto({"tipo": "concluida", "status": "normal"}) == ""


def test_unida_com_data():
    assert (
        _ocorrencia_vinculo_texto(
            {"resolucao": "concluida_via_juncao", "juncao_destino_data": "2026-09-03"}
        )
        == "Unida com a aula de 03/09/2026"
    )


def test_continuacao_de():
    assert (
        _ocorrencia_vinculo_texto({"continuacao_origem_data": "2026-09-01T08:00:00"})
        == "Continuação de 01/09/2026"
    )


if __name__ == "__main__":
    test_sem_ocorrencia_vazio()
    test_unida_com_data()
    test_continuacao_de()
    print("ok")
