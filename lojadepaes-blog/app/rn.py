"""Rotas de servidor do Right Now. O navegador fala com o blog; o blog fala com o Hub."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import urllib.error
import urllib.request
from datetime import datetime, timezone

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, Response

from app import cms

COOKIE = "lp_vid"
YEAR = 60 * 60 * 24 * 365
VID_RE = re.compile(r"^[A-Za-z0-9_-]{32,80}$")


def secret() -> str:
    return os.environ.get("LEPAIN_CMS_KEY", "").strip()


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded.strip():
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "0.0.0.0"


def visitor(request: Request) -> tuple[str, bool, str]:
    current = request.cookies.get(COOKIE, "")
    created = not VID_RE.fullmatch(current or "")
    vid = secrets.token_urlsafe(32) if created else current
    digest = hashlib.sha256((vid + secret()).encode()).hexdigest()
    return vid, created, digest


def attach(response: Response, vid: str, created: bool) -> Response:
    if created:
        response.set_cookie(
            COOKIE,
            vid,
            max_age=YEAR,
            httponly=True,
            samesite="lax",
            path="/",
        )
    return response


def hub_origin() -> str:
    base = cms.posts_base()
    suffix = "/api/cms/posts"
    if base.endswith(suffix):
        return base[: -len(suffix)]
    return base


def hub_request(method: str, path: str, body: dict | None, ip: str) -> tuple[int, object]:
    payload = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        hub_origin() + path,
        data=payload,
        method=method,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-LePain-Key": secret(),
            "X-Forwarded-For": ip,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=3.5) as res:
            raw = res.read().decode()
            return res.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as err:
        raw = err.read().decode()
        try:
            parsed = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            parsed = None
        return err.code, parsed


def lookup(slug: str) -> dict | None:
    if cms.source() == "hub":
        try:
            fetched = cms.fetch_hub_post(slug)
        except Exception:
            fetched = None
        if fetched and fetched.get("secao") == "right_now" and cms.visible(fetched) and fetched.get("id"):
            return fetched
    for post in cms.all_posts():
        if post.get("slug") == slug and post.get("secao") == "right_now" and cms.visible(post):
            return post if post.get("id") else None
    return None


def json_with_cookie(request: Request, payload, status: int = 200) -> JSONResponse:
    vid, created, _digest = visitor(request)
    response = JSONResponse(content=payload, status_code=status)
    return attach(response, vid, created)


def quero(request: Request, slug: str) -> JSONResponse:
    post = lookup(slug)
    if post is None or not post.get("id"):
        raise HTTPException(status_code=404)
    _vid, created, digest = visitor(request)
    status, body = hub_request(
        "POST",
        f"/api/cms/posts/{int(post['id'])}/quero",
        {"visitante": digest},
        client_ip(request),
    )
    if status != 200 or not isinstance(body, dict):
        raise HTTPException(status_code=status if status in {404, 401, 429} else 502)
    response = JSONResponse({"count": int(body.get("count") or 0), "voted": True})
    return attach(response, _vid, created)


def enquete(request: Request, idioma: str) -> JSONResponse:
    if idioma not in {"pt", "en"}:
        raise HTTPException(status_code=400)
    _vid, created, digest = visitor(request)
    status, body = hub_request(
        "GET",
        "/api/cms/enquetes/atual?visitante=" + digest,
        None,
        client_ip(request),
    )
    if status != 200:
        raise HTTPException(status_code=status if status in {401, 429} else 502)
    payload = map_enquete(body, idioma)
    response = JSONResponse(content=payload)
    return attach(response, _vid, created)


def map_enquete(body, idioma: str):
    if not isinstance(body, dict) or not body.get("id"):
        return None
    key = "en" if idioma == "en" else "pt"
    opcoes = []
    for item in body.get("opcoes") or []:
        if not isinstance(item, dict):
            continue
        opcoes.append({"id": item.get("id"), "texto": item.get(key) or ""})
    out = {
        "id": body.get("id"),
        "pergunta": body.get("pergunta_en") if key == "en" else body.get("pergunta_pt"),
        "opcoes": opcoes,
        "fecha_em": body.get("fecha_em"),
        "votou": bool(body.get("votou")),
    }
    if "resultado" in body:
        out["resultado"] = body.get("resultado")
        out["total"] = body.get("total")
    return out


def voto(request: Request, enquete_id: int, opcao_id: str) -> JSONResponse:
    _vid, created, digest = visitor(request)
    status, body = hub_request(
        "POST",
        f"/api/cms/enquetes/{int(enquete_id)}/votos",
        {"opcao_id": opcao_id, "visitante": digest},
        client_ip(request),
    )
    if status != 200 or not isinstance(body, dict):
        code = status if status in {400, 404, 409, 410, 429} else 502
        raise HTTPException(status_code=code)
    response = JSONResponse(
        {"resultado": body.get("resultado") or [], "total": int(body.get("total") or 0)}
    )
    return attach(response, _vid, created)


def ics_text(value: str) -> str:
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("\r\n", "\n")
        .replace("\n", "\\n")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


def calendar(post: dict, lang: str) -> str:
    if post.get("right_now_tipo") != "evento":
        raise HTTPException(status_code=404)
    raw = str(post.get("data_evento") or "")[:10]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        raise HTTPException(status_code=404)
    day = raw.replace("-", "")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = post.get("slug") or "evento"
    link = cms.public_base() + f"/{lang}/right-now/{slug}"
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//LePain//Right Now//PT",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{ics_text(slug)}-{lang}@lepain.lojadepaes.com.br",
        f"DTSTAMP:{stamp}",
        f"DTSTART;VALUE=DATE:{day}",
        f"SUMMARY:{ics_text(post.get('titulo') or '')}",
        f"URL:{ics_text(link)}",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(lines) + "\r\n"
