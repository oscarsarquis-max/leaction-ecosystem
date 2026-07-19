"""Testes unitários do motor de conciliação (sem banco)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "LeAction_SysF"))

from services.conciliacao_engine import (  # noqa: E402
    calc_comissao_contrato,
    conciliar_contratos,
    consultor_sob_agencia,
    plano_elegivel_consultoria_tecnica,
)


def _consultor(cid: int, **kwargs):
    base = {
        "id": cid,
        "tipo": "individual",
        "id_agencia_pai": None,
        "taxa_comissao_venda": 10.0,
        "taxa_comissao_tecnica": 15.0,
    }
    base.update(kwargs)
    return base


def test_premium_elegivel():
    assert plano_elegivel_consultoria_tecnica("Conta Premium", False) is True
    assert plano_elegivel_consultoria_tecnica("Conta Básica", False) is False
    assert plano_elegivel_consultoria_tecnica("Básico", True) is True


def test_regra_venda():
    contrato = {
        "id": 1,
        "id_clie": 10,
        "nome_clie": "Cliente A",
        "nome_plano": "Conta Básica",
        "valor_negociado": 1000,
        "status": "ativo",
        "id_consultor_origem": 5,
        "id_consultor_tecnico": None,
        "direito_consultoria_tecnica": False,
    }
    cons_map = {5: _consultor(5)}
    linha = calc_comissao_contrato(contrato, id_consultor_alvo=5, consultores_por_id=cons_map)
    assert linha["comissao_venda"] == 100.0
    assert linha["comissao_tecnica"] == 0.0


def test_regra_acumulo_premium():
    contrato = {
        "id": 2,
        "id_clie": 11,
        "nome_clie": "Cliente B",
        "nome_plano": "Conta Premium",
        "valor_negociado": 2000,
        "status": "ativo",
        "id_consultor_origem": 7,
        "id_consultor_tecnico": 7,
        "direito_consultoria_tecnica": True,
    }
    cons_map = {7: _consultor(7)}
    linha = calc_comissao_contrato(contrato, id_consultor_alvo=7, consultores_por_id=cons_map)
    assert linha["comissao_venda"] == 200.0
    assert linha["comissao_tecnica"] == 300.0
    assert linha["comissao_total"] == 500.0


def test_regra_agencia_membro_zerado():
    membro = _consultor(3, id_agencia_pai=1)
    assert consultor_sob_agencia(membro) is True
    contratos = [{
        "id": 3,
        "id_clie": 12,
        "nome_plano": "Conta Premium",
        "valor_negociado": 1000,
        "status": "ativo",
        "id_consultor_origem": 3,
        "id_consultor_tecnico": 3,
        "direito_consultoria_tecnica": True,
    }]
    cons_map = {3: membro}
    result = conciliar_contratos(contratos, membro, [], cons_map)
    assert result["totais"]["comissao_total"] == 0.0
    assert result["consultor"]["financeiro_visivel"] is False


def test_regra_agencia_rollup():
    agencia = _consultor(1, tipo="agencia")
    filho = _consultor(3, id_agencia_pai=1)
    contratos = [{
        "id": 4,
        "id_clie": 13,
        "nome_plano": "Conta Básica",
        "valor_negociado": 1000,
        "status": "ativo",
        "id_consultor_origem": 3,
        "id_consultor_tecnico": None,
        "direito_consultoria_tecnica": False,
    }]
    cons_map = {1: agencia, 3: filho}
    result = conciliar_contratos(contratos, agencia, [filho], cons_map)
    assert result["totais"]["comissao_total"] == 100.0
    assert result["consultor"]["rollup_agencia"] is True


if __name__ == "__main__":
    test_premium_elegivel()
    test_regra_venda()
    test_regra_acumulo_premium()
    test_regra_agencia_membro_zerado()
    test_regra_agencia_rollup()
    print("conciliacao_engine: todos os testes passaram.")
