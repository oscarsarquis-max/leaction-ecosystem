"""POST /api/receitas — repassa multipart ao Hub (BLOG-025). Não loga telefone."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from app import cms, rn


def hub_intake_url() -> str:
    return rn.hub_origin() + "/api/cms/receitas/intake"


def post_receita(request: Request, form: dict[str, Any], file_tuple: tuple | None) -> JSONResponse:
    # Campo-isca: deve vir vazio.
    if str(form.get("site") or "").strip():
        raise HTTPException(status_code=400, detail={"erro": "envio inválido", "campo": "site"})

    boundary = "----LepainReceitaBoundary7MA4YWxkTrZu0gW"
    lines: list[bytes] = []

    def add_field(name: str, value: str) -> None:
        lines.append(f"--{boundary}\r\n".encode())
        lines.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        lines.append(str(value or "").encode("utf-8"))
        lines.append(b"\r\n")

    for key in (
        "nome",
        "cidade",
        "telefone",
        "instagram",
        "titulo",
        "historia",
        "ingredientes",
        "preparo",
        "consentimento",
        "idioma",
        "site",
    ):
        if key in form:
            add_field(key, form.get(key))

    if file_tuple is not None:
        filename, content_type, raw = file_tuple
        lines.append(f"--{boundary}\r\n".encode())
        lines.append(
            (
                f'Content-Disposition: form-data; name="foto"; filename="{filename}"\r\n'
                f"Content-Type: {content_type}\r\n\r\n"
            ).encode()
        )
        lines.append(raw)
        lines.append(b"\r\n")

    lines.append(f"--{boundary}--\r\n".encode())
    body = b"".join(lines)

    req = urllib.request.Request(
        hub_intake_url(),
        data=body,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "X-LePain-Key": rn.secret(),
            "X-Forwarded-For": rn.client_ip(request),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            raw = res.read().decode()
            payload = json.loads(raw) if raw else {}
            status = res.status
    except urllib.error.HTTPError as err:
        raw = err.read().decode()
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"erro": "falha no Hub"}
        status = err.code
    except Exception:
        raise HTTPException(status_code=502, detail={"erro": "hub indisponível"}) from None

    if status == 201:
        return JSONResponse(
            {"ok": True, "cliente_loja": bool((payload or {}).get("cliente_loja"))},
            status_code=201,
        )
    if status == 429:
        return JSONResponse(payload or {"erro": "limite diário"}, status_code=429)
    if status == 400:
        return JSONResponse(payload or {"erro": "dados inválidos"}, status_code=400)
    raise HTTPException(status_code=502, detail={"erro": "falha no Hub"})
