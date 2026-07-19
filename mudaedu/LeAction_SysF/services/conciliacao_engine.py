"""Motor de conciliação financeira — comissões do Portal do Parceiro (Consultor)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

CONTRATO_STATUSES_COMISSAO = frozenset({"ativo", "trial"})
DEMANDA_STATUSES = frozenset({"aberta", "em_andamento", "resolvida"})


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def plano_elegivel_consultoria_tecnica(
    nome_plano: str | None,
    direito_flag: bool | None = None,
) -> bool:
    """Premium ou flag explícita no plano."""
    if direito_flag:
        return True
    nome = (nome_plano or "").strip().lower()
    return "premium" in nome


def consultor_sob_agencia(consultor: dict) -> bool:
    return consultor.get("id_agencia_pai") is not None


def ids_consultores_escopo(
    consultor: dict,
    membros_agencia: list[dict],
) -> list[int]:
    """
    IDs de consultores cujos contratos entram no escopo financeiro do painel.
    - Membro de agência: escopo vazio (valores zerados na tela dele).
    - Agência: próprio id + filhos.
    - Indivíduo independente: apenas próprio id.
    """
    if consultor_sob_agencia(consultor):
        return []
    if (consultor.get("tipo") or "").strip().lower() == "agencia":
        ids = [int(consultor["id"])]
        ids.extend(int(m["id"]) for m in membros_agencia)
        return ids
    return [int(consultor["id"])]


def ids_consultores_carteira(
    consultor: dict,
    membros_agencia: list[dict],
) -> list[int]:
    """IDs para listagem de clientes/sprints (inclui o próprio consultor)."""
    if (consultor.get("tipo") or "").strip().lower() == "agencia":
        ids = [int(consultor["id"])]
        ids.extend(int(m["id"]) for m in membros_agencia)
        return ids
    return [int(consultor["id"])]


def calc_comissao_contrato(
    contrato: dict,
    *,
    id_consultor_alvo: int,
    consultores_por_id: dict[int, dict],
    zerar_valores: bool = False,
) -> dict[str, Any]:
    """
    Calcula comissão de venda e técnica para um contrato em relação a um consultor-alvo.
    Usa as taxas do consultor designado no contrato (origem / técnico).
    """
    valor = _to_float(contrato.get("valor_negociado"))
    status = (contrato.get("status") or "").strip().lower()
    if status not in CONTRATO_STATUSES_COMISSAO:
        return _linha_comissao_zerada(contrato, id_consultor_alvo)

    id_origem = contrato.get("id_consultor_origem")
    id_tecnico = contrato.get("id_consultor_tecnico")
    elegivel_tecnica = plano_elegivel_consultoria_tecnica(
        contrato.get("nome_plano"),
        contrato.get("direito_consultoria_tecnica"),
    )

    com_venda = 0.0
    com_tecnica = 0.0
    taxa_venda_aplicada = 0.0
    taxa_tecnica_aplicada = 0.0
    papeis: list[str] = []

    if id_origem == id_consultor_alvo:
        cons = consultores_por_id.get(int(id_origem), {})
        taxa_venda_aplicada = _to_float(cons.get("taxa_comissao_venda"))
        com_venda = round(valor * taxa_venda_aplicada / 100.0, 2)
        papeis.append("origem")

    if id_tecnico == id_consultor_alvo and elegivel_tecnica:
        cons = consultores_por_id.get(int(id_tecnico), {})
        taxa_tecnica_aplicada = _to_float(cons.get("taxa_comissao_tecnica"))
        com_tecnica = round(valor * taxa_tecnica_aplicada / 100.0, 2)
        papeis.append("tecnico")

    if zerar_valores:
        com_venda = 0.0
        com_tecnica = 0.0

    return {
        "id_contrato": contrato.get("id"),
        "id_clie": contrato.get("id_clie"),
        "nome_clie": contrato.get("nome_clie"),
        "nome_plano": contrato.get("nome_plano"),
        "valor_negociado": valor,
        "status": status,
        "id_consultor_origem": id_origem,
        "id_consultor_tecnico": id_tecnico,
        "id_consultor_alvo": id_consultor_alvo,
        "papeis": papeis,
        "elegivel_consultoria_tecnica": elegivel_tecnica,
        "taxa_comissao_venda": taxa_venda_aplicada,
        "taxa_comissao_tecnica": taxa_tecnica_aplicada,
        "comissao_venda": com_venda,
        "comissao_tecnica": com_tecnica,
        "comissao_total": round(com_venda + com_tecnica, 2),
    }


def _linha_comissao_zerada(contrato: dict, id_consultor_alvo: int) -> dict[str, Any]:
    return {
        "id_contrato": contrato.get("id"),
        "id_clie": contrato.get("id_clie"),
        "nome_clie": contrato.get("nome_clie"),
        "nome_plano": contrato.get("nome_plano"),
        "valor_negociado": _to_float(contrato.get("valor_negociado")),
        "status": contrato.get("status"),
        "id_consultor_origem": contrato.get("id_consultor_origem"),
        "id_consultor_tecnico": contrato.get("id_consultor_tecnico"),
        "id_consultor_alvo": id_consultor_alvo,
        "papeis": [],
        "elegivel_consultoria_tecnica": plano_elegivel_consultoria_tecnica(
            contrato.get("nome_plano"),
            contrato.get("direito_consultoria_tecnica"),
        ),
        "taxa_comissao_venda": 0.0,
        "taxa_comissao_tecnica": 0.0,
        "comissao_venda": 0.0,
        "comissao_tecnica": 0.0,
        "comissao_total": 0.0,
    }


def conciliar_contratos(
    contratos: list[dict],
    consultor: dict,
    membros_agencia: list[dict],
    consultores_por_id: dict[int, dict],
) -> dict[str, Any]:
    """
    Consolida comissões para o painel do consultor logado.
    REGRA 4: membro de agência vê valores zerados; agência pai acumula roll-up dos filhos.
    """
    escopo_financeiro = ids_consultores_escopo(consultor, membros_agencia)
    zerar_exibicao = consultor_sob_agencia(consultor)
    is_agencia = (consultor.get("tipo") or "").strip().lower() == "agencia"

    linhas: list[dict[str, Any]] = []
    total_venda = 0.0
    total_tecnica = 0.0
    contratos_no_escopo = 0

    if is_agencia and escopo_financeiro:
        for cid in escopo_financeiro:
            if cid == int(consultor["id"]):
                continue
            for contrato in contratos:
                linha = calc_comissao_contrato(
                    contrato,
                    id_consultor_alvo=cid,
                    consultores_por_id=consultores_por_id,
                    zerar_valores=False,
                )
                if linha["comissao_total"] > 0:
                    linha["rollup_de_consultor_id"] = cid
                    linhas.append(linha)
                    total_venda += linha["comissao_venda"]
                    total_tecnica += linha["comissao_tecnica"]
                    contratos_no_escopo += 1

        for contrato in contratos:
            linha_propria = calc_comissao_contrato(
                contrato,
                id_consultor_alvo=int(consultor["id"]),
                consultores_por_id=consultores_por_id,
                zerar_valores=False,
            )
            if linha_propria["comissao_total"] > 0:
                linhas.append(linha_propria)
                total_venda += linha_propria["comissao_venda"]
                total_tecnica += linha_propria["comissao_tecnica"]
                contratos_no_escopo += 1
    elif escopo_financeiro:
        cid = int(consultor["id"])
        for contrato in contratos:
            linha = calc_comissao_contrato(
                contrato,
                id_consultor_alvo=cid,
                consultores_por_id=consultores_por_id,
                zerar_valores=zerar_exibicao,
            )
            if linha["papeis"]:
                linhas.append(linha)
                total_venda += linha["comissao_venda"]
                total_tecnica += linha["comissao_tecnica"]
                contratos_no_escopo += 1

    membros_resumo = [
        {
            "id": m["id"],
            "nome": m.get("nome"),
            "email": m.get("email"),
            "taxa_comissao_venda": _to_float(m.get("taxa_comissao_venda")),
            "taxa_comissao_tecnica": _to_float(m.get("taxa_comissao_tecnica")),
        }
        for m in membros_agencia
    ]

    return {
        "consultor": {
            "id": consultor["id"],
            "tipo": consultor.get("tipo"),
            "id_agencia_pai": consultor.get("id_agencia_pai"),
            "nome_agencia_pai": consultor.get("nome_agencia_pai"),
            "taxa_comissao_venda": _to_float(consultor.get("taxa_comissao_venda")),
            "taxa_comissao_tecnica": _to_float(consultor.get("taxa_comissao_tecnica")),
            "financeiro_visivel": not zerar_exibicao,
            "rollup_agencia": is_agencia,
        },
        "membros_agencia": membros_resumo,
        "totais": {
            "comissao_venda": round(total_venda, 2),
            "comissao_tecnica": round(total_tecnica, 2),
            "comissao_total": round(total_venda + total_tecnica, 2),
            "contratos_comissionados": contratos_no_escopo,
            "contratos_carteira": len(contratos),
        },
        "linhas": linhas,
    }


def montar_dashboard_consultor(
    consultor: dict,
    membros_agencia: list[dict],
    contratos: list[dict],
    consultores_por_id: dict[int, dict],
    demandas_abertas: int = 0,
    sprints_ativas: int = 0,
) -> dict[str, Any]:
    conciliacao = conciliar_contratos(
        contratos, consultor, membros_agencia, consultores_por_id
    )
    carteira_ids = ids_consultores_carteira(consultor, membros_agencia)
    clientes_unicos = len({c["id_clie"] for c in contratos if c.get("id_clie")})

    return {
        "conciliacao": conciliacao,
        "estatisticas": {
            "clientes_carteira": clientes_unicos,
            "contratos_ativos_carteira": len(contratos),
            "demandas_abertas": demandas_abertas,
            "sprints_ativas": sprints_ativas,
            "membros_agencia": len(membros_agencia) if consultor.get("tipo") == "agencia" else 0,
            "ids_consultores_carteira": carteira_ids,
        },
    }
