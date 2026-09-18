"""122 — chave de curadoria por aula, não por desafio."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from curadoria_aula_chave import aula_key_do_sync  # noqa: E402


def test_prioriza_origem_aula_explicita():
    assert (
        aula_key_do_sync(
            {"origem_aula_b2c_id": "47", "id_evento": "99"},
            {"id": "12"},
        )
        == "47"
    )


def test_usa_id_evento_do_payload():
    assert aula_key_do_sync({"id_evento": 50}, {"id": "12"}) == "50"


def test_cai_no_mesa_id_legado_121():
    """Payload de produção 121: só mesa.id = id_evento."""
    assert aula_key_do_sync({}, {"id": "50", "titulo": "aula 2"}) == "50"


def test_sem_identidade_nao_inventa():
    assert aula_key_do_sync({}, {}) == ""
    assert aula_key_do_sync(None, None) == ""


def test_duas_aulas_mesma_cadeia_tem_chaves_distintas():
    a = aula_key_do_sync({}, {"id": "49"})
    b = aula_key_do_sync({}, {"id": "50"})
    assert a == "49" and b == "50" and a != b


if __name__ == "__main__":
    test_prioriza_origem_aula_explicita()
    test_usa_id_evento_do_payload()
    test_cai_no_mesa_id_legado_121()
    test_sem_identidade_nao_inventa()
    test_duas_aulas_mesma_cadeia_tem_chaves_distintas()
    print("ok")
