"""Leitura da demanda confirmada da Loja (somente SELECT, papel gestao_reader).

Regra (GESTAO-001, seção 1.3): status confirmed, in_production ou ready, com holds_capacity,
fora pedidos com exclusão gerencial ativa. Data da fornada: production_local_date; se nulo, a data
local de breads_available_at da fornada legada. Nenhuma coluna pessoal é lida.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

STATUS_DEMANDA = ("confirmed", "in_production", "ready")

SQL_DEMANDA = text(
    """
SELECT
  COALESCE(o.production_local_date,
           (pb.breads_available_at AT TIME ZONE :tz)::date)                       AS fornada_data,
  CASE WHEN oi.product_id IS NOT NULL THEN 'catalogo' ELSE 'criador' END           AS origem,
  COALESCE(p.name, oi.dough_name_snapshot, dt.name)                                AS produto_ou_massa,
  COALESCE(pv.display_name, oi.shape_name_snapshot)                                AS variante_ou_forma,
  rb.code                                                                          AS receita_base,
  SUM(oi.quantity)                                                                 AS quantidade,
  SUM(COALESCE(oi.physical_units, oi.quantity))                                    AS paes_fisicos,
  COUNT(*) FILTER (WHERE oi.physical_units IS NULL AND oi.product_id IS NOT NULL)  AS linhas_unidades_pendentes
FROM orders o
JOIN order_items oi              ON oi.order_id = o.id
LEFT JOIN products p             ON p.id  = oi.product_id
LEFT JOIN product_variants pv    ON pv.id = oi.product_variant_id
LEFT JOIN dough_types dt         ON dt.id = oi.dough_type_id
LEFT JOIN recipe_bases rb        ON rb.id = COALESCE(oi.recipe_base_id, dt.recipe_base_id)
LEFT JOIN production_batches pb  ON pb.id = o.production_batch_id
WHERE o.status IN ('confirmed', 'in_production', 'ready')
  AND o.holds_capacity IS TRUE
  AND NOT EXISTS (
        SELECT 1 FROM managerial_exclusions me
        WHERE me.subject_type = 'order' AND me.subject_id = o.id AND me.reversed_at IS NULL)
  AND COALESCE(o.production_local_date,
               (pb.breads_available_at AT TIME ZONE :tz)::date) BETWEEN :de AND :ate
GROUP BY 1, 2, 3, 4, 5
ORDER BY 1, 2, 3, 4, 5
"""
)

# Mesmas tabelas, o mesmo WHERE e as mesmas colunas da demanda da Hoje.
# product_id, product_variant_id e orders.id já estão no GRANT do gestao_reader.
SQL_DEMANDA_VINCULO = text(
    """
SELECT
  COALESCE(o.production_local_date,
           (pb.breads_available_at AT TIME ZONE :tz)::date)                       AS fornada_data,
  oi.product_id                                                                   AS product_id,
  oi.product_variant_id                                                           AS product_variant_id,
  COALESCE(p.name, oi.dough_name_snapshot, dt.name)                                AS produto_ou_massa,
  COALESCE(pv.display_name, oi.shape_name_snapshot)                                AS variante_ou_forma,
  SUM(COALESCE(oi.physical_units, oi.quantity))                                    AS paes_fisicos,
  array_agg(DISTINCT o.id::text)                                                   AS pedido_ids
FROM orders o
JOIN order_items oi              ON oi.order_id = o.id
LEFT JOIN products p             ON p.id  = oi.product_id
LEFT JOIN product_variants pv    ON pv.id = oi.product_variant_id
LEFT JOIN dough_types dt         ON dt.id = oi.dough_type_id
LEFT JOIN recipe_bases rb        ON rb.id = COALESCE(oi.recipe_base_id, dt.recipe_base_id)
LEFT JOIN production_batches pb  ON pb.id = o.production_batch_id
WHERE o.status IN ('confirmed', 'in_production', 'ready')
  AND o.holds_capacity IS TRUE
  AND NOT EXISTS (
        SELECT 1 FROM managerial_exclusions me
        WHERE me.subject_type = 'order' AND me.subject_id = o.id AND me.reversed_at IS NULL)
  AND COALESCE(o.production_local_date,
               (pb.breads_available_at AT TIME ZONE :tz)::date) BETWEEN :de AND :ate
GROUP BY 1, 2, 3, 4, 5
ORDER BY 1, 4, 5
"""
)

SQL_VERSAO_LOJA = text("SELECT version_num FROM alembic_version LIMIT 1")


@dataclass(frozen=True)
class LinhaDemanda:
    fornada_data: date
    origem: str
    produto_ou_massa: str | None
    variante_ou_forma: str | None
    receita_base: str | None
    quantidade: int
    paes_fisicos: int
    linhas_unidades_pendentes: int


def consultar_demanda(
    loja: Session, *, de: date, ate: date, fuso: str = "America/Sao_Paulo"
) -> list[LinhaDemanda]:
    linhas = loja.execute(SQL_DEMANDA, {"de": de, "ate": ate, "tz": fuso}).mappings().all()
    return [
        LinhaDemanda(
            fornada_data=linha["fornada_data"],
            origem=linha["origem"],
            produto_ou_massa=linha["produto_ou_massa"],
            variante_ou_forma=linha["variante_ou_forma"],
            receita_base=linha["receita_base"],
            quantidade=int(linha["quantidade"] or 0),
            paes_fisicos=int(linha["paes_fisicos"] or 0),
            linhas_unidades_pendentes=int(linha["linhas_unidades_pendentes"] or 0),
        )
        for linha in linhas
    ]


@dataclass(frozen=True)
class LinhaVinculo:
    fornada_data: date
    product_id: str | None
    product_variant_id: str | None
    produto_ou_massa: str | None
    variante_ou_forma: str | None
    paes_fisicos: int
    pedido_ids: list[str]


def consultar_demanda_vinculo(
    loja: Session, *, de: date, ate: date, fuso: str = "America/Sao_Paulo"
) -> list[LinhaVinculo]:
    """A demanda da Hoje, com o id do produto e os pedidos, para virar ordem de produção."""
    linhas = loja.execute(SQL_DEMANDA_VINCULO, {"de": de, "ate": ate, "tz": fuso}).mappings().all()
    saida = []
    for linha in linhas:
        ids = linha["pedido_ids"] or []
        saida.append(
            LinhaVinculo(
                fornada_data=linha["fornada_data"],
                product_id=str(linha["product_id"]) if linha["product_id"] else None,
                product_variant_id=str(linha["product_variant_id"]) if linha["product_variant_id"] else None,
                produto_ou_massa=linha["produto_ou_massa"],
                variante_ou_forma=linha["variante_ou_forma"],
                paes_fisicos=int(linha["paes_fisicos"] or 0),
                pedido_ids=[str(item) for item in ids],
            )
        )
    return saida


def versao_loja(loja: Session) -> str | None:
    return loja.execute(SQL_VERSAO_LOJA).scalar_one_or_none()


def verificar_contrato(loja: Session, *, fuso: str) -> None:
    """Roda a consulta de demanda num intervalo vazio: valida colunas e privilégios sem ler dados."""
    consultar_demanda(loja, de=date(1970, 1, 1), ate=date(1969, 12, 31), fuso=fuso)
    consultar_demanda_vinculo(loja, de=date(1970, 1, 1), ate=date(1969, 12, 31), fuso=fuso)
    versao_loja(loja)
