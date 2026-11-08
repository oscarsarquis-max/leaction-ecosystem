"""Leitura do CMS. fixtures (padrão) ou GET público do Hub."""

from __future__ import annotations

import json
import os
import time
from datetime import date
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures" / "posts.json"
TTL_SEC = 300
HUB_ORIGIN = "https://api.actionhub.com.br"

_cache: dict = {"posts": None, "at": 0.0}


def reset_cache() -> None:
    _cache["posts"] = None
    _cache["at"] = 0.0


def source() -> str:
    value = os.environ.get("LEPAIN_CMS_SOURCE", "fixtures").strip().lower()
    return value or "fixtures"


def today() -> date:
    raw = os.environ.get("LEPAIN_TODAY", "").strip()
    if raw:
        return date.fromisoformat(raw)
    return date.today()


def public_base() -> str:
    return os.environ.get("LEPAIN_PUBLIC_URL", "https://lepain.lojadepaes.com.br").rstrip("/")


def _as_date(value) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def normalize(row: dict) -> dict:
    sentidos = row.get("sentidos") or []
    if isinstance(sentidos, str):
        sentidos = [sentidos]
    return {
        "slug": str(row.get("slug") or "").strip(),
        "titulo": str(row.get("titulo") or "").strip(),
        "resumo": row.get("resumo") or "",
        "resumo_instagram": row.get("resumo_instagram") or row.get("resumo") or "",
        "conteudo_html": row.get("conteudo_html") or "",
        "imagem_capa": row.get("imagem_capa") or "",
        "secao": row.get("secao") or "insights",
        "idioma": row.get("idioma") or "",
        "grupo_id": row.get("grupo_id"),
        "sentidos": list(sentidos),
        "right_now_tipo": row.get("right_now_tipo") or "",
        "data_evento": row.get("data_evento") or "",
        "valido_ate": row.get("valido_ate") or "",
        "publicado_em": row.get("publicado_em") or "",
        "atualizado_em": row.get("atualizado_em") or row.get("publicado_em") or "",
        "sistema_destino": (row.get("sistema_destino") or "lepain"),
    }


def load_fixtures() -> list[dict]:
    rows = json.loads(FIXTURES.read_text(encoding="utf-8"))
    return [normalize(row) for row in rows]


def posts_base() -> str:
    raw = os.environ.get("LEPAIN_HUB_URL", HUB_ORIGIN).strip().rstrip("/")
    if raw.endswith("/api/cms/posts"):
        return raw
    return raw + "/api/cms/posts"


def list_url(secao: str = "", idioma: str = "", offset: int = 0, limit: int = 100) -> str:
    parts = [
        "sistema_destino=lepain",
        f"limit={int(limit)}",
        f"offset={int(offset)}",
    ]
    if secao:
        parts.append("secao=" + quote(secao))
    if idioma:
        parts.append("idioma=" + quote(idioma))
    return posts_base() + "?" + "&".join(parts)


def post_url(slug: str) -> str:
    return posts_base() + "/" + quote(str(slug).strip(), safe="")


def http_get_json(url: str) -> dict:
    import urllib.request

    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=3.5) as res:
        body = json.loads(res.read().decode("utf-8"))
    if not isinstance(body, dict):
        raise ValueError("resposta do Hub sem objeto")
    return body


def fetch_hub_payload(secao: str = "", idioma: str = "") -> list[dict]:
    offset = 0
    limit = 100
    rows: list[dict] = []
    while True:
        body = http_get_json(list_url(secao=secao, idioma=idioma, offset=offset, limit=limit))
        page = body.get("posts")
        page = page if isinstance(page, list) else []
        rows.extend(page)
        if len(page) < limit:
            return rows
        offset += limit


def fetch_hub_post(slug: str) -> dict | None:
    body = http_get_json(post_url(slug))
    post = body.get("post")
    if not isinstance(post, dict):
        return None
    rows = from_hub([post])
    return rows[0] if rows else None


def from_hub(rows: list[dict]) -> list[dict]:
    kept = []
    for row in rows:
        destino = str(row.get("sistema_destino") or "").strip().lower()
        if destino == "todos":
            continue
        status = str(row.get("status") or "publicado").strip().lower()
        if status != "publicado":
            continue
        kept.append(normalize(row))
    return kept


def all_posts() -> list[dict]:
    if source() != "hub":
        return load_fixtures()
    now = time.monotonic()
    cached = _cache["posts"]
    if cached is not None and (now - _cache["at"]) < TTL_SEC:
        return list(cached)
    try:
        posts = from_hub(fetch_hub_payload())
    except Exception:
        if cached is not None:
            return list(cached)
        return []
    _cache["posts"] = posts
    _cache["at"] = now
    return list(posts)


def expired(post: dict, on: date | None = None) -> bool:
    if post.get("secao") != "right_now":
        return False
    end = _as_date(post.get("valido_ate"))
    if end is None:
        return False
    return end < (on or today())


def visible(post: dict) -> bool:
    return not expired(post)


def by_lang(
    lang: str,
    secao: str | None = None,
    sentido: str | None = None,
    tipo: str | None = None,
) -> list[dict]:
    rows = []
    for post in all_posts():
        if post.get("idioma") != lang or not visible(post):
            continue
        if secao and post.get("secao") != secao:
            continue
        if sentido and sentido not in (post.get("sentidos") or []):
            continue
        if tipo and post.get("right_now_tipo") != tipo:
            continue
        rows.append(post)
    rows.sort(key=lambda item: item.get("publicado_em") or "", reverse=True)
    return rows


def find(lang: str, slug: str, secao: str | None = None) -> dict | None:
    if source() == "hub":
        try:
            fetched = fetch_hub_post(slug)
        except Exception:
            fetched = None
        if (
            fetched
            and fetched.get("idioma") == lang
            and (not secao or fetched.get("secao") == secao)
            and visible(fetched)
        ):
            return fetched
    for post in all_posts():
        if post.get("idioma") != lang or post.get("slug") != slug:
            continue
        if secao and post.get("secao") != secao:
            continue
        if not visible(post):
            return None
        return post
    return None


def sibling(post: dict, lang: str) -> dict | None:
    grupo = post.get("grupo_id")
    if grupo is None:
        return None
    for other in all_posts():
        if other.get("grupo_id") == grupo and other.get("idioma") == lang and visible(other):
            return other
    return None


def story_path(post: dict) -> str:
    section = "insights" if post.get("secao") == "insights" else "right-now"
    return f"/{post['idioma']}/{section}/{post['slug']}"
