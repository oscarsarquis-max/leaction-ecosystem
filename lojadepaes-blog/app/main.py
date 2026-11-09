"""LePain · Bread & Sense. Páginas em HTML, lidas no servidor."""

from __future__ import annotations

import os
import re
import urllib.request
from datetime import date
from pathlib import Path
from urllib.parse import urlparse
from xml.sax.saxutils import escape

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from markupsafe import Markup

from app import cms
from app.copy import COPY, MONTHS, RADII, SENSE_ORDER, SENSES
from app.sanitize import clean as sanitize_html

ROOT = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(ROOT / "templates"))
KIND_VALUES = {"promocao", "evento", "noticia"}
CAPA_HOST = "paneldx-cms-assets-2026.s3.us-east-2.amazonaws.com"
CAPA_MAX_BYTES = 8_000_000

app = FastAPI(title="LePain")
app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")


def prefer_lang(header: str | None) -> str:
    if not header:
        return "pt"
    ranked: list[tuple[float, int, str]] = []
    for index, bit in enumerate(header.split(",")):
        piece = bit.strip()
        if not piece:
            continue
        tag, _, params = piece.partition(";")
        quality = 1.0
        for param in params.split(";"):
            param = param.strip()
            if param.startswith("q="):
                try:
                    quality = float(param[2:])
                except ValueError:
                    quality = 0.0
        ranked.append((-quality, index, tag.strip().lower()))
    ranked.sort()
    for _, _, tag in ranked:
        if tag.startswith("en"):
            return "en"
        if tag.startswith("pt"):
            return "pt"
    return "pt"


def format_date(value: str, lang: str) -> str:
    if not value:
        return ""
    try:
        day = date.fromisoformat(str(value)[:10])
    except ValueError:
        return ""
    if lang == "en":
        return f"{MONTHS['en'][day.month]} {day.day}, {day.year}"
    return f"{day.day} de {MONTHS['pt'][day.month]} de {day.year}"


def reading_minutes(html: str) -> int:
    text = re.sub(r"<[^>]+>", " ", html or "")
    words = [word for word in text.split() if word]
    if not words:
        return 1
    return max(1, round(len(words) / 180))


def media_label(post: dict, lang: str) -> str:
    html = post.get("conteudo_html") or ""
    if "<iframe" in html or "<video" in html:
        return "vídeo" if lang == "pt" else "video"
    if "<audio" in html:
        return "áudio" if lang == "pt" else "audio"
    return "texto" if lang == "pt" else "text"


def when_label(post: dict, lang: str) -> str:
    text = COPY[lang]
    kind = post.get("right_now_tipo")
    if kind == "promocao" and post.get("valido_ate"):
        return f"{text['until']} {format_date(post['valido_ate'], lang)}"
    if kind == "evento":
        return format_date(post.get("data_evento") or "", lang)
    return format_date(post.get("publicado_em") or "", lang)


def absolute(path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if not path.startswith("/"):
        path = "/" + path
    return cms.public_base() + path


def cover_url(post: dict) -> str:
    cover = (post.get("imagem_capa") or "").strip()
    if cover:
        return absolute(cover)
    return absolute("/static/img/lepain-logo.png")


def query_path(path: str, sentido: str = "", tipo: str = "") -> str:
    parts = []
    if sentido:
        parts.append(f"sentido={sentido}")
    if tipo:
        parts.append(f"tipo={tipo}")
    if not parts:
        return path
    return path + "?" + "&".join(parts)


def alternates(pt_path: str, en_path: str) -> list[dict]:
    pt_url = absolute(pt_path)
    en_url = absolute(en_path)
    return [
        {"code": "pt", "href": pt_url},
        {"code": "en", "href": en_url},
        {"code": "x-default", "href": pt_url},
    ]


def require_lang(lang: str) -> str:
    if lang not in {"pt", "en"}:
        raise HTTPException(status_code=404)
    return lang


def group_key(post: dict) -> str:
    grupo = post.get("grupo_id")
    if grupo is not None and str(grupo).strip():
        return f"g:{grupo}"
    return f"s:{post.get('slug') or ''}"


def issue_index(post: dict) -> int | None:
    if post.get("secao") != "insights":
        return None
    rows = [
        item
        for item in cms.all_posts()
        if item.get("secao") == "insights" and item.get("idioma") == "pt" and cms.visible(item)
    ]
    rows.sort(key=lambda item: (item.get("publicado_em") or "9999-99-99", item.get("slug") or ""))
    order = {group_key(item): index for index, item in enumerate(rows, start=1)}
    origin = post
    if post.get("idioma") != "pt":
        origin = cms.sibling(post, "pt") or post
    return order.get(group_key(origin))


def issue_label(post: dict) -> str:
    number = issue_index(post)
    if number is None:
        return "INSIGHTS"
    return f"INSIGHTS · Nº {number:02d}"


def card_number(post: dict) -> str:
    number = issue_index(post)
    if number is None:
        return "Insights"
    return f"Insights · Nº {number:02d}"


def essay_html(post: dict) -> str:
    body = sanitize_html(post.get("conteudo_html") or "")
    cover = (post.get("imagem_capa") or "").strip()
    if not cover:
        return body
    src = absolute(cover)
    if src in body or cover in body:
        return body
    safe = escape(src, {'"': "&quot;"})
    return f'<figure class="wide"><img src="{safe}" alt=""></figure>{body}'


def instagram_handle() -> str:
    raw = os.environ.get("LEPAIN_INSTAGRAM", "").strip().lstrip("@")
    if re.fullmatch(r"[A-Za-z0-9._]{1,30}", raw):
        return raw
    return ""


def present(post: dict, lang: str, index: int = 0) -> dict:
    sense_ids = [item for item in post.get("sentidos") or [] if item in SENSES]
    primary = sense_ids[0] if sense_ids else "sabor"
    cover = (post.get("imagem_capa") or "").strip()
    return {
        **post,
        "html": Markup(essay_html(post)),
        "cover": absolute(cover) if cover else "",
        "issue_label": issue_label(post),
        "card_number": card_number(post),
        "senses": sense_ids,
        "primary": primary,
        "color": SENSES[primary]["color"],
        "ink": SENSES[primary]["ink"],
        "radius": RADII[index % len(RADII)],
        "when": when_label(post, lang),
        "minutes": reading_minutes(post.get("conteudo_html") or ""),
        "media": media_label(post, lang),
        "date_label": format_date(post.get("publicado_em") or "", lang),
        "path": cms.story_path(post),
        "card_path": f"/{post['idioma']}/card/{post['slug']}",
    }


def base_context(request: Request, lang: str, **extra) -> dict:
    context = {
        "request": request,
        "lang": lang,
        "html_lang": "pt-BR" if lang == "pt" else "en",
        "t": COPY[lang],
        "sense_order": SENSE_ORDER,
        "senses": SENSES,
        "forest": False,
        "noindex": False,
        "fallback": False,
        "title": "LePain · Bread & Sense",
        "description": COPY[lang]["instagram"],
        "canonical": absolute(request.url.path),
        "hreflang": alternates("/pt", "/en"),
        "og_locale": "pt_BR" if lang == "pt" else "en_US",
        "og_image": absolute("/static/img/lepain-logo.png"),
        "og_type": "website",
        "pt_href": "/pt",
        "en_href": "/en",
        "section": "home",
        "url_lang": lang,
        "instagram": instagram_handle(),
    }
    context.update(extra)
    return context


def resolve_story(lang: str, slug: str, secao: str) -> tuple[dict | None, bool]:
    post = cms.find(lang, slug, secao)
    if post:
        return post, False
    if lang == "en" and secao == "insights":
        original = cms.find("pt", slug, "insights")
        if original and cms.sibling(original, "en") is None:
            return original, True
    return None, False


def story_links(post: dict, lang: str, fallback: bool, secao: str) -> tuple[str, str]:
    pt = cms.sibling(post, "pt") if post.get("idioma") != "pt" else post
    en = None if fallback else cms.sibling(post, "en")
    if post.get("idioma") == "en":
        en = post
    if pt is None and post.get("idioma") == "pt":
        pt = post
    section = "insights" if secao == "insights" else "right-now"
    pt_path = cms.story_path(pt) if pt else f"/pt/{section}/{post['slug']}"
    if en:
        en_path = cms.story_path(en)
    elif pt:
        en_path = f"/en/{section}/{pt['slug']}"
    else:
        en_path = f"/en/{section}/{post['slug']}"
    return pt_path, en_path


@app.get("/api/v1/health")
def health() -> dict:
    return {"ok": True, "service": "lepain"}


@app.get("/robots.txt")
def robots() -> PlainTextResponse:
    body = f"User-agent: *\nAllow: /\n\nSitemap: {cms.public_base()}/sitemap.xml\n"
    return PlainTextResponse(body)


@app.get("/sitemap.xml")
def sitemap() -> Response:
    homes = ("/pt", "/en", "/pt/insights", "/en/insights", "/pt/right-now", "/en/right-now")
    chunks = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">',
    ]
    for path in homes:
        other = "/en" + path[3:] if path.startswith("/pt") else "/pt" + path[3:]
        chunks.append(_sitemap_url(path, other, ""))
    seen: set[str] = set()
    for post in cms.all_posts():
        if not cms.visible(post) or post.get("idioma") != "pt":
            continue
        pt_path, en_path = story_links(post, "pt", cms.sibling(post, "en") is None, post["secao"])
        if pt_path in seen:
            continue
        seen.add(pt_path)
        chunks.append(_sitemap_url(pt_path, en_path, str(post.get("atualizado_em") or "")[:10]))
        if en_path not in seen:
            seen.add(en_path)
            sibling_post = cms.sibling(post, "en")
            lastmod = str((sibling_post or post).get("atualizado_em") or "")[:10]
            chunks.append(_sitemap_url(en_path, pt_path, lastmod))
    chunks.append("</urlset>")
    return Response("".join(chunks), media_type="application/xml")


def _sitemap_url(path: str, other: str, lastmod: str) -> str:
    loc = escape(absolute(path))
    pt = escape(absolute(path if path.startswith("/pt") else other))
    en = escape(absolute(path if path.startswith("/en") else other))
    lines = ["<url>", f"<loc>{loc}</loc>"]
    if lastmod:
        lines.append(f"<lastmod>{escape(lastmod)}</lastmod>")
    lines.append(f'<xhtml:link rel="alternate" hreflang="pt" href="{pt}"/>')
    lines.append(f'<xhtml:link rel="alternate" hreflang="en" href="{en}"/>')
    lines.append(f'<xhtml:link rel="alternate" hreflang="x-default" href="{pt}"/>')
    lines.append("</url>")
    return "".join(lines)


@app.get("/")
def root(request: Request) -> RedirectResponse:
    lang = prefer_lang(request.headers.get("accept-language"))
    return RedirectResponse(f"/{lang}", status_code=302)


@app.get("/{lang}", response_class=HTMLResponse)
def home(request: Request, lang: str) -> HTMLResponse:
    require_lang(lang)
    insights = [present(post, lang, index) for index, post in enumerate(cms.by_lang(lang, "insights"))]
    featured = insights[0] if insights else None
    rest = insights[1:] if insights else []
    now = [present(post, lang, index) for index, post in enumerate(cms.by_lang(lang, "right_now")[:3])]
    return TEMPLATES.TemplateResponse(
        request,
        "home.html",
        base_context(
            request,
            lang,
            section="insights",
            featured=featured,
            cards=rest,
            now=now,
            canonical=absolute(f"/{lang}"),
            hreflang=alternates("/pt", "/en"),
            pt_href="/pt",
            en_href="/en",
            description=featured["resumo"] if featured else COPY[lang]["instagram"],
        ),
    )


@app.get("/{lang}/insights", response_class=HTMLResponse)
def insights(request: Request, lang: str, sentido: str = "") -> HTMLResponse:
    require_lang(lang)
    chosen = sentido if sentido in SENSES else ""
    rows = [
        present(post, lang, index)
        for index, post in enumerate(cms.by_lang(lang, "insights", sentido=chosen or None))
    ]
    path = query_path(f"/{lang}/insights", sentido=chosen)
    other = "en" if lang == "pt" else "pt"
    return TEMPLATES.TemplateResponse(
        request,
        "insights.html",
        base_context(
            request,
            lang,
            section="insights",
            cards=rows,
            chosen=chosen,
            canonical=absolute(path),
            hreflang=alternates(
                query_path("/pt/insights", sentido=chosen),
                query_path("/en/insights", sentido=chosen),
            ),
            pt_href=query_path("/pt/insights", sentido=chosen),
            en_href=query_path("/en/insights", sentido=chosen),
            title=f"{COPY[lang]['insights']} — LePain",
            other_lang=other,
        ),
    )


@app.get("/{lang}/insights/{slug}", response_class=HTMLResponse)
def insight(request: Request, lang: str, slug: str) -> HTMLResponse:
    require_lang(lang)
    post, fallback = resolve_story(lang, slug, "insights")
    if post is None:
        raise HTTPException(status_code=404)
    content_lang = "pt" if fallback else lang
    view = present(post, content_lang)
    pt_path, en_path = story_links(post, lang, fallback, "insights")
    others = [
        present(item, content_lang, index)
        for index, item in enumerate(cms.by_lang(content_lang, "insights"))
        if item["slug"] != post["slug"]
    ][:2]
    page_lang = "pt" if fallback else lang
    return TEMPLATES.TemplateResponse(
        request,
        "post.html",
        base_context(
            request,
            page_lang,
            section="insights",
            post=view,
            others=others,
            fallback=fallback,
            url_lang=lang,
            canonical=absolute(f"/{lang}/insights/{slug}"),
            hreflang=alternates(pt_path, en_path),
            pt_href=pt_path,
            en_href=en_path,
            title=f"{view['titulo']} — LePain",
            description=view["resumo"],
            og_image=cover_url(post),
            og_type="article",
            html_lang="pt-BR" if page_lang == "pt" else "en",
            og_locale="pt_BR" if page_lang == "pt" else "en_US",
        ),
    )


@app.get("/{lang}/right-now", response_class=HTMLResponse)
def right_now(request: Request, lang: str, tipo: str = "") -> HTMLResponse:
    require_lang(lang)
    chosen = tipo if tipo in KIND_VALUES else ""
    rows = [
        present(post, lang, index)
        for index, post in enumerate(cms.by_lang(lang, "right_now", tipo=chosen or None))
    ]
    path = query_path(f"/{lang}/right-now", tipo=chosen)
    return TEMPLATES.TemplateResponse(
        request,
        "right_now.html",
        base_context(
            request,
            lang,
            forest=True,
            section="right_now",
            items=rows,
            chosen=chosen,
            canonical=absolute(path),
            hreflang=alternates(
                query_path("/pt/right-now", tipo=chosen),
                query_path("/en/right-now", tipo=chosen),
            ),
            pt_href=query_path("/pt/right-now", tipo=chosen),
            en_href=query_path("/en/right-now", tipo=chosen),
            title=f"Right Now — LePain",
            description=COPY[lang]["right_lead"],
            og_image=absolute("/static/img/lepain-logo-creme.png"),
        ),
    )


@app.get("/{lang}/right-now/{slug}", response_class=HTMLResponse)
def right_now_item(request: Request, lang: str, slug: str) -> HTMLResponse:
    require_lang(lang)
    post = cms.find(lang, slug, "right_now")
    if post is None and lang == "en":
        original = cms.find("pt", slug, "right_now")
        if original and cms.sibling(original, "en") is None:
            post = original
            fallback = True
        else:
            fallback = False
    else:
        fallback = False
    if post is None:
        raise HTTPException(status_code=404)
    content_lang = "pt" if fallback else lang
    view = present(post, content_lang)
    pt_path, en_path = story_links(post, lang, fallback, "right_now")
    page_lang = "pt" if fallback else lang
    return TEMPLATES.TemplateResponse(
        request,
        "note.html",
        base_context(
            request,
            page_lang,
            forest=True,
            section="right_now",
            post=view,
            fallback=fallback,
            url_lang=lang,
            canonical=absolute(f"/{lang}/right-now/{slug}"),
            hreflang=alternates(pt_path, en_path),
            pt_href=pt_path,
            en_href=en_path,
            title=f"{view['titulo']} — LePain",
            description=view["resumo"],
            og_image=cover_url(post),
            og_type="article",
        ),
    )


def card_modelo(raw: str | None) -> str:
    return "foto" if (raw or "").strip().lower() == "foto" else "tipografico"


def capa_url_ok(url: str) -> bool:
    parsed = urlparse((url or "").strip())
    return (
        parsed.scheme == "https"
        and (parsed.hostname or "").lower() == CAPA_HOST
        and not parsed.username
        and not parsed.password
    )


class _CapaRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not capa_url_ok(newurl):
            return None
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def post_by_slug(slug: str) -> dict | None:
    for lang in ("pt", "en"):
        found = cms.find(lang, slug)
        if found:
            return found
    return None


@app.get("/media/capa/{slug}")
def media_capa(slug: str) -> Response:
    post = post_by_slug(slug)
    if post is None:
        raise HTTPException(status_code=404)
    url = (post.get("imagem_capa") or "").strip()
    if not url:
        raise HTTPException(status_code=404)
    if not capa_url_ok(url):
        raise HTTPException(status_code=400, detail="capa fora do bucket do CMS")
    opener = urllib.request.build_opener(_CapaRedirect)
    try:
        with opener.open(url, timeout=8) as res:
            if not capa_url_ok(res.geturl()):
                raise HTTPException(status_code=400, detail="capa fora do bucket do CMS")
            data = res.read(CAPA_MAX_BYTES + 1)
            ctype = (res.headers.get("Content-Type") or "image/jpeg").split(";", 1)[0].strip()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail="capa indisponível") from exc
    if len(data) > CAPA_MAX_BYTES or not ctype.startswith("image/"):
        raise HTTPException(status_code=502, detail="capa indisponível")
    return Response(content=data, media_type=ctype, headers={"Cache-Control": "public, max-age=300"})


@app.get("/{lang}/card/{slug}")
def card(request: Request, lang: str, slug: str, modelo: str = "") -> Response:
    require_lang(lang)
    post, fallback = resolve_story(lang, slug, "insights")
    if post is None:
        post = cms.find(lang, slug, "right_now")
        fallback = False
    if post is None:
        raise HTTPException(status_code=404)
    chosen = card_modelo(modelo)
    if chosen == "foto" and not (post.get("imagem_capa") or "").strip():
        return RedirectResponse(f"/{lang}/card/{slug}?modelo=tipografico", status_code=302)
    content_lang = "pt" if fallback else lang
    view = present(post, content_lang)
    pt_path, en_path = story_links(post, lang, fallback, post["secao"])
    text = COPY[content_lang]
    pt_slug = pt_path.rsplit("/", 1)[-1]
    en_slug = en_path.rsplit("/", 1)[-1]
    return TEMPLATES.TemplateResponse(
        request,
        "card.html",
        base_context(
            request,
            content_lang,
            noindex=True,
            post=view,
            fallback=fallback,
            url_lang=lang,
            canonical=absolute(f"/{lang}/card/{slug}?modelo={chosen}"),
            hreflang=alternates(
                f"/pt/card/{pt_slug}?modelo={chosen}",
                f"/en/card/{en_slug}?modelo={chosen}",
            ),
            pt_href=f"/pt/card/{pt_slug}?modelo={chosen}",
            en_href=f"/en/card/{en_slug}?modelo={chosen}",
            title=f"{view['titulo']} — LePain",
            description=view["resumo"],
            og_image=cover_url(post),
            card_kicker=text["card_kicker"],
            card_cta=text["card_cta"],
            download=COPY[lang]["download"],
            modelo=chosen,
        ),
    )


@app.exception_handler(404)
def not_found(request: Request, _exc: HTTPException) -> HTMLResponse:
    parts = [part for part in request.url.path.split("/") if part]
    lang = parts[0] if parts and parts[0] in {"pt", "en"} else "pt"
    return TEMPLATES.TemplateResponse(
        request,
        "404.html",
        base_context(request, lang, title="LePain"),
        status_code=404,
    )
