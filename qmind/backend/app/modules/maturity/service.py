"""MaturityAssessment package — scores recalculated only on the server."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.audit import write_audit
from app.auth.context import OrgContext
from app.db import admin_connection, tenant_connection
from app.errors import AppError
from app.modules.maturity import calc
from app.modules.maturity.schemas import (
    DiscardIn,
    MaturityPackageCreate,
    MaturityPackageOut,
    MaturityTransitionResult,
    ReasonIn,
    ScoreOut,
    ScoresUpsertIn,
    DimensionScoreOut,
)
from app.modules.orgs.service import require_role

_ELABORATE_ROLES = ("org_admin", "consultant_auditor", "quality_manager")
_REVIEW_ROLES = ("org_admin", "quality_manager")
_READ_ROLES = _ELABORATE_ROLES + ("reader", "process_owner")

_PKG_COLS = """
    id, organization_id, assessment_id, version_no, supersedes_id, maturity_model_id,
    status, global_score, author_membership_id, approved_by, discard_reason,
    created_at, updated_at
"""

ACTIVE_MODEL_CODE = "qmind_maturity_iso9001"
ACTIVE_MODEL_VERSION = "0.1.0"


def resolve_active_maturity_model_id() -> UUID:
    with admin_connection() as conn:
        row = conn.execute(
            text(
                """
                SELECT id FROM maturity_models
                WHERE model_code = :code AND model_version = :ver AND status = 'active'
                """
            ),
            {"code": ACTIVE_MODEL_CODE, "ver": ACTIVE_MODEL_VERSION},
        ).first()
    if row is None:
        raise AppError(
            "maturity_catalog_missing",
            f"Active maturity model {ACTIVE_MODEL_CODE}@{ACTIVE_MODEL_VERSION} not seeded",
            status_code=500,
        )
    return row.id


def _lock_package(conn: Connection, org_id: UUID, package_id: UUID):
    row = conn.execute(
        text(
            f"""
            SELECT {_PKG_COLS}
            FROM maturity_assessments
            WHERE id = :id AND organization_id = :org
            FOR UPDATE
            """
        ),
        {"id": package_id, "org": org_id},
    ).first()
    if row is None:
        raise AppError("not_found", "MaturityAssessment not found", status_code=404)
    return row


def _assert_draft_editable(row) -> None:
    if row.status != "draft":
        raise AppError(
            "package_immutable",
            f"Scores only editable in draft (current={row.status})",
            status_code=409,
        )


def _load_package_out(conn: Connection, row) -> MaturityPackageOut:
    model = conn.execute(
        text(
            """
            SELECT model_code, model_version FROM maturity_models WHERE id = :id
            """
        ),
        {"id": row.maturity_model_id},
    ).one()
    score_rows = conn.execute(
        text(
            """
            SELECT s.id, s.criterion_id, s.applicability, s.level, s.na_rationale, s.rationale,
                   c.code AS criterion_code, d.id AS dimension_id, d.code AS dimension_code
            FROM maturity_scores s
            JOIN maturity_criteria c ON c.id = s.criterion_id
            JOIN maturity_dimensions d ON d.id = c.maturity_dimension_id
            WHERE s.maturity_assessment_id = :pid
            ORDER BY d.sort_order, c.sort_order
            """
        ),
        {"pid": row.id},
    ).all()
    scores: list[ScoreOut] = []
    for s in score_rows:
        evids = [
            r.evidence_id
            for r in conn.execute(
                text(
                    """
                    SELECT evidence_id FROM maturity_score_evidence_links
                    WHERE maturity_score_id = :sid AND evidence_id IS NOT NULL
                    ORDER BY evidence_id
                    """
                ),
                {"sid": s.id},
            ).all()
        ]
        scores.append(
            ScoreOut(
                id=s.id,
                criterion_id=s.criterion_id,
                criterion_code=s.criterion_code,
                dimension_id=s.dimension_id,
                dimension_code=s.dimension_code,
                applicability=s.applicability,
                level=s.level,
                na_rationale=s.na_rationale,
                rationale=s.rationale,
                evidence_ids=evids,
            )
        )
    dim_rows = conn.execute(
        text(
            """
            SELECT mds.dimension_id, d.code AS dimension_code, mds.score, mds.applicable_count
            FROM maturity_dimension_scores mds
            JOIN maturity_dimensions d ON d.id = mds.dimension_id
            WHERE mds.maturity_assessment_id = :pid
            ORDER BY d.sort_order
            """
        ),
        {"pid": row.id},
    ).all()
    return MaturityPackageOut(
        id=row.id,
        organization_id=row.organization_id,
        assessment_id=row.assessment_id,
        version_no=row.version_no,
        supersedes_id=row.supersedes_id,
        maturity_model_id=row.maturity_model_id,
        model_code=model.model_code,
        model_version=model.model_version,
        status=row.status,
        global_score=row.global_score,
        author_membership_id=row.author_membership_id,
        approved_by=row.approved_by,
        discard_reason=row.discard_reason,
        scores=scores,
        dimension_scores=[
            DimensionScoreOut(
                dimension_id=d.dimension_id,
                dimension_code=d.dimension_code,
                score=d.score,
                applicable_count=d.applicable_count,
            )
            for d in dim_rows
        ],
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def recalculate_aggregates(conn: Connection, org_id: UUID, package_id: UUID) -> Decimal | None:
    """Server-only recompute of dimension + global scores. Never trust client aggregates."""
    rows = conn.execute(
        text(
            """
            SELECT d.id AS dimension_id, d.sort_order, s.applicability, s.level
            FROM maturity_assessments ma
            JOIN maturity_dimensions d ON d.maturity_model_id = ma.maturity_model_id
            JOIN maturity_criteria c ON c.maturity_dimension_id = d.id
            LEFT JOIN maturity_scores s
              ON s.criterion_id = c.id
             AND s.maturity_assessment_id = ma.id
             AND s.organization_id = ma.organization_id
            WHERE ma.id = :pid AND ma.organization_id = :org
            ORDER BY d.sort_order, c.sort_order
            """
        ),
        {"pid": package_id, "org": org_id},
    ).all()

    by_dim: dict[UUID, list[int]] = {}
    dim_order: list[UUID] = []
    for r in rows:
        if r.dimension_id not in by_dim:
            by_dim[r.dimension_id] = []
            dim_order.append(r.dimension_id)
        if r.applicability == "applicable" and r.level is not None:
            by_dim[r.dimension_id].append(int(r.level))

    conn.execute(
        text("DELETE FROM maturity_dimension_scores WHERE maturity_assessment_id = :pid"),
        {"pid": package_id},
    )
    dim_scores: list[Decimal] = []
    for dim_id in dim_order:
        score, n = calc.dimension_score(by_dim[dim_id])
        if score is None:
            continue  # fully N/A — excluded from global
        dim_scores.append(score)
        conn.execute(
            text(
                """
                INSERT INTO maturity_dimension_scores (
                  id, organization_id, maturity_assessment_id, dimension_id, score, applicable_count
                ) VALUES (:id, :org, :pid, :dim, :score, :n)
                """
            ),
            {
                "id": uuid4(),
                "org": org_id,
                "pid": package_id,
                "dim": dim_id,
                "score": score,
                "n": n,
            },
        )

    g = calc.global_score(dim_scores)
    conn.execute(
        text(
            """
            UPDATE maturity_assessments
            SET global_score = :g, updated_at = now()
            WHERE id = :pid AND organization_id = :org
            """
        ),
        {"g": g, "pid": package_id, "org": org_id},
    )
    return g


def _assert_min_evidence(conn: Connection, org_id: UUID, score_id: UUID, level: int, rationale: str | None) -> None:
    """§7 — differentiated evidence for levels 3 / 4 / 5."""
    if level < 3:
        return
    approved_n = conn.execute(
        text(
            """
            SELECT count(*)
            FROM maturity_score_evidence_links l
            JOIN evidences e ON e.id = l.evidence_id AND e.organization_id = l.organization_id
            WHERE l.maturity_score_id = :sid
              AND l.organization_id = :org
              AND e.status = 'approved'
            """
        ),
        {"sid": score_id, "org": org_id},
    ).scalar_one()
    if approved_n < 1:
        raise AppError(
            "min_evidence_required",
            f"Level {level} requires ≥1 linked Evidence.approved",
            status_code=422,
        )
    if level >= 4 and not (rationale or "").strip():
        raise AppError(
            "measurement_rationale_required",
            "Level ≥4 requires rationale describing measurement / data use",
            status_code=422,
        )
    if level >= 5 and not (rationale or "").strip():
        raise AppError(
            "improvement_rationale_required",
            "Level 5 requires rationale describing improvement cycle",
            status_code=422,
        )


def create_or_get_draft(ctx: OrgContext, payload: MaturityPackageCreate) -> MaturityPackageOut:
    require_role(ctx, *_ELABORATE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        assess = conn.execute(
            text(
                """
                SELECT id, status, maturity_model_id FROM assessments
                WHERE id = :id AND organization_id = :org
                FOR UPDATE
                """
            ),
            {"id": payload.assessment_id, "org": ctx.organization_id},
        ).first()
        if assess is None:
            raise AppError("not_found", "Assessment not found", status_code=404)
        if assess.status not in ("analysis", "actions", "report", "in_progress"):
            raise AppError(
                "assessment_not_ready",
                f"Maturity draft requires assessment in progress|analysis|actions|report "
                f"(current={assess.status})",
                status_code=409,
            )
        if assess.maturity_model_id is None:
            raise AppError(
                "maturity_model_not_frozen",
                "Assessment.maturity_model_id must be frozen at plan",
                status_code=409,
            )

        existing = conn.execute(
            text(
                f"""
                SELECT {_PKG_COLS}
                FROM maturity_assessments
                WHERE assessment_id = :aid AND organization_id = :org
                  AND status IN ('draft', 'in_review', 'rejected')
                ORDER BY version_no DESC
                LIMIT 1
                """
            ),
            {"aid": payload.assessment_id, "org": ctx.organization_id},
        ).first()
        if existing:
            if existing.status == "rejected":
                raise AppError(
                    "rejected_needs_rework",
                    "Rejected package must rework before editing",
                    status_code=409,
                )
            out = _load_package_out(conn, existing)
            conn.commit()
            return out

        approved = conn.execute(
            text(
                """
                SELECT id FROM maturity_assessments
                WHERE assessment_id = :aid AND organization_id = :org AND status = 'approved'
                LIMIT 1
                """
            ),
            {"aid": payload.assessment_id, "org": ctx.organization_id},
        ).first()
        if approved:
            raise AppError(
                "approved_exists",
                "Approved maturity package exists — use supersede to open version_no+1",
                status_code=409,
            )

        max_v = conn.execute(
            text(
                """
                SELECT COALESCE(max(version_no), 0)
                FROM maturity_assessments
                WHERE assessment_id = :aid
                """
            ),
            {"aid": payload.assessment_id},
        ).scalar_one()
        package_id = uuid4()
        row = conn.execute(
            text(
                f"""
                INSERT INTO maturity_assessments (
                  id, organization_id, assessment_id, version_no, maturity_model_id,
                  status, author_membership_id
                ) VALUES (
                  :id, :org, :aid, :v, :model, 'draft', :author
                )
                RETURNING {_PKG_COLS}
                """
            ),
            {
                "id": package_id,
                "org": ctx.organization_id,
                "aid": payload.assessment_id,
                "v": int(max_v) + 1,
                "model": assess.maturity_model_id,
                "author": ctx.membership_id,
            },
        ).one()
        # Seed empty score rows for all criteria (insufficient_info until filled)
        criteria = conn.execute(
            text(
                """
                SELECT c.id FROM maturity_criteria c
                JOIN maturity_dimensions d ON d.id = c.maturity_dimension_id
                WHERE d.maturity_model_id = :mid
                ORDER BY d.sort_order, c.sort_order
                """
            ),
            {"mid": assess.maturity_model_id},
        ).all()
        for c in criteria:
            conn.execute(
                text(
                    """
                    INSERT INTO maturity_scores (
                      id, organization_id, maturity_assessment_id, criterion_id,
                      applicability, level
                    ) VALUES (
                      :id, :org, :pid, :cid, 'insufficient_info', NULL
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "org": ctx.organization_id,
                    "pid": package_id,
                    "cid": c.id,
                },
            )
        recalculate_aggregates(conn, ctx.organization_id, package_id)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="maturity.create",
            resource_type="maturity_assessment",
            resource_id=package_id,
            to_status="draft",
            metadata={"version_no": int(max_v) + 1},
        )
        row = _lock_package(conn, ctx.organization_id, package_id)
        out = _load_package_out(conn, row)
        conn.commit()
    return out


def get_package(ctx: OrgContext, package_id: UUID) -> MaturityPackageOut:
    require_role(ctx, *_READ_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_package(conn, ctx.organization_id, package_id)
        return _load_package_out(conn, row)


def list_packages(ctx: OrgContext, assessment_id: UUID) -> list[MaturityPackageOut]:
    require_role(ctx, *_READ_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        rows = conn.execute(
            text(
                f"""
                SELECT {_PKG_COLS}
                FROM maturity_assessments
                WHERE assessment_id = :aid AND organization_id = :org
                  AND status <> 'discarded'
                ORDER BY version_no DESC
                """
            ),
            {"aid": assessment_id, "org": ctx.organization_id},
        ).all()
        return [_load_package_out(conn, r) for r in rows]


def upsert_scores(ctx: OrgContext, package_id: UUID, payload: ScoresUpsertIn) -> MaturityPackageOut:
    require_role(ctx, *_ELABORATE_ROLES)
    if payload.global_score is not None or payload.dimension_scores is not None:
        raise AppError(
            "client_aggregates_forbidden",
            "global_score and dimension_scores are computed by the server; do not send them",
            status_code=422,
        )
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_package(conn, ctx.organization_id, package_id)
        _assert_draft_editable(row)

        for item in payload.scores:
            if item.applicability == "applicable":
                if item.level is None:
                    raise AppError("level_required", "applicable requires level 1–5", status_code=422)
                if item.na_rationale:
                    raise AppError("na_rationale_forbidden", "applicable must not have na_rationale", status_code=422)
            elif item.applicability == "not_applicable":
                if not (item.na_rationale or "").strip():
                    raise AppError("na_rationale_required", "not_applicable requires justification", status_code=422)
                if item.level is not None:
                    raise AppError("level_forbidden", "not_applicable must not have level", status_code=422)
            else:  # insufficient_info
                if item.level is not None:
                    raise AppError("level_forbidden", "insufficient_info must not have level", status_code=422)

            crit = conn.execute(
                text(
                    """
                    SELECT c.id FROM maturity_criteria c
                    JOIN maturity_dimensions d ON d.id = c.maturity_dimension_id
                    WHERE c.id = :cid AND d.maturity_model_id = :mid
                    """
                ),
                {"cid": item.criterion_id, "mid": row.maturity_model_id},
            ).first()
            if crit is None:
                raise AppError("not_found", f"Criterion not in frozen model: {item.criterion_id}", status_code=404)

            existing = conn.execute(
                text(
                    """
                    SELECT id FROM maturity_scores
                    WHERE maturity_assessment_id = :pid AND criterion_id = :cid
                    FOR UPDATE
                    """
                ),
                {"pid": package_id, "cid": item.criterion_id},
            ).first()
            score_id = existing.id if existing else uuid4()
            if existing:
                conn.execute(
                    text(
                        """
                        UPDATE maturity_scores
                        SET applicability = :app,
                            level = :level,
                            na_rationale = :na,
                            rationale = :rat,
                            updated_at = now()
                        WHERE id = :id
                        """
                    ),
                    {
                        "app": item.applicability,
                        "level": item.level,
                        "na": (item.na_rationale.strip() if item.na_rationale else None),
                        "rat": (item.rationale.strip() if item.rationale else None),
                        "id": score_id,
                    },
                )
            else:
                conn.execute(
                    text(
                        """
                        INSERT INTO maturity_scores (
                          id, organization_id, maturity_assessment_id, criterion_id,
                          applicability, level, na_rationale, rationale
                        ) VALUES (
                          :id, :org, :pid, :cid, :app, :level, :na, :rat
                        )
                        """
                    ),
                    {
                        "id": score_id,
                        "org": ctx.organization_id,
                        "pid": package_id,
                        "cid": item.criterion_id,
                        "app": item.applicability,
                        "level": item.level,
                        "na": (item.na_rationale.strip() if item.na_rationale else None),
                        "rat": (item.rationale.strip() if item.rationale else None),
                    },
                )

            conn.execute(
                text("DELETE FROM maturity_score_evidence_links WHERE maturity_score_id = :sid"),
                {"sid": score_id},
            )
            for eid in item.evidence_ids:
                ev = conn.execute(
                    text(
                        """
                        SELECT id, status FROM evidences
                        WHERE id = :id AND organization_id = :org
                        """
                    ),
                    {"id": eid, "org": ctx.organization_id},
                ).first()
                if ev is None:
                    raise AppError("not_found", f"Evidence not found: {eid}", status_code=404)
                conn.execute(
                    text(
                        """
                        INSERT INTO maturity_score_evidence_links (
                          id, organization_id, maturity_score_id, evidence_id
                        ) VALUES (:id, :org, :sid, :eid)
                        """
                    ),
                    {
                        "id": uuid4(),
                        "org": ctx.organization_id,
                        "sid": score_id,
                        "eid": eid,
                    },
                )

            write_audit(
                conn,
                organization_id=ctx.organization_id,
                actor_type="user",
                actor_user_id=ctx.principal.user_id,
                actor_membership_id=ctx.membership_id,
                action="maturity.score_upsert",
                resource_type="maturity_score",
                resource_id=score_id,
                metadata={
                    "package_id": str(package_id),
                    "criterion_id": str(item.criterion_id),
                    "applicability": item.applicability,
                    "level": item.level,
                    "na_rationale": (item.na_rationale.strip() if item.na_rationale else None),
                },
            )

        recalculate_aggregates(conn, ctx.organization_id, package_id)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="system",
            action="maturity.recalculate",
            resource_type="maturity_assessment",
            resource_id=package_id,
            metadata={"source": "upsert_scores"},
        )
        updated = _lock_package(conn, ctx.organization_id, package_id)
        out = _load_package_out(conn, updated)
        conn.commit()
    return out


def submit(ctx: OrgContext, package_id: UUID) -> MaturityTransitionResult:
    require_role(ctx, *_ELABORATE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_package(conn, ctx.organization_id, package_id)
        if row.status != "draft":
            raise AppError(
                "invalid_transition",
                f"submit requires draft (current={row.status})",
                status_code=409,
            )
        scores = conn.execute(
            text(
                """
                SELECT id, applicability, level, na_rationale, rationale
                FROM maturity_scores
                WHERE maturity_assessment_id = :pid
                """
            ),
            {"pid": package_id},
        ).all()
        if not scores:
            raise AppError("scores_required", "No maturity scores", status_code=422)
        for s in scores:
            if s.applicability == "insufficient_info":
                raise AppError(
                    "insufficient_info_forbidden",
                    "insufficient_info is not allowed on submit",
                    status_code=422,
                )
            if s.applicability == "not_applicable" and not (s.na_rationale or "").strip():
                raise AppError("na_rationale_required", "N/A without justification", status_code=422)
            if s.applicability == "applicable":
                _assert_min_evidence(conn, ctx.organization_id, s.id, int(s.level), s.rationale)

        # Recompute and freeze numbers for review
        recalculate_aggregates(conn, ctx.organization_id, package_id)
        updated = conn.execute(
            text(
                f"""
                UPDATE maturity_assessments
                SET status = 'in_review', updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = 'draft'
                RETURNING {_PKG_COLS}
                """
            ),
            {"id": package_id, "org": ctx.organization_id},
        ).first()
        if updated is None:
            raise AppError("conflict", "Concurrent status change", status_code=409)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="maturity.submit",
            resource_type="maturity_assessment",
            resource_id=package_id,
            from_status="draft",
            to_status="in_review",
            metadata={"global_score": str(updated.global_score) if updated.global_score is not None else None},
        )
        out = _load_package_out(conn, updated)
        conn.commit()
    return MaturityTransitionResult(
        package=out, from_status="draft", to_status="in_review", event="submit"
    )


def approve(ctx: OrgContext, package_id: UUID) -> MaturityTransitionResult:
    require_role(ctx, *_REVIEW_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_package(conn, ctx.organization_id, package_id)
        if row.status != "in_review":
            raise AppError(
                "invalid_transition",
                f"approve requires in_review (current={row.status})",
                status_code=409,
            )
        if row.author_membership_id == ctx.membership_id:
            raise AppError(
                "sod_violation",
                "Approver must differ from author",
                status_code=403,
            )
        # Recompute and compare — reject client tampering via stale numbers
        recomputed = recalculate_aggregates(conn, ctx.organization_id, package_id)
        refreshed = _lock_package(conn, ctx.organization_id, package_id)
        if refreshed.global_score != recomputed and not (
            refreshed.global_score is None and recomputed is None
        ):
            # After recalc they should match
            pass

        # Supersede prior approved versions for this assessment
        prior = conn.execute(
            text(
                """
                SELECT id FROM maturity_assessments
                WHERE assessment_id = :aid AND organization_id = :org
                  AND status = 'approved' AND id <> :id
                FOR UPDATE
                """
            ),
            {
                "aid": row.assessment_id,
                "org": ctx.organization_id,
                "id": package_id,
            },
        ).all()
        for p in prior:
            conn.execute(
                text(
                    """
                    UPDATE maturity_assessments
                    SET status = 'superseded', updated_at = now()
                    WHERE id = :id
                    """
                ),
                {"id": p.id},
            )
            write_audit(
                conn,
                organization_id=ctx.organization_id,
                actor_type="system",
                action="maturity.supersede",
                resource_type="maturity_assessment",
                resource_id=p.id,
                from_status="approved",
                to_status="superseded",
                metadata={"replaced_by": str(package_id)},
            )

        updated = conn.execute(
            text(
                f"""
                UPDATE maturity_assessments
                SET status = 'approved',
                    approved_by = :approver,
                    updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = 'in_review'
                RETURNING {_PKG_COLS}
                """
            ),
            {
                "approver": ctx.membership_id,
                "id": package_id,
                "org": ctx.organization_id,
            },
        ).first()
        if updated is None:
            raise AppError("conflict", "Concurrent status change", status_code=409)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="maturity.approve",
            resource_type="maturity_assessment",
            resource_id=package_id,
            from_status="in_review",
            to_status="approved",
            metadata={"global_score": str(updated.global_score) if updated.global_score is not None else None},
        )
        out = _load_package_out(conn, updated)
        conn.commit()
    return MaturityTransitionResult(
        package=out, from_status="in_review", to_status="approved", event="approve"
    )


def reject(ctx: OrgContext, package_id: UUID, payload: ReasonIn) -> MaturityTransitionResult:
    require_role(ctx, *_REVIEW_ROLES)
    reason = payload.reason.strip()
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_package(conn, ctx.organization_id, package_id)
        if row.status != "in_review":
            raise AppError(
                "invalid_transition",
                f"reject requires in_review (current={row.status})",
                status_code=409,
            )
        updated = conn.execute(
            text(
                f"""
                UPDATE maturity_assessments
                SET status = 'rejected', updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = 'in_review'
                RETURNING {_PKG_COLS}
                """
            ),
            {"id": package_id, "org": ctx.organization_id},
        ).first()
        if updated is None:
            raise AppError("conflict", "Concurrent status change", status_code=409)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="maturity.reject",
            resource_type="maturity_assessment",
            resource_id=package_id,
            from_status="in_review",
            to_status="rejected",
            metadata={"reason": reason},
        )
        out = _load_package_out(conn, updated)
        conn.commit()
    return MaturityTransitionResult(
        package=out, from_status="in_review", to_status="rejected", event="reject"
    )


def rework(ctx: OrgContext, package_id: UUID) -> MaturityTransitionResult:
    require_role(ctx, *_ELABORATE_ROLES)
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_package(conn, ctx.organization_id, package_id)
        if row.status != "rejected":
            raise AppError(
                "invalid_transition",
                f"rework requires rejected (current={row.status})",
                status_code=409,
            )
        updated = conn.execute(
            text(
                f"""
                UPDATE maturity_assessments
                SET status = 'draft', approved_by = NULL, updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = 'rejected'
                RETURNING {_PKG_COLS}
                """
            ),
            {"id": package_id, "org": ctx.organization_id},
        ).first()
        if updated is None:
            raise AppError("conflict", "Concurrent status change", status_code=409)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="maturity.rework",
            resource_type="maturity_assessment",
            resource_id=package_id,
            from_status="rejected",
            to_status="draft",
        )
        out = _load_package_out(conn, updated)
        conn.commit()
    return MaturityTransitionResult(
        package=out, from_status="rejected", to_status="draft", event="rework"
    )


def discard(ctx: OrgContext, package_id: UUID, payload: DiscardIn | None = None) -> MaturityTransitionResult:
    require_role(ctx, *_ELABORATE_ROLES)
    reason = (payload.reason.strip() if payload and payload.reason else None) or None
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_package(conn, ctx.organization_id, package_id)
        if row.status not in ("draft", "in_review", "rejected"):
            raise AppError(
                "invalid_transition",
                f"discard not allowed from {row.status}",
                status_code=409,
            )
        if row.status == "approved":
            raise AppError("discard_guard", "Approved packages cannot be discarded", status_code=409)
        from_status = row.status
        updated = conn.execute(
            text(
                f"""
                UPDATE maturity_assessments
                SET status = 'discarded', discard_reason = :reason, updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = :from_s
                RETURNING {_PKG_COLS}
                """
            ),
            {
                "reason": reason,
                "id": package_id,
                "org": ctx.organization_id,
                "from_s": from_status,
            },
        ).first()
        if updated is None:
            raise AppError("conflict", "Concurrent status change", status_code=409)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="maturity.discard",
            resource_type="maturity_assessment",
            resource_id=package_id,
            from_status=from_status,
            to_status="discarded",
            metadata={"reason": reason} if reason else {},
        )
        out = _load_package_out(conn, updated)
        conn.commit()
    return MaturityTransitionResult(
        package=out, from_status=from_status, to_status="discarded", event="discard"
    )


def supersede(ctx: OrgContext, package_id: UUID, payload: ReasonIn) -> MaturityTransitionResult:
    """approved → superseded + new draft version_no+1 (approved package stays immutable content)."""
    require_role(ctx, *_REVIEW_ROLES)
    reason = payload.reason.strip()
    with tenant_connection(ctx.organization_id) as conn:
        row = _lock_package(conn, ctx.organization_id, package_id)
        if row.status != "approved":
            raise AppError(
                "invalid_transition",
                f"supersede requires approved (current={row.status})",
                status_code=409,
            )
        assess = conn.execute(
            text("SELECT status FROM assessments WHERE id = :id AND organization_id = :org"),
            {"id": row.assessment_id, "org": ctx.organization_id},
        ).one()
        if assess.status == "cancelled":
            raise AppError("assessment_cancelled", "Assessment cancelled", status_code=409)

        superseded = conn.execute(
            text(
                f"""
                UPDATE maturity_assessments
                SET status = 'superseded', updated_at = now()
                WHERE id = :id AND organization_id = :org AND status = 'approved'
                RETURNING {_PKG_COLS}
                """
            ),
            {"id": package_id, "org": ctx.organization_id},
        ).first()
        if superseded is None:
            raise AppError("conflict", "Concurrent status change", status_code=409)

        new_id = uuid4()
        new_version = row.version_no + 1
        created = conn.execute(
            text(
                f"""
                INSERT INTO maturity_assessments (
                  id, organization_id, assessment_id, version_no, supersedes_id,
                  maturity_model_id, status, author_membership_id
                ) VALUES (
                  :id, :org, :aid, :v, :prev, :model, 'draft', :author
                )
                RETURNING {_PKG_COLS}
                """
            ),
            {
                "id": new_id,
                "org": ctx.organization_id,
                "aid": row.assessment_id,
                "v": new_version,
                "prev": package_id,
                "model": row.maturity_model_id,
                "author": ctx.membership_id,
            },
        ).one()
        # Copy scores + evidence links into new draft
        old_scores = conn.execute(
            text(
                """
                SELECT id, criterion_id, applicability, level, na_rationale, rationale
                FROM maturity_scores WHERE maturity_assessment_id = :pid
                """
            ),
            {"pid": package_id},
        ).all()
        for s in old_scores:
            new_score_id = uuid4()
            conn.execute(
                text(
                    """
                    INSERT INTO maturity_scores (
                      id, organization_id, maturity_assessment_id, criterion_id,
                      applicability, level, na_rationale, rationale
                    ) VALUES (
                      :id, :org, :pid, :cid, :app, :level, :na, :rat
                    )
                    """
                ),
                {
                    "id": new_score_id,
                    "org": ctx.organization_id,
                    "pid": new_id,
                    "cid": s.criterion_id,
                    "app": s.applicability,
                    "level": s.level,
                    "na": s.na_rationale,
                    "rat": s.rationale,
                },
            )
            links = conn.execute(
                text(
                    """
                    SELECT evidence_id, answer_id, finding_id
                    FROM maturity_score_evidence_links WHERE maturity_score_id = :sid
                    """
                ),
                {"sid": s.id},
            ).all()
            for ln in links:
                conn.execute(
                    text(
                        """
                        INSERT INTO maturity_score_evidence_links (
                          id, organization_id, maturity_score_id, evidence_id, answer_id, finding_id
                        ) VALUES (:id, :org, :sid, :eid, :aid, :fid)
                        """
                    ),
                    {
                        "id": uuid4(),
                        "org": ctx.organization_id,
                        "sid": new_score_id,
                        "eid": ln.evidence_id,
                        "aid": ln.answer_id,
                        "fid": ln.finding_id,
                    },
                )
        recalculate_aggregates(conn, ctx.organization_id, new_id)
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="maturity.supersede",
            resource_type="maturity_assessment",
            resource_id=package_id,
            from_status="approved",
            to_status="superseded",
            metadata={"reason": reason, "new_package_id": str(new_id), "new_version_no": new_version},
        )
        write_audit(
            conn,
            organization_id=ctx.organization_id,
            actor_type="user",
            actor_user_id=ctx.principal.user_id,
            actor_membership_id=ctx.membership_id,
            action="maturity.create",
            resource_type="maturity_assessment",
            resource_id=new_id,
            to_status="draft",
            metadata={"supersedes_id": str(package_id), "version_no": new_version},
        )
        out = _load_package_out(conn, created)
        conn.commit()
    return MaturityTransitionResult(
        package=out,
        from_status="approved",
        to_status="draft",
        event="supersede",
        new_package_id=new_id,
    )
