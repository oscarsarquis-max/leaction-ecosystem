"""Catálogo fechado de relatórios. Extensível só por código."""

from dataclasses import dataclass

from app.modules.identity_organization.authorization import (
    PERMISSION_REPORTING_COMPLIANCE_READ,
    PERMISSION_REPORTING_COSTING_READ,
    PERMISSION_REPORTING_DASHBOARD_READ,
    PERMISSION_REPORTING_DATA_QUALITY_READ,
    PERMISSION_REPORTING_PRICING_READ,
    PERMISSION_REPORTING_PRODUCTION_READ,
    PERMISSION_REPORTING_TRACEABILITY_READ,
    PERMISSION_REPORTING_INVENTORY_READ,
)
from app.modules.reporting_analytics.constants import REPORT_VERSION


@dataclass(frozen=True)
class ReportSpec:
    code: str
    name: str
    description: str
    permission: str
    extra_permissions: tuple[str, ...]
    metrics: tuple[str, ...]
    version: str = REPORT_VERSION


REPORTS: dict[str, ReportSpec] = {
    "executive": ReportSpec(
        "executive",
        "Visão executiva",
        "Síntese de produção, custos autorizados, preços e conformidade, sem tratar margem como venda.",
        PERMISSION_REPORTING_DASHBOARD_READ,
        (
            PERMISSION_REPORTING_COSTING_READ,
            PERMISSION_REPORTING_PRICING_READ,
            PERMISSION_REPORTING_COMPLIANCE_READ,
        ),
        (
            "orders_by_status",
            "planned_quantity",
            "actual_quantity",
            "yield_actual",
            "loss_actual",
            "cost_variance",
            "cost_per_sellable_unit",
            "price_coverage",
            "compliance_coverage",
            "data_coverage",
        ),
    ),
    "production": ReportSpec(
        "production",
        "Planejamento e produção",
        "Plano versus ordens, estados distintos e cumprimento de quantidade.",
        PERMISSION_REPORTING_PRODUCTION_READ,
        (),
        (
            "orders_by_status",
            "quantity_adherence",
            "normal_completion_rate",
            "short_close_rate",
            "blocking_occurrences",
        ),
    ),
    "consumption": ReportSpec(
        "consumption",
        "Consumo de componentes",
        "Planejado versus consumido, retorno, desperdício e consumo líquido.",
        PERMISSION_REPORTING_PRODUCTION_READ,
        (),
        ("net_consumption", "consumption_variance", "price_coverage"),
    ),
    "yield_losses": ReportSpec(
        "yield_losses",
        "Rendimento e perdas",
        "Massa pré e pós-forno, unidades vendáveis e perdas distinguíveis.",
        PERMISSION_REPORTING_PRODUCTION_READ,
        (),
        ("yield_actual", "loss_actual", "yield_coverage"),
    ),
    "costing": ReportSpec(
        "costing",
        "Custos de produção",
        "Previsto, padrão e realizado com cobertura. Sem inventar venda.",
        PERMISSION_REPORTING_COSTING_READ,
        (),
        ("cost_variance", "cost_per_sellable_unit"),
    ),
    "pricing": ReportSpec(
        "pricing",
        "Formação de preços",
        "Preço sugerido versus praticado, markup e margens estimadas.",
        PERMISSION_REPORTING_PRICING_READ,
        (),
        ("markup_percent", "gross_margin", "contribution_margin", "price_coverage"),
    ),
    "compliance": ReportSpec(
        "compliance",
        "Conformidade e rotulagem",
        "Dossiês, achados e evidência insuficiente. Não é certificado.",
        PERMISSION_REPORTING_COMPLIANCE_READ,
        (),
        ("compliance_coverage",),
    ),
    "traceability": ReportSpec(
        "traceability",
        "Rastreabilidade e auditoria",
        "Timeline de ordem, batelada, eventos, ocorrências e emissões.",
        PERMISSION_REPORTING_TRACEABILITY_READ,
        (),
        (),
    ),
    "inventory": ReportSpec(
        "inventory",
        "Estoque e compras",
        "Posição física, disponível, validade, movimentações e necessidades. Sem valor contábil.",
        PERMISSION_REPORTING_INVENTORY_READ,
        (),
        (
            "physical_on_hand",
            "available_quantity",
            "reserved_quantity",
            "in_transit_quantity",
            "expiring_lots",
            "blocked_lots",
            "count_variance",
            "replenishment_need",
            "inventory_data_quality",
        ),
    ),
    "data_quality": ReportSpec(
        "data_quality",
        "Qualidade dos dados",
        "Pendências acionáveis por domínio, sem ranking individual.",
        PERMISSION_REPORTING_DATA_QUALITY_READ,
        (),
        (
            "price_coverage",
            "nutrition_coverage",
            "yield_coverage",
            "compliance_coverage",
            "data_coverage",
        ),
    ),
}
