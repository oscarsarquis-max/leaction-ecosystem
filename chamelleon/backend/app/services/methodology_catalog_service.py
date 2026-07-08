"""Catálogo de blocos metodológicos (leaf_bloc) por framework."""

from __future__ import annotations

from typing import Any

from app.data.legacy_framework_loader import (
    build_full_methodology_document,
    load_universal_methodology_structure,
)
from app.database.models import Framework, db


def _flatten_blocks_from_dimensions(dimensions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    catalog: list[dict[str, Any]] = []
    for dim in dimensions:
        id_dime = dim.get("id_dime")
        dim_key = dim.get("dimension_key") or dim.get("code_dime")
        for dom in dim.get("domains") or []:
            id_doma = dom.get("id_doma")
            domain_key = dom.get("domain_key")
            domain_name = dom.get("name_doma")
            for bloc in dom.get("blocks") or []:
                catalog.append(
                    {
                        "id_bloc": bloc.get("id_bloc"),
                        "name_bloc": bloc.get("name_bloc"),
                        "desc_bloc": bloc.get("desc_bloc"),
                        "level_bloc": bloc.get("level_bloc"),
                        "id_dime": id_dime or bloc.get("id_dime"),
                        "id_doma": id_doma or bloc.get("id_doma"),
                        "dimension_key": dim_key,
                        "domain_key": domain_key,
                        "domain_name": domain_name,
                        "deliverables": bloc.get("deliverables") or [],
                    }
                )
    return catalog


def get_framework_block_catalog(framework_id: str) -> list[dict[str, Any]]:
    """Lista plana de blocos com entregáveis para um framework publicado."""
    framework = db.session.get(Framework, framework_id)
    if not framework:
        return []

    rules = framework.rules_metadata or {}
    stored_doc = rules.get("methodology_document")
    if isinstance(stored_doc, dict):
        universal = stored_doc.get("canonical_dimensions") or stored_doc.get("universal_dimensions") or []
        sector_dim = stored_doc.get("sector_dimension") or {}
        sector_list = [sector_dim] if sector_dim.get("domains") else []
        return _flatten_blocks_from_dimensions(list(universal) + sector_list)

    op_dim = rules.get("operational_dimension") or {}
    doc = build_full_methodology_document(operational_dimension=op_dim)
    universal = doc.get("canonical_dimensions") or load_universal_methodology_structure()
    sector = doc.get("sector_dimension") or {}
    sector_list = [sector] if sector.get("domains") else []
    return _flatten_blocks_from_dimensions(list(universal) + sector_list)


def get_all_blocks_mapping(framework_id: str) -> list[dict[str, Any]]:
    """Compatível com PanelDX get_all_blocks_mapping — campos id_bloc, name_bloc, id_dime, id_doma."""
    return [
        {
            "id_bloc": b.get("id_bloc"),
            "name_bloc": b.get("name_bloc"),
            "desc_bloc": b.get("desc_bloc"),
            "id_dime": b.get("id_dime"),
            "id_doma": b.get("id_doma"),
            "dimension_key": b.get("dimension_key"),
            "domain_key": b.get("domain_key"),
            "deliverables": b.get("deliverables") or [],
        }
        for b in get_framework_block_catalog(framework_id)
    ]
