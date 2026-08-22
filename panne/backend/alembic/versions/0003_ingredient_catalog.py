"""Catálogo técnico de ingredientes regularizado.

Revision ID: 0003_ingredient_catalog
Revises: 0002_organization_foundation
Create Date: 2026-08-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_ingredient_catalog"
down_revision: Union[str, Sequence[str], None] = "0002_organization_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _audit_pair() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "measurement_unit",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("plural_name", sa.Text(), nullable=True),
        sa.Column("dimension", sa.Text(), nullable=False),
        sa.Column("si_factor", sa.Numeric(20, 10), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'active'"), nullable=False),
        *_audit_pair(),
        sa.CheckConstraint(
            "dimension IN ('mass','volume','count','energy','arbitrary')",
            name="ck_measurement_unit_dimension",
        ),
        sa.CheckConstraint("si_factor > 0", name="ck_measurement_unit_si_factor"),
        sa.CheckConstraint("status IN ('active','inactive')", name="ck_measurement_unit_status"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "unit_conversion",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("from_unit_id", sa.Uuid(), nullable=False),
        sa.Column("to_unit_id", sa.Uuid(), nullable=False),
        sa.Column("factor", sa.Numeric(20, 10), nullable=False),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'active'"), nullable=False),
        *_audit_pair(),
        sa.CheckConstraint("from_unit_id <> to_unit_id", name="ck_unit_conversion_distinct"),
        sa.CheckConstraint("factor > 0", name="ck_unit_conversion_factor"),
        sa.CheckConstraint("status IN ('active','inactive')", name="ck_unit_conversion_status"),
        sa.ForeignKeyConstraint(["from_unit_id"], ["measurement_unit.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["to_unit_id"], ["measurement_unit.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_unit_conversion_pair_ctx",
        "unit_conversion",
        ["from_unit_id", "to_unit_id", "context"],
        unique=True,
        postgresql_where=sa.text("context IS NOT NULL"),
    )
    op.create_index(
        "uq_unit_conversion_pair",
        "unit_conversion",
        ["from_unit_id", "to_unit_id"],
        unique=True,
        postgresql_where=sa.text("context IS NULL"),
    )

    op.create_table(
        "nutrient_definition",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("unit_id", sa.Uuid(), nullable=False),
        sa.Column("group_code", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'active'"), nullable=False),
        *_audit_pair(),
        sa.CheckConstraint("status IN ('active','inactive')", name="ck_nutrient_definition_status"),
        sa.ForeignKeyConstraint(["unit_id"], ["measurement_unit.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "allergen",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'active'"), nullable=False),
        *_audit_pair(),
        sa.CheckConstraint("status IN ('active','inactive')", name="ck_allergen_status"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "data_source",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("external_ref", sa.Text(), nullable=True),
        sa.Column("version_label", sa.Text(), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("uri", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'active'"), nullable=False),
        *_audit_pair(),
        sa.CheckConstraint(
            "source_type IN ('official_catalog','regulation','manufacturer_label',"
            "'lab_report','internal_calc','user_declared')",
            name="ck_data_source_type",
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_data_source_validity",
        ),
        sa.CheckConstraint("status IN ('active','inactive')", name="ck_data_source_status"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "ingredient",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("ingredient_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'active'"), nullable=False),
        *_audit_pair(),
        sa.CheckConstraint(
            "ingredient_type IN ('simple','composite','preparation')",
            name="ck_ingredient_type",
        ),
        sa.CheckConstraint("status IN ('active','inactive')", name="ck_ingredient_status"),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "code", name="uq_ingredient_org_code"),
        sa.UniqueConstraint("id", "organization_id", name="uq_ingredient_id_org"),
    )

    op.create_table(
        "ingredient_version",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("ingredient_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'draft'"), nullable=False),
        sa.Column("data_source_id", sa.Uuid(), nullable=True),
        sa.Column(
            "nutrition_basis_type",
            sa.Text(),
            server_default=sa.text("'per_100g'"),
            nullable=False,
        ),
        sa.Column(
            "nutrition_basis_quantity",
            sa.Numeric(14, 6),
            server_default=sa.text("100"),
            nullable=False,
        ),
        sa.Column("nutrition_basis_unit_id", sa.Uuid(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('draft','published','retired')",
            name="ck_ingredient_version_status",
        ),
        sa.CheckConstraint("version_number >= 1", name="ck_ingredient_version_number"),
        sa.CheckConstraint(
            "nutrition_basis_type = 'per_100g'",
            name="ck_ingredient_version_basis_type",
        ),
        sa.CheckConstraint(
            "nutrition_basis_quantity = 100",
            name="ck_ingredient_version_basis_qty",
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from",
            name="ck_ingredient_version_validity",
        ),
        sa.ForeignKeyConstraint(
            ["ingredient_id", "organization_id"],
            ["ingredient.id", "ingredient.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["nutrition_basis_unit_id"], ["measurement_unit.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["data_source_id"], ["data_source.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ingredient_id", "version_number", name="uq_ingredient_version_number"),
        sa.UniqueConstraint("id", "organization_id", name="uq_ingredient_version_id_org"),
    )
    op.create_index(
        "uq_ingredient_version_published",
        "ingredient_version",
        ["ingredient_id"],
        unique=True,
        postgresql_where=sa.text("status = 'published'"),
    )

    op.create_table(
        "ingredient_composition",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("parent_ingredient_version_id", sa.Uuid(), nullable=False),
        sa.Column("component_ingredient_version_id", sa.Uuid(), nullable=False),
        sa.Column("component_type", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 6), nullable=False),
        sa.Column("measurement_unit_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("quantity > 0", name="ck_ingredient_composition_qty"),
        sa.CheckConstraint("sequence >= 0", name="ck_ingredient_composition_sequence"),
        sa.CheckConstraint(
            "component_type IN ('constituent','preparation')",
            name="ck_ingredient_composition_type",
        ),
        sa.CheckConstraint(
            "parent_ingredient_version_id <> component_ingredient_version_id",
            name="ck_ingredient_composition_distinct",
        ),
        sa.ForeignKeyConstraint(
            ["parent_ingredient_version_id", "organization_id"],
            ["ingredient_version.id", "ingredient_version.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["component_ingredient_version_id", "organization_id"],
            ["ingredient_version.id", "ingredient_version.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["measurement_unit_id"], ["measurement_unit.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "parent_ingredient_version_id",
            "component_ingredient_version_id",
            name="uq_ingredient_composition_pair",
        ),
        sa.UniqueConstraint(
            "parent_ingredient_version_id",
            "sequence",
            name="uq_ingredient_composition_sequence",
        ),
    )

    op.create_table(
        "ingredient_nutrient",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("ingredient_version_id", sa.Uuid(), nullable=False),
        sa.Column("nutrient_id", sa.Uuid(), nullable=False),
        sa.Column("value", sa.Numeric(14, 6), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("value >= 0", name="ck_ingredient_nutrient_value"),
        sa.ForeignKeyConstraint(
            ["ingredient_version_id", "organization_id"],
            ["ingredient_version.id", "ingredient_version.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["nutrient_id"], ["nutrient_definition.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ingredient_version_id", "nutrient_id", name="uq_ingredient_nutrient"),
    )

    op.create_table(
        "ingredient_allergen",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("ingredient_version_id", sa.Uuid(), nullable=False),
        sa.Column("allergen_id", sa.Uuid(), nullable=False),
        sa.Column("presence", sa.Text(), nullable=False),
        sa.Column("data_source_id", sa.Uuid(), nullable=True),
        sa.Column("evidence_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "presence IN ('contains','may_contain','not_declared')",
            name="ck_ingredient_allergen_presence",
        ),
        sa.ForeignKeyConstraint(
            ["ingredient_version_id", "organization_id"],
            ["ingredient_version.id", "ingredient_version.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["allergen_id"], ["allergen.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["data_source_id"], ["data_source.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ingredient_version_id", "allergen_id", name="uq_ingredient_allergen"),
    )

    op.create_table(
        "supplier",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'active'"), nullable=False),
        *_audit_pair(),
        sa.CheckConstraint("status IN ('active','inactive')", name="ck_supplier_status"),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "code", name="uq_supplier_org_code"),
        sa.UniqueConstraint("id", "organization_id", name="uq_supplier_id_org"),
    )

    op.create_table(
        "supplier_item",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=False),
        sa.Column("ingredient_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_sku", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("package_quantity", sa.Numeric(14, 6), nullable=False),
        sa.Column("measurement_unit_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'active'"), nullable=False),
        *_audit_pair(),
        sa.CheckConstraint("package_quantity > 0", name="ck_supplier_item_package"),
        sa.CheckConstraint("status IN ('active','inactive')", name="ck_supplier_item_status"),
        sa.ForeignKeyConstraint(
            ["supplier_id", "organization_id"],
            ["supplier.id", "supplier.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["ingredient_id", "organization_id"],
            ["ingredient.id", "ingredient.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["measurement_unit_id"], ["measurement_unit.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("supplier_id", "supplier_sku", name="uq_supplier_item_sku"),
    )

    op.create_table(
        "supplier_item_price",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("supplier_item_id", sa.Uuid(), nullable=False),
        sa.Column("unit_price", sa.Numeric(14, 4), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("unit_price >= 0", name="ck_supplier_item_price_value"),
        sa.CheckConstraint("char_length(currency) = 3", name="ck_supplier_item_price_currency"),
        sa.ForeignKeyConstraint(["supplier_item_id"], ["supplier_item.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.execute(
        """
        CREATE FUNCTION panne_unit_conversion_same_dimension() RETURNS trigger AS $$
        DECLARE
          d1 text;
          d2 text;
        BEGIN
          SELECT dimension INTO d1 FROM measurement_unit WHERE id = NEW.from_unit_id;
          SELECT dimension INTO d2 FROM measurement_unit WHERE id = NEW.to_unit_id;
          IF d1 IS DISTINCT FROM d2 THEN
            RAISE EXCEPTION 'incompatible_unit_dimension';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER unit_conversion_same_dimension
        BEFORE INSERT OR UPDATE ON unit_conversion
        FOR EACH ROW EXECUTE FUNCTION panne_unit_conversion_same_dimension();
        """
    )
    op.execute(
        """
        CREATE FUNCTION panne_nutrition_unit_is_mass() RETURNS trigger AS $$
        DECLARE
          dim text;
        BEGIN
          SELECT dimension INTO dim FROM measurement_unit
          WHERE id = NEW.nutrition_basis_unit_id;
          IF dim IS DISTINCT FROM 'mass' THEN
            RAISE EXCEPTION 'nutrition_basis_unit_must_be_mass';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER ingredient_version_nutrition_mass
        BEFORE INSERT OR UPDATE ON ingredient_version
        FOR EACH ROW EXECUTE FUNCTION panne_nutrition_unit_is_mass();
        """
    )
    op.execute(
        """
        CREATE FUNCTION panne_forbid_published_version_mutation() RETURNS trigger AS $$
        BEGIN
          IF TG_OP = 'DELETE' AND OLD.status = 'published' THEN
            RAISE EXCEPTION 'published_frozen';
          END IF;
          IF TG_OP = 'UPDATE' AND OLD.status = 'published' THEN
            RAISE EXCEPTION 'published_frozen';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER ingredient_version_published_frozen
        BEFORE UPDATE OR DELETE ON ingredient_version
        FOR EACH ROW EXECUTE FUNCTION panne_forbid_published_version_mutation();
        """
    )
    op.execute(
        """
        CREATE FUNCTION panne_forbid_published_parent_mutation() RETURNS trigger AS $$
        DECLARE
          version_id uuid;
          v_status text;
        BEGIN
          IF TG_OP = 'DELETE' THEN
            version_id := OLD.parent_ingredient_version_id;
          ELSE
            version_id := NEW.parent_ingredient_version_id;
          END IF;
          SELECT status INTO v_status FROM ingredient_version WHERE id = version_id;
          IF v_status = 'published' THEN
            RAISE EXCEPTION 'published_frozen';
          END IF;
          IF TG_OP = 'DELETE' THEN
            RETURN OLD;
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE FUNCTION panne_forbid_published_version_child_mutation() RETURNS trigger AS $$
        DECLARE
          version_id uuid;
          v_status text;
        BEGIN
          IF TG_OP = 'DELETE' THEN
            version_id := OLD.ingredient_version_id;
          ELSE
            version_id := NEW.ingredient_version_id;
          END IF;
          SELECT status INTO v_status FROM ingredient_version WHERE id = version_id;
          IF v_status = 'published' THEN
            RAISE EXCEPTION 'published_frozen';
          END IF;
          IF TG_OP = 'DELETE' THEN
            RETURN OLD;
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER ingredient_composition_published_frozen
        BEFORE INSERT OR UPDATE OR DELETE ON ingredient_composition
        FOR EACH ROW EXECUTE FUNCTION panne_forbid_published_parent_mutation();
        """
    )
    op.execute(
        """
        CREATE TRIGGER ingredient_nutrient_published_frozen
        BEFORE INSERT OR UPDATE OR DELETE ON ingredient_nutrient
        FOR EACH ROW EXECUTE FUNCTION panne_forbid_published_version_child_mutation();
        """
    )
    op.execute(
        """
        CREATE TRIGGER ingredient_allergen_published_frozen
        BEFORE INSERT OR UPDATE OR DELETE ON ingredient_allergen
        FOR EACH ROW EXECUTE FUNCTION panne_forbid_published_version_child_mutation();
        """
    )
    op.execute(
        """
        CREATE TRIGGER supplier_item_price_append_only
        BEFORE UPDATE OR DELETE ON supplier_item_price
        FOR EACH ROW EXECUTE FUNCTION panne_forbid_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS supplier_item_price_append_only ON supplier_item_price")
    op.execute("DROP TRIGGER IF EXISTS ingredient_allergen_published_frozen ON ingredient_allergen")
    op.execute("DROP TRIGGER IF EXISTS ingredient_nutrient_published_frozen ON ingredient_nutrient")
    op.execute(
        "DROP TRIGGER IF EXISTS ingredient_composition_published_frozen ON ingredient_composition"
    )
    op.execute("DROP TRIGGER IF EXISTS ingredient_version_published_frozen ON ingredient_version")
    op.execute("DROP TRIGGER IF EXISTS ingredient_version_nutrition_mass ON ingredient_version")
    op.execute("DROP TRIGGER IF EXISTS unit_conversion_same_dimension ON unit_conversion")
    op.execute("DROP FUNCTION IF EXISTS panne_forbid_published_version_child_mutation()")
    op.execute("DROP FUNCTION IF EXISTS panne_forbid_published_parent_mutation()")
    op.execute("DROP FUNCTION IF EXISTS panne_forbid_published_child_mutation()")
    op.execute("DROP FUNCTION IF EXISTS panne_forbid_published_version_mutation()")
    op.execute("DROP FUNCTION IF EXISTS panne_nutrition_unit_is_mass()")
    op.execute("DROP FUNCTION IF EXISTS panne_unit_conversion_same_dimension()")
    op.drop_table("supplier_item_price")
    op.drop_table("supplier_item")
    op.drop_table("supplier")
    op.drop_table("ingredient_allergen")
    op.drop_table("ingredient_nutrient")
    op.drop_table("ingredient_composition")
    op.drop_index("uq_ingredient_version_published", table_name="ingredient_version")
    op.drop_table("ingredient_version")
    op.drop_table("ingredient")
    op.drop_table("data_source")
    op.drop_table("allergen")
    op.drop_table("nutrient_definition")
    op.drop_index("uq_unit_conversion_pair", table_name="unit_conversion")
    op.drop_index("uq_unit_conversion_pair_ctx", table_name="unit_conversion")
    op.drop_table("unit_conversion")
    op.drop_table("measurement_unit")
