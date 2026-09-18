"""146 — preferências do gestor + disparo manual do job de onboarding."""
from __future__ import annotations

import os

from flask import Blueprint, jsonify, request
from psycopg2.extras import RealDictCursor

from auth_guards import current_gestor, require_gestor
from db import get_conn

bp = Blueprint("onboarding_mail", __name__)


def _job_secret_ok() -> bool:
    expected = (
        (os.getenv("SCHOOL_JOB_SECRET") or "").strip()
        or (os.getenv("SCHOOL_INTEGRATION_API_KEY") or "").strip()
        or (os.getenv("PRODUCTION_MASTER_KEY") or "").strip()
    )
    if not expected:
        return False
    got = (
        request.headers.get("x-school-job-secret")
        or request.headers.get("x-school-integration-key")
        or ""
    ).strip()
    return bool(got) and got == expected


@bp.get("/api/gestor/preferencias")
@require_gestor
def get_preferencias():
    user = current_gestor() or {}
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT recebe_resumo_diario
                  FROM public.school_gestores
                 WHERE id = %s::uuid
                """,
                (user.get("id"),),
            )
            row = cur.fetchone() or {}
    return jsonify(
        {
            "ok": True,
            "recebe_resumo_diario": bool(row.get("recebe_resumo_diario", True)),
        }
    )


@bp.patch("/api/gestor/preferencias")
@require_gestor
def patch_preferencias():
    user = current_gestor() or {}
    body = request.get_json(silent=True) or {}
    if "recebe_resumo_diario" not in body:
        return jsonify({"error": "Informe recebe_resumo_diario"}), 400
    value = bool(body.get("recebe_resumo_diario"))
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                UPDATE public.school_gestores
                   SET recebe_resumo_diario = %s
                 WHERE id = %s::uuid
             RETURNING recebe_resumo_diario
                """,
                (value, user.get("id")),
            )
            row = cur.fetchone()
    if not row:
        return jsonify({"error": "Gestor não encontrado"}), 404
    return jsonify({"ok": True, "recebe_resumo_diario": bool(row["recebe_resumo_diario"])})


@bp.post("/api/jobs/onboarding-mail/run")
def run_onboarding_mail():
    if not _job_secret_ok():
        return jsonify({"ok": False, "error": "não autorizado"}), 401
    body = request.get_json(silent=True) or {}
    from onboarding_mail import parse_allowlist, run_job

    allow = parse_allowlist(body.get("allowlist") if isinstance(body.get("allowlist"), str) else "")
    if isinstance(body.get("allowlist"), list):
        allow = parse_allowlist(",".join(str(x) for x in body.get("allowlist")))
    report = run_job(
        control=bool(body["control"]) if "control" in body else None,
        allowlist=allow or None,
        dry_run=bool(body.get("dry_run")),
        preview_teacher=bool(body.get("preview_teacher")),
    )
    return jsonify(report), (200 if report.get("ok") else 500)
