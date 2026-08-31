"""Produto canônico (evolução de technical_product) e famílias.

Revision ID: 0021_product_canonical
Revises: 0020_inventory_procurement
Create Date: 2026-08-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from app.modules.identity_organization.authorization import (
    PRODUCT_PERMISSION_DEFINITIONS,
    ROLE_PERMISSIONS,
)

revision: str = "0021_product_canonical"
down_revision: Union[str, Sequence[str], None] = "0020_inventory_procurement"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ORG_EQ = "organization_id IS NOT NULL AND organization_id = panne_current_org_id()"
_CODES = {code for code, _ in PRODUCT_PERMISSION_DEFINITIONS}


def upgrade() -> None:
    op.create_table(
        "product_family",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'active'"), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("char_length(code) > 0", name="ck_product_family_code"),
        sa.CheckConstraint("status IN ('active','inactive')", name="ck_product_family_status"),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["parent_id", "organization_id"],
            ["product_family.id", "product_family.organization_id"],
            ondelete="RESTRICT",
            name="fk_product_family_parent",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "code", name="uq_product_family_org_code"),
        sa.UniqueConstraint("id", "organization_id", name="uq_product_family_id_org"),
    )
    op.create_index("ix_product_family_org_status", "product_family", ["organization_id", "status"])
    op.execute("ALTER TABLE product_family ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE product_family FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY rls_product_family_org ON product_family FOR ALL "
        f"USING ({_ORG_EQ}) WITH CHECK ({_ORG_EQ})"
    )

    op.add_column("technical_product", sa.Column("family_id", sa.Uuid(), nullable=True))
    op.add_column(
        "technical_product",
        sa.Column("purpose", sa.Text(), server_default=sa.text("'final'"), nullable=False),
    )
    op.add_column(
        "technical_product",
        sa.Column("supply_mode", sa.Text(), server_default=sa.text("'produced'"), nullable=False),
    )
    op.add_column("technical_product", sa.Column("stock_unit_id", sa.Uuid(), nullable=True))
    op.add_column("technical_product", sa.Column("sale_unit_id", sa.Uuid(), nullable=True))
    op.add_column("technical_product", sa.Column("net_content", sa.Numeric(18, 6), nullable=True))
    op.add_column("technical_product", sa.Column("net_content_unit_id", sa.Uuid(), nullable=True))
    op.add_column(
        "technical_product",
        sa.Column("default_shelf_life_days", sa.Integer(), nullable=True),
    )
    op.add_column("technical_product", sa.Column("packaging_description", sa.Text(), nullable=True))
    op.add_column("technical_product", sa.Column("created_by_user_id", sa.Uuid(), nullable=True))
    op.add_column("technical_product", sa.Column("updated_by_user_id", sa.Uuid(), nullable=True))

    op.execute("ALTER TABLE technical_product DROP CONSTRAINT IF EXISTS ck_technical_product_status")
    op.execute(
        """
        UPDATE technical_product
        SET status = CASE
            WHEN status = 'retired' THEN 'inactive'
            ELSE 'active'
        END,
        purpose = COALESCE(purpose, 'final'),
        supply_mode = COALESCE(supply_mode, 'produced')
        """
    )
    op.execute("ALTER TABLE technical_product ALTER COLUMN status SET DEFAULT 'active'")
    op.create_check_constraint(
        "ck_technical_product_status",
        "technical_product",
        "status IN ('active','inactive')",
    )

    op.create_foreign_key(
        "fk_technical_product_family",
        "technical_product",
        "product_family",
        ["family_id", "organization_id"],
        ["id", "organization_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_technical_product_stock_unit",
        "technical_product",
        "measurement_unit",
        ["stock_unit_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_technical_product_sale_unit",
        "technical_product",
        "measurement_unit",
        ["sale_unit_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_technical_product_net_content_unit",
        "technical_product",
        "measurement_unit",
        ["net_content_unit_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_technical_product_created_by",
        "technical_product",
        "app_user",
        ["created_by_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_technical_product_updated_by",
        "technical_product",
        "app_user",
        ["updated_by_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.create_check_constraint(
        "ck_technical_product_purpose",
        "technical_product",
        "purpose IN ('final','intermediate')",
    )
    op.create_check_constraint(
        "ck_technical_product_supply_mode",
        "technical_product",
        "supply_mode IN ('produced','purchased','mixed','combo')",
    )
    op.create_check_constraint(
        "ck_technical_product_shelf_life",
        "technical_product",
        "default_shelf_life_days IS NULL OR default_shelf_life_days >= 0",
    )
    op.create_check_constraint(
        "ck_technical_product_net_content",
        "technical_product",
        "net_content IS NULL OR net_content > 0",
    )
    op.create_index(
        "ix_technical_product_org_supply",
        "technical_product",
        ["organization_id", "supply_mode"],
    )
    op.create_index(
        "ix_technical_product_org_purpose",
        "technical_product",
        ["organization_id", "purpose"],
    )

    bind = op.get_bind()
    for code, description in PRODUCT_PERMISSION_DEFINITIONS:
        bind.execute(
            sa.text(
                "INSERT INTO permission (code, description) "
                "SELECT :code, :description WHERE NOT EXISTS "
                "(SELECT 1 FROM permission WHERE code = :code)"
            ),
            {"code": code, "description": description},
        )
    for role, codes in ROLE_PERMISSIONS.items():
        for code in codes:
            if code not in _CODES:
                continue
            bind.execute(
                sa.text(
                    "INSERT INTO role_permission (role, permission_id) "
                    "SELECT :role, id FROM permission WHERE code = :code "
                    "AND NOT EXISTS ("
                    "SELECT 1 FROM role_permission rp "
                    "WHERE rp.role = :role AND rp.permission_id = permission.id)"
                ),
                {"role": role, "code": code},
            )

    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'panne_runtime') THEN
            GRANT SELECT, INSERT, UPDATE, DELETE ON product_family TO panne_runtime;
          END IF;
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'panne_demo_runtime') THEN
            GRANT SELECT, INSERT, UPDATE, DELETE ON product_family TO panne_demo_runtime;
          END IF;
        END
        $$
        """
    )


def downgrade() -> None:
    op.drop_index("ix_technical_product_org_purpose", table_name="technical_product")
    op.drop_index("ix_technical_product_org_supply", table_name="technical_product")
    op.drop_constraint("ck_technical_product_net_content", "technical_product", type_="check")
    op.drop_constraint("ck_technical_product_shelf_life", "technical_product", type_="check")
    op.drop_constraint("ck_technical_product_supply_mode", "technical_product", type_="check")
    op.drop_constraint("ck_technical_product_purpose", "technical_product", type_="check")
    op.drop_constraint("ck_technical_product_status", "technical_product", type_="check")
    op.execute(
        """
        UPDATE technical_product
        SET status = CASE WHEN status = 'inactive' THEN 'retired' ELSE 'development' END
        """
    )
    op.create_check_constraint(
        "ck_technical_product_status",
        "technical_product",
        "status IN ('development','approved','retired')",
    )
    op.execute("ALTER TABLE technical_product ALTER COLUMN status SET DEFAULT 'development'")
    for name in (
        "fk_technical_product_updated_by",
        "fk_technical_product_created_by",
        "fk_technical_product_net_content_unit",
        "fk_technical_product_sale_unit",
        "fk_technical_product_stock_unit",
        "fk_technical_product_family",
    ):
        op.drop_constraint(name, "technical_product", type_="foreignkey")
    for col in (
        "updated_by_user_id",
        "created_by_user_id",
        "packaging_description",
        "default_shelf_life_days",
        "net_content_unit_id",
        "net_content",
        "sale_unit_id",
        "stock_unit_id",
        "supply_mode",
        "purpose",
        "family_id",
    ):
        op.drop_column("technical_product", col)
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "DELETE FROM role_permission WHERE permission_id IN "
            "(SELECT id FROM permission WHERE code LIKE 'product.%')"
        )
    )
    bind.execute(sa.text("DELETE FROM permission WHERE code LIKE 'product.%'"))
    op.execute("DROP POLICY IF EXISTS rls_product_family_org ON product_family")
    op.execute("ALTER TABLE product_family NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE product_family DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_product_family_org_status", table_name="product_family")
    op.drop_table("product_family")
