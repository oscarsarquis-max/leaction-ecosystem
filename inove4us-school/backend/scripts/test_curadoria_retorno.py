"""Validação do retorno ao docente e alvo do aviso."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from curadoria_retorno import (  # noqa: E402
    ROTULO_RESPOSTA,
    aviso_visivel_para_professor,
    ler_retorno_docente,
    montar_texto_aviso,
)


def test_retorno_obrigatorio():
    texto, erro = ler_retorno_docente({})
    assert texto is None
    assert "retorno ao docente" in (erro or "").lower()
    texto, erro = ler_retorno_docente({"retorno_docente": "   "})
    assert texto is None
    texto, erro = ler_retorno_docente({"retorno_docente": "Seguimos com o ciclo."})
    assert texto == "Seguimos com o ciclo."
    assert erro is None


def test_aviso_so_do_professor_alvo():
    assert aviso_visivel_para_professor(aviso_professor_b2c_id=None, id_clie=10) is True
    assert aviso_visivel_para_professor(aviso_professor_b2c_id=7, id_clie=7) is True
    assert aviso_visivel_para_professor(aviso_professor_b2c_id=7, id_clie=8) is False


def test_texto_aviso_tres_resultados():
    for resultado, trecho in (
        ("aprovada", "Aprovada"),
        ("adaptada", "Adaptada"),
        ("nao_incorporada", "Não incorporada agora"),
    ):
        texto = montar_texto_aviso(
            resultado=resultado,
            sugestao_original="Usar mapa mental no fechamento.",
            retorno="Obrigada pela proposta.",
        )
        assert ROTULO_RESPOSTA in texto
        assert trecho in texto
        assert "Usar mapa mental" in texto
        assert "Obrigada pela proposta." in texto


if __name__ == "__main__":
    test_retorno_obrigatorio()
    test_aviso_so_do_professor_alvo()
    test_texto_aviso_tres_resultados()
    print("ok")
