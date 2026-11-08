"""Leitura do CMS. fixtures (padrão) ou GET público do Hub."""

from __future__ import annotations

import json
import os
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures" / "posts.json"
TTL_SEC = 300
HUB_URL = "https://api.actionhub.com.br/api/cms/posts"

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


def fetch_hub_payload() -> list[dict]:
    import urllib.request

    url = os.environ.get("LEPAIN_HUB_URL", HUB_URL).strip()
    sep = "&" if "?" in url else "?"
    full = f"{url}{sep}sistema_destino=lepain&limit=100"
    req = urllib.request.Request(full, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=3.5) as res:
        body = json.loads(res.read().decode("utf-8"))
    posts = body.get("posts") if isinstance(body, dict) else None
    return posts if isinstance(posts, list) else []


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
