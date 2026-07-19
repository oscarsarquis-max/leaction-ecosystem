"""Fulfillment de pagamentos ActionHub → PanelDX (contrato + liberação de assessment)."""

from __future__ import annotations

from datetime import date, timedelta

HUB_MATU_ACTIVE_STATUS = "PROJETO OK"
HUB_PROJETO_ACTIVE_STATUS = "ATIVO"
# Status avançados não devem ser sobrescritos pelo pagamento/toggle.
_STATUS_IA_PRESERVE_ON_ACTIVATE = frozenset(
    {
        "AVALIACAO OK",
        "PENDENTE",
        "PROCESSANDO",
        "CONCLUIDO",
        "ERRO_IA",
    }
)


class HubFulfillmentError(ValueError):
    """Erro de negócio no fulfillment do webhook Action Hub."""


def _parse_positive_int(value) -> int | None:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError, AttributeError):
        return None
    return parsed if parsed > 0 else None


def _resolve_status_ia_on_activate(current_status: str | None) -> str:
    """Mantém o status do funil se o assessment/gênese já avançaram."""
    normalized = (current_status or "").strip().upper()
    if normalized in _STATUS_IA_PRESERVE_ON_ACTIVATE:
        return normalized
    return HUB_MATU_ACTIVE_STATUS


def _activate_matu_and_projeto(cur, id_matu: int, id_clie: int) -> dict:
    """Ativa projeto (has_active + ctdi_projetos ATIVO) sem regredir status_ia."""
    cur.execute(
        """
        SELECT m.status_ia, COALESCE(p.status, ''), COALESCE(c.has_active_project, false)
        FROM public.ctdi_matu m
        JOIN public.ctdi_clie c ON c.id_clie = m.id_clie
        LEFT JOIN public.ctdi_projetos p ON p.id_clie = c.id_clie
        WHERE m.id_matu = %s AND m.id_clie = %s
        LIMIT 1
        """,
        (id_matu, id_clie),
    )
    row = cur.fetchone()
    if not row:
        raise HubFulfillmentError(f"id_matu {id_matu} não encontrado para id_clie {id_clie}")

    status_ia, projeto_status, has_active = row
    next_status = _resolve_status_ia_on_activate(status_ia)
    already_active = (
        projeto_status == HUB_PROJETO_ACTIVE_STATUS
        and bool(has_active)
        and (status_ia or "").strip().upper() == next_status
    )
    if already_active:
        return {
            "status": "already_active",
            "id_matu": id_matu,
            "id_clie": id_clie,
            "status_ia": status_ia,
        }

    cur.execute(
        "UPDATE public.ctdi_clie SET has_active_project = TRUE WHERE id_clie = %s",
        (id_clie,),
    )
    cur.execute(
        "UPDATE public.ctdi_matu SET status_ia = %s WHERE id_matu = %s",
        (next_status, id_matu),
    )
    cur.execute(
        """
        INSERT INTO public.ctdi_projetos (id_clie, status)
        VALUES (%s, %s)
        ON CONFLICT (id_clie) DO UPDATE SET status = EXCLUDED.status
        """,
        (id_clie, HUB_PROJETO_ACTIVE_STATUS),
    )
    return {
        "status": "activated",
        "id_matu": id_matu,
        "id_clie": id_clie,
        "status_ia": next_status,
        "projeto_status": HUB_PROJETO_ACTIVE_STATUS,
    }


def fulfill_hub_subscription(
    cur,
    *,
    id_clie: int,
    id_plano: int,
    id_matu: int | None,
    order_id,
    gateway_ref: str,
    valor_negociado: float | None = None,
) -> dict:
    """
    Cria/atualiza contrato CRM e libera assessment completo após pagamento de plano.
    """
    cur.execute("SELECT id_clie FROM public.ctdi_clie WHERE id_clie = %s LIMIT 1;", (id_clie,))
    if not cur.fetchone():
        raise HubFulfillmentError(f"id_clie {id_clie} não encontrado")

    cur.execute(
        "SELECT id, valor_mensal FROM public.dx_planos WHERE id = %s AND ativo = TRUE LIMIT 1;",
        (id_plano,),
    )
    plano = cur.fetchone()
    if not plano:
        raise HubFulfillmentError(f"Plano {id_plano} não encontrado ou inativo")

    plano_id_db, valor_plano = plano
    valor = float(valor_negociado if valor_negociado is not None else valor_plano)
    hoje = date.today()
    vencimento = hoje + timedelta(days=365)

    cur.execute(
        """
        SELECT id, id_plano, status FROM public.dx_contratos
        WHERE id_clie = %s AND status IN ('ativo', 'trial', 'inadimplente')
        ORDER BY id DESC LIMIT 1
        """,
        (id_clie,),
    )
    contrato_row = cur.fetchone()
    if contrato_row:
        contrato_id = contrato_row[0]
        cur.execute(
            """
            UPDATE public.dx_contratos
            SET status = 'ativo',
                id_plano = %s,
                valor_negociado = %s,
                data_vencimento = %s,
                atualizado_em = NOW()
            WHERE id = %s
            """,
            (id_plano, valor, vencimento, contrato_id),
        )
    else:
        cur.execute(
            """
            INSERT INTO public.dx_contratos
                (id_clie, id_plano, valor_negociado, status, data_inicio, data_vencimento)
            VALUES (%s, %s, %s, 'ativo', %s, %s)
            RETURNING id
            """,
            (id_clie, id_plano, valor, hoje, vencimento),
        )
        contrato_id = cur.fetchone()[0]

    matu_id = id_matu
    if not matu_id:
        cur.execute(
            """
            SELECT id_matu FROM public.ctdi_matu
            WHERE id_clie = %s
            ORDER BY id_matu DESC LIMIT 1
            """,
            (id_clie,),
        )
        matu_row = cur.fetchone()
        matu_id = int(matu_row[0]) if matu_row else None

    activation = None
    if matu_id:
        activation = _activate_matu_and_projeto(cur, matu_id, id_clie)

    # Funil: marca oportunidade como ganho e espelha consultor de origem no contrato
    try:
        cur.execute(
            """
            SELECT id, id_consultor_origem
            FROM public.dx_oportunidades
            WHERE id_clie = %s OR id_matu = %s
            ORDER BY
                CASE WHEN id_matu = %s THEN 0 ELSE 1 END,
                id DESC
            LIMIT 1;
            """,
            (id_clie, matu_id, matu_id),
        )
        opp = cur.fetchone()
        if opp:
            opp_id = opp[0] if not isinstance(opp, dict) else opp["id"]
            opp_consultor = opp[1] if not isinstance(opp, dict) else opp.get("id_consultor_origem")
            cur.execute(
                """
                UPDATE public.dx_oportunidades
                SET status_funil = 'ganho',
                    id_clie = COALESCE(id_clie, %s),
                    id_matu = COALESCE(id_matu, %s),
                    atualizado_em = NOW()
                WHERE id = %s;
                """,
                (id_clie, matu_id, opp_id),
            )
            if opp_consultor:
                cur.execute(
                    """
                    UPDATE public.dx_contratos
                    SET id_consultor_origem = COALESCE(id_consultor_origem, %s),
                        atualizado_em = NOW()
                    WHERE id = %s;
                    """,
                    (opp_consultor, contrato_id),
                )
    except Exception:
        # Tabela pode não existir ainda em ambientes sem migration 025
        pass

    return {
        "status": "subscription_fulfilled",
        "id_contrato": contrato_id,
        "id_clie": id_clie,
        "id_plano": id_plano,
        "id_matu": matu_id,
        "order_id": order_id,
        "gateway_ref": gateway_ref,
        "activation": activation,
    }
