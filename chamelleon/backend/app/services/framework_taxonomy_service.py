"""Persistência e leitura da taxonomia PanelDX (leaf_dime → leaf_doma → leaf_bloc → leaf_derv)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.core.sector_constants import is_canonical_education_framework
from app.data.legacy_framework_loader import load_full_taxonomy_from_legacy
from app.database.models import (
    Framework,
    FrameworkBlock,
    FrameworkDeliverable,
    FrameworkDimension,
    FrameworkDomain,
    db,
)

logger = logging.getLogger(__name__)


def _clear_framework_taxonomy(framework_id: str) -> None:
    FrameworkDeliverable.query.filter_by(framework_id=framework_id).delete()
    FrameworkBlock.query.filter_by(framework_id=framework_id).delete()
    FrameworkDimension.query.filter_by(framework_id=framework_id).delete()
    FrameworkDomain.query.filter_by(framework_id=framework_id).delete()


def import_taxonomy_from_legacy(framework_id: str) -> dict[str, int]:
    """Importa taxonomia completa do banco PanelDX legado."""
    payload = load_full_taxonomy_from_legacy()
    if not payload:
        raise RuntimeError(
            "Não foi possível importar taxonomia do PanelDX. "
            "Verifique LEGACY_QUEST_DATABASE_URL."
        )
    return _persist_taxonomy_payload(framework_id, payload)


def import_taxonomy_from_methodology_document(
    framework_id: str,
    methodology_document: dict[str, Any] | None,
) -> dict[str, int]:
    """Persiste taxonomia a partir do documento metodológico (frameworks gerados por IA)."""
    if not methodology_document:
        return {"dimensions": 0, "domains": 0, "blocks": 0, "deliverables": 0}

    dimensions_in: list[dict[str, Any]] = list(
        methodology_document.get("canonical_dimensions") or []
    )
    sector_dim = methodology_document.get("sector_dimension")
    if isinstance(sector_dim, dict) and sector_dim.get("domains"):
        dimensions_in.append(sector_dim)

    synthetic_id = -1
    dimensions_normalized: list[dict[str, Any]] = []
    for dim in dimensions_in:
        row = dict(dim)
        if row.get("id_dime") is None:
            row["id_dime"] = synthetic_id
            synthetic_id -= 1
        dimensions_normalized.append(row)

    domains_map: dict[int, dict[str, Any]] = {}
    blocks_out: list[dict[str, Any]] = []
    deliverables_out: list[dict[str, Any]] = []
    synthetic_bloc_id = synthetic_id

    for dim in dimensions_normalized:
        id_dime = dim.get("id_dime")
        for dom in dim.get("domains") or []:
            id_doma = dom.get("id_doma")
            if id_doma is not None:
                domains_map[int(id_doma)] = dom
            elif dom.get("domain_key"):
                synthetic_doma = synthetic_bloc_id
                synthetic_bloc_id -= 1
                dom = {**dom, "id_doma": synthetic_doma}
                domains_map[synthetic_doma] = dom
                id_doma = synthetic_doma

            for bloc in dom.get("blocks") or []:
                bloc_id = bloc.get("id_bloc")
                if bloc_id is None:
                    bloc_id = synthetic_bloc_id
                    synthetic_bloc_id -= 1
                bloc_row = {
                    **bloc,
                    "id_bloc": bloc_id,
                    "id_dime": id_dime or bloc.get("id_dime"),
                    "id_doma": id_doma or bloc.get("id_doma"),
                }
                blocks_out.append(bloc_row)
                for derv in bloc.get("deliverables") or []:
                    deliverables_out.append({**derv, "id_bloc": bloc_id})

    payload = {
        "dimensions": [
            {
                "id_dime": d.get("id_dime"),
                "dimension_key": d.get("dimension_key") or d.get("code_dime"),
                "name_dime": d.get("name_dime") or d.get("name"),
                "desc_dime": d.get("desc_dime") or d.get("description"),
                "long_description": d.get("long_description"),
                "code_dime": d.get("code_dime") or d.get("dimension_key"),
                "perspective_dime": d.get("perspective_dime"),
            }
            for d in dimensions_normalized
        ],
        "domains": [
            {
                "id_doma": d.get("id_doma"),
                "domain_key": d.get("domain_key"),
                "name_doma": d.get("name_doma") or d.get("name"),
                "desc_doma": d.get("desc_doma") or d.get("description"),
                "vetor_estrategico": d.get("vetor_estrategico"),
            }
            for d in domains_map.values()
        ],
        "blocks": blocks_out,
        "deliverables": deliverables_out,
    }
    return _persist_taxonomy_payload(framework_id, payload)


def _persist_taxonomy_payload(framework_id: str, payload: dict[str, Any]) -> dict[str, int]:
    framework = db.session.get(Framework, framework_id)
    if not framework:
        raise ValueError(f"Framework '{framework_id}' não encontrado.")

    _clear_framework_taxonomy(framework_id)

    dim_by_legacy: dict[int, uuid.UUID] = {}
    dom_by_legacy: dict[int, uuid.UUID] = {}
    block_by_legacy: dict[int, uuid.UUID] = {}

    for index, row in enumerate(payload.get("dimensions") or []):
        legacy_id = row.get("id_dime")
        entity = FrameworkDimension(
            framework_id=framework_id,
            legacy_id_dime=int(legacy_id) if legacy_id is not None else None,
            dimension_key=(row.get("dimension_key") or row.get("code_dime") or "").upper() or None,
            name_dime=row.get("name_dime") or "",
            desc_dime=row.get("desc_dime"),
            long_description=row.get("long_description"),
            code_dime=row.get("code_dime"),
            perspective_dime=row.get("perspective_dime"),
            display_order=index + 1,
        )
        db.session.add(entity)
        db.session.flush()
        if legacy_id is not None:
            dim_by_legacy[int(legacy_id)] = entity.id

    for index, row in enumerate(payload.get("domains") or []):
        legacy_id = row.get("id_doma")
        entity = FrameworkDomain(
            framework_id=framework_id,
            legacy_id_doma=int(legacy_id) if legacy_id is not None else None,
            domain_key=row.get("domain_key"),
            name_doma=row.get("name_doma") or "",
            desc_doma=row.get("desc_doma"),
            vetor_estrategico=row.get("vetor_estrategico"),
            display_order=index + 1,
        )
        db.session.add(entity)
        db.session.flush()
        if legacy_id is not None:
            dom_by_legacy[int(legacy_id)] = entity.id

    for row in payload.get("blocks") or []:
        legacy_bloc = row.get("id_bloc")
        legacy_dime = row.get("id_dime")
        legacy_doma = row.get("id_doma")
        entity = FrameworkBlock(
            framework_id=framework_id,
            dimension_id=dim_by_legacy.get(int(legacy_dime)) if legacy_dime is not None else None,
            domain_id=dom_by_legacy.get(int(legacy_doma)) if legacy_doma is not None else None,
            legacy_id_bloc=int(legacy_bloc) if legacy_bloc is not None else None,
            name_bloc=row.get("name_bloc") or "",
            desc_bloc=row.get("desc_bloc"),
            level_bloc=row.get("level_bloc"),
            quali_bloc=row.get("quali_bloc"),
        )
        db.session.add(entity)
        db.session.flush()
        if legacy_bloc is not None:
            block_by_legacy[int(legacy_bloc)] = entity.id

    derv_count = 0
    for row in payload.get("deliverables") or []:
        legacy_derv = row.get("id_derv")
        legacy_bloc = row.get("id_bloc")
        block_id = block_by_legacy.get(int(legacy_bloc)) if legacy_bloc is not None else None
        if not block_id:
            continue
        db.session.add(
            FrameworkDeliverable(
                framework_id=framework_id,
                block_id=block_id,
                legacy_id_derv=int(legacy_derv) if legacy_derv is not None else None,
                name_derv=row.get("name_derv") or "",
                desc_derv=row.get("desc_derv"),
                derv_defi=row.get("derv_defi"),
                derv_comp=row.get("derv_comp"),
                derv_metr=row.get("derv_metr"),
                criteria_dod=row.get("criteria_dod") or {},
            )
        )
        derv_count += 1

    counts = {
        "dimensions": len(payload.get("dimensions") or []),
        "domains": len(payload.get("domains") or []),
        "blocks": len(payload.get("blocks") or []),
        "deliverables": derv_count,
    }

    meta = dict(framework.rules_metadata or {})
    meta["taxonomy_counts"] = counts
    meta["taxonomy_imported"] = True
    framework.rules_metadata = meta
    db.session.commit()

    logger.info(
        "Taxonomia '%s': %d dim, %d dom, %d blocos, %d entregáveis.",
        framework_id,
        counts["dimensions"],
        counts["domains"],
        counts["blocks"],
        counts["deliverables"],
    )
    return counts


def get_framework_taxonomy(framework_id: str) -> dict[str, Any]:
    """Retorna taxonomia completa para API/UI."""
    dimensions = (
        FrameworkDimension.query.filter_by(framework_id=framework_id)
        .order_by(FrameworkDimension.display_order.asc(), FrameworkDimension.legacy_id_dime.asc())
        .all()
    )
    domains = (
        FrameworkDomain.query.filter_by(framework_id=framework_id)
        .order_by(FrameworkDomain.display_order.asc(), FrameworkDomain.legacy_id_doma.asc())
        .all()
    )
    blocks = (
        FrameworkBlock.query.filter_by(framework_id=framework_id)
        .order_by(
            FrameworkBlock.level_bloc.asc().nullslast(),
            FrameworkBlock.legacy_id_bloc.asc().nullslast(),
        )
        .all()
    )
    deliverables = (
        FrameworkDeliverable.query.filter_by(framework_id=framework_id)
        .order_by(FrameworkDeliverable.legacy_id_derv.asc().nullslast())
        .all()
    )

    dim_map = {str(d.id): d for d in dimensions}
    dom_map = {str(d.id): d for d in domains}
    block_map = {str(b.id): b for b in blocks}

    return {
        "framework_id": framework_id,
        "counts": {
            "dimensions": len(dimensions),
            "domains": len(domains),
            "blocks": len(blocks),
            "deliverables": len(deliverables),
        },
        "dimensions": [_serialize_dimension(d) for d in dimensions],
        "domains": [_serialize_domain(d) for d in domains],
        "blocks": [_serialize_block(b, dim_map, dom_map) for b in blocks],
        "deliverables": [_serialize_deliverable(d, block_map) for d in deliverables],
    }


def ensure_framework_taxonomy(
    framework_id: str,
    *,
    force: bool = False,
) -> dict[str, int]:
    """Garante taxonomia persistida; educação importa do PanelDX legado."""
    existing = FrameworkDimension.query.filter_by(framework_id=framework_id).count()
    if existing > 0 and not force:
        return {
            "dimensions": existing,
            "domains": FrameworkDomain.query.filter_by(framework_id=framework_id).count(),
            "blocks": FrameworkBlock.query.filter_by(framework_id=framework_id).count(),
            "deliverables": FrameworkDeliverable.query.filter_by(framework_id=framework_id).count(),
        }

    framework = db.session.get(Framework, framework_id)
    if not framework:
        raise ValueError(f"Framework '{framework_id}' não encontrado.")

    if is_canonical_education_framework(framework_id):
        return import_taxonomy_from_legacy(framework_id)

    meta = framework.rules_metadata or {}
    methodology = meta.get("methodology_document")
    if methodology:
        return import_taxonomy_from_methodology_document(framework_id, methodology)

    return import_taxonomy_from_legacy(framework_id)


def _serialize_dimension(d: FrameworkDimension) -> dict[str, Any]:
    return {
        "id": str(d.id),
        "legacy_id_dime": d.legacy_id_dime,
        "dimension_key": d.dimension_key,
        "name_dime": d.name_dime,
        "desc_dime": d.desc_dime,
        "long_description": d.long_description,
        "code_dime": d.code_dime,
        "perspective_dime": d.perspective_dime,
        "display_order": d.display_order,
    }


def _serialize_domain(d: FrameworkDomain) -> dict[str, Any]:
    return {
        "id": str(d.id),
        "legacy_id_doma": d.legacy_id_doma,
        "domain_key": d.domain_key,
        "name_doma": d.name_doma,
        "desc_doma": d.desc_doma,
        "vetor_estrategico": d.vetor_estrategico,
        "display_order": d.display_order,
    }


def _serialize_block(
    b: FrameworkBlock,
    dim_map: dict[str, FrameworkDimension],
    dom_map: dict[str, FrameworkDomain],
) -> dict[str, Any]:
    dim = dim_map.get(str(b.dimension_id)) if b.dimension_id else None
    dom = dom_map.get(str(b.domain_id)) if b.domain_id else None
    return {
        "id": str(b.id),
        "legacy_id_bloc": b.legacy_id_bloc,
        "dimension_id": str(b.dimension_id) if b.dimension_id else None,
        "domain_id": str(b.domain_id) if b.domain_id else None,
        "legacy_id_dime": dim.legacy_id_dime if dim else None,
        "legacy_id_doma": dom.legacy_id_doma if dom else None,
        "dimension_key": dim.dimension_key if dim else None,
        "dimension_name": dim.name_dime if dim else None,
        "domain_key": dom.domain_key if dom else None,
        "domain_name": dom.name_doma if dom else None,
        "name_bloc": b.name_bloc,
        "desc_bloc": b.desc_bloc,
        "level_bloc": b.level_bloc,
        "quali_bloc": b.quali_bloc,
    }


def _serialize_deliverable(
    d: FrameworkDeliverable,
    block_map: dict[str, FrameworkBlock],
) -> dict[str, Any]:
    block = block_map.get(str(d.block_id))
    return {
        "id": str(d.id),
        "legacy_id_derv": d.legacy_id_derv,
        "block_id": str(d.block_id),
        "legacy_id_bloc": block.legacy_id_bloc if block else None,
        "block_name": block.name_bloc if block else None,
        "name_derv": d.name_derv,
        "desc_derv": d.desc_derv,
        "derv_defi": d.derv_defi,
        "derv_comp": d.derv_comp,
        "derv_metr": d.derv_metr,
        "criteria_dod": d.criteria_dod or {},
    }
