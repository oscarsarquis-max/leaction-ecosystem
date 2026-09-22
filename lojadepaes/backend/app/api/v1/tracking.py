"""Proxy do navegador para o Action-Sponge. O segredo fica só no servidor."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.api.deps import AppSettings
from app.domain.crm_tracking import build_hub_body, emit_tracking

router = APIRouter(tags=["tracking"])


@router.post("/api/tracking/enviar")
async def tracking_enviar(request: Request, settings: AppSettings) -> JSONResponse:
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}

    id_sessao = str(payload.get("id_sessao") or "").strip()
    tipo_evento = str(payload.get("tipo_evento") or "pageview").strip()
    if not id_sessao:
        return JSONResponse({"ok": False, "error": "id_sessao obrigatório"}, status_code=400)

    forwarded = request.headers.get("x-forwarded-for") or ""
    if forwarded:
        ip_real = forwarded.split(",")[0].strip()
    elif request.client is not None:
        ip_real = request.client.host
    else:
        ip_real = ""
    body = build_hub_body(
        id_sessao=id_sessao,
        tipo_evento=tipo_evento,
        url_pagina=str(payload.get("url_pagina") or "/"),
        id_usuario=payload.get("id_usuario"),
        dados=payload.get("dados"),
        ip_real=ip_real,
        user_agent=request.headers.get("user-agent") or "",
    )
    if body is None:
        return JSONResponse({"ok": False, "error": "id_sessao deve ser UUID"}, status_code=400)
    emit_tracking(settings, body)
    return JSONResponse({"ok": True, "forwarded": True}, status_code=202)
