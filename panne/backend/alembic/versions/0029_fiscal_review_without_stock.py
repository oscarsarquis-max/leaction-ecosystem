"""Gravar a revisão da nota sem lançar estoque.

Upgrade é só acréscimo: libera o status `reviewed` e guarda a revisão humana
em JSONB. Não reescreve status de notas existentes, não apaga documento,
insumo, local, movimento, saldo nem histórico de custo. Não insere seed,
catálogo fictício, nota demo nem unidade.

Em produção use somente upgrade. O downgrade existe para o teste descartável;
não aplicá-lo na base de cliente. Seed é proibido em produção.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0029_fiscal_review_without_stock"
down_revision: str | Sequence[str] | None = "0028_access_credential"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_BEFORE = (
    "draft",
    "captured",
    "awaiting_xml",
    "awaiting_match",
    "awaiting_check",
    "partially_received",
    "received",
    "divergent",
    "cancelled",
    "refused",
    "superseded",
)
_AFTER = _BEFORE[:5] + ("reviewed",) + _BEFORE[5:]


def _status_in(values: Sequence[str]) -> str:
    rendered = ",".join(f"'{value}'" for value in values)
    return f"status IN ({rendered})"


def upgrade() -> None:
    # Não há UPDATE de linhas existentes: notas, itens e movimentos permanecem.
    op.drop_constraint("ck_fiscal_inbound_document_status", "fiscal_inbound_document", type_="check")
    op.create_check_constraint(
        "ck_fiscal_inbound_document_status",
        "fiscal_inbound_document",
        _status_in(_AFTER),
    )
    op.add_column(
        "fiscal_inbound_item",
        sa.Column(
            "human_review",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.execute("UPDATE fiscal_inbound_document SET status = 'awaiting_match' WHERE status = 'reviewed'")
    op.drop_column("fiscal_inbound_item", "human_review")
    op.drop_constraint("ck_fiscal_inbound_document_status", "fiscal_inbound_document", type_="check")
    op.create_check_constraint(
        "ck_fiscal_inbound_document_status",
        "fiscal_inbound_document",
        _status_in(_BEFORE),
    )
