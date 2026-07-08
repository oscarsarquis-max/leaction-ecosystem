"""Exportacao/importacao de frameworks completos (metodologia + questoes + taxonomia)."""

from __future__ import annotations

import gzip
import json
import uuid
from typing import Any

from app.database.models import (
    AssessmentItem,
    Framework,
    FrameworkBlock,
    FrameworkDeliverable,
    FrameworkDimension,
    FrameworkDomain,
    MaturityLevel,
    db,
)


def _serialize_framework(framework: Framework) -> dict[str, Any]:
    return {
        "id": framework.id,
        "name": framework.name,
        "industry": framework.industry,
        "version": framework.version,
        "rules_metadata": framework.rules_metadata,
        "is_active": framework.is_active,
    }


def load_framework_bundle_file(path: str) -> dict[str, Any]:
    if path.endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            return json.load(handle)
    with open(path, encoding="utf-8-sig") as handle:
        return json.load(handle)


def export_framework_bundle(framework_id: str) -> dict[str, Any]:
    framework = db.session.get(Framework, framework_id)
    if not framework:
        raise ValueError(f"Framework '{framework_id}' nao encontrado.")

    dimensions = FrameworkDimension.query.filter_by(framework_id=framework_id).all()
    domains = FrameworkDomain.query.filter_by(framework_id=framework_id).all()
    blocks = FrameworkBlock.query.filter_by(framework_id=framework_id).all()
    deliverables = FrameworkDeliverable.query.filter_by(framework_id=framework_id).all()
    items = AssessmentItem.query.filter_by(framework_id=framework_id).all()
    levels = MaturityLevel.query.filter_by(framework_id=framework_id).all()

    return {
        "version": 1,
        "framework_id": framework_id,
        "framework": _serialize_framework(framework),
        "maturity_levels": [
            {
                "id": str(level.id),
                "level": level.level,
                "name": level.name,
                "description": level.description,
            }
            for level in levels
        ],
        "dimensions": [
            {
                "id": str(row.id),
                "legacy_id_dime": row.legacy_id_dime,
                "dimension_key": row.dimension_key,
                "name_dime": row.name_dime,
                "desc_dime": row.desc_dime,
                "long_description": row.long_description,
                "code_dime": row.code_dime,
                "perspective_dime": row.perspective_dime,
                "display_order": row.display_order,
            }
            for row in dimensions
        ],
        "domains": [
            {
                "id": str(row.id),
                "legacy_id_doma": row.legacy_id_doma,
                "domain_key": row.domain_key,
                "name_doma": row.name_doma,
                "desc_doma": row.desc_doma,
                "vetor_estrategico": row.vetor_estrategico,
                "display_order": row.display_order,
            }
            for row in domains
        ],
        "blocks": [
            {
                "id": str(row.id),
                "dimension_id": str(row.dimension_id) if row.dimension_id else None,
                "domain_id": str(row.domain_id) if row.domain_id else None,
                "legacy_id_bloc": row.legacy_id_bloc,
                "name_bloc": row.name_bloc,
                "desc_bloc": row.desc_bloc,
                "level_bloc": row.level_bloc,
                "quali_bloc": row.quali_bloc,
            }
            for row in blocks
        ],
        "deliverables": [
            {
                "id": str(row.id),
                "block_id": str(row.block_id),
                "legacy_id_derv": row.legacy_id_derv,
                "name_derv": row.name_derv,
                "desc_derv": row.desc_derv,
                "derv_defi": row.derv_defi,
                "derv_comp": row.derv_comp,
                "derv_metr": row.derv_metr,
                "criteria_dod": row.criteria_dod,
            }
            for row in deliverables
        ],
        "assessment_items": [
            {
                "id": str(item.id),
                "axis": item.axis,
                "question_text": item.question_text,
                "question_type": item.question_type,
                "options": item.options,
                "item_metadata": item.item_metadata,
            }
            for item in items
        ],
        "counts": {
            "assessment_items": len(items),
            "maturity_levels": len(levels),
            "dimensions": len(dimensions),
            "domains": len(domains),
            "blocks": len(blocks),
            "deliverables": len(deliverables),
        },
    }


def import_framework_bundle(
    bundle: dict[str, Any],
    *,
    replace: bool = True,
) -> dict[str, Any]:
    framework_data = bundle.get("framework") or {}
    framework_id = framework_data.get("id") or bundle.get("framework_id")
    if not framework_id:
        raise ValueError("Bundle sem framework_id.")

    existing = db.session.get(Framework, framework_id)
    if existing and replace:
        AssessmentItem.query.filter_by(framework_id=framework_id).delete(synchronize_session=False)
        MaturityLevel.query.filter_by(framework_id=framework_id).delete(synchronize_session=False)
        FrameworkDeliverable.query.filter_by(framework_id=framework_id).delete(synchronize_session=False)
        FrameworkBlock.query.filter_by(framework_id=framework_id).delete(synchronize_session=False)
        FrameworkDomain.query.filter_by(framework_id=framework_id).delete(synchronize_session=False)
        FrameworkDimension.query.filter_by(framework_id=framework_id).delete(synchronize_session=False)
        db.session.delete(existing)
        db.session.flush()
    elif existing and not replace:
        raise ValueError(f"Framework '{framework_id}' ja existe. Use replace=True.")

    framework = Framework(
        id=framework_id,
        name=framework_data["name"],
        industry=framework_data.get("industry"),
        version=framework_data.get("version"),
        rules_metadata=framework_data.get("rules_metadata"),
        is_active=bool(framework_data.get("is_active", True)),
    )
    db.session.add(framework)

    for row in bundle.get("maturity_levels") or []:
        db.session.add(
            MaturityLevel(
                id=uuid.UUID(row["id"]),
                framework_id=framework_id,
                level=int(row["level"]),
                name=row["name"],
                description=row.get("description"),
            )
        )

    for row in bundle.get("dimensions") or []:
        db.session.add(
            FrameworkDimension(
                id=uuid.UUID(row["id"]),
                framework_id=framework_id,
                legacy_id_dime=row.get("legacy_id_dime"),
                dimension_key=row.get("dimension_key"),
                name_dime=row["name_dime"],
                desc_dime=row.get("desc_dime"),
                long_description=row.get("long_description"),
                code_dime=row.get("code_dime"),
                perspective_dime=row.get("perspective_dime"),
                display_order=int(row.get("display_order") or 0),
            )
        )

    for row in bundle.get("domains") or []:
        db.session.add(
            FrameworkDomain(
                id=uuid.UUID(row["id"]),
                framework_id=framework_id,
                legacy_id_doma=row.get("legacy_id_doma"),
                domain_key=row.get("domain_key"),
                name_doma=row["name_doma"],
                desc_doma=row.get("desc_doma"),
                vetor_estrategico=row.get("vetor_estrategico"),
                display_order=int(row.get("display_order") or 0),
            )
        )

    for row in bundle.get("blocks") or []:
        db.session.add(
            FrameworkBlock(
                id=uuid.UUID(row["id"]),
                framework_id=framework_id,
                dimension_id=uuid.UUID(row["dimension_id"]) if row.get("dimension_id") else None,
                domain_id=uuid.UUID(row["domain_id"]) if row.get("domain_id") else None,
                legacy_id_bloc=row.get("legacy_id_bloc"),
                name_bloc=row["name_bloc"],
                desc_bloc=row.get("desc_bloc"),
                level_bloc=row.get("level_bloc"),
                quali_bloc=row.get("quali_bloc"),
            )
        )

    for row in bundle.get("deliverables") or []:
        db.session.add(
            FrameworkDeliverable(
                id=uuid.UUID(row["id"]),
                framework_id=framework_id,
                block_id=uuid.UUID(row["block_id"]),
                legacy_id_derv=row.get("legacy_id_derv"),
                name_derv=row["name_derv"],
                desc_derv=row.get("desc_derv"),
                derv_defi=row.get("derv_defi"),
                derv_comp=row.get("derv_comp"),
                derv_metr=row.get("derv_metr"),
                criteria_dod=row.get("criteria_dod"),
            )
        )

    for row in bundle.get("assessment_items") or []:
        db.session.add(
            AssessmentItem(
                id=uuid.UUID(row["id"]),
                framework_id=framework_id,
                axis=row["axis"],
                question_text=row["question_text"],
                question_type=row["question_type"],
                options=row.get("options"),
                item_metadata=row.get("item_metadata"),
            )
        )

    db.session.commit()
    counts = bundle.get("counts") or {}
    return {
        "status": "ok",
        "framework_id": framework_id,
        "name": framework.name,
        "counts": counts,
    }
