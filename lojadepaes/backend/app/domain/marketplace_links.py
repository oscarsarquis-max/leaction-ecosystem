from __future__ import annotations

from urllib.parse import parse_qs, urlparse

ML_HOSTS = frozenset(
    {
        "www.mercadolivre.com.br",
        "mercadolivre.com.br",
        "produto.mercadolivre.com.br",
        "click.mercadolivre.com.br",
        "www.mercadolibre.com",
        "mercadolibre.com",
    }
)
ML_SEARCH_HOSTS = frozenset({"lista.mercadolivre.com.br"})

AMAZON_HOSTS = frozenset(
    {
        "www.amazon.com.br",
        "amazon.com.br",
        "www.amazon.com",
        "amazon.com",
        "amzn.to",
    }
)

ML_IMAGE_HOST_SUFFIXES = (".mlstatic.com", ".mercadolivre.com.br", ".mercadolibre.com")
AMAZON_IMAGE_HOST_SUFFIXES = (".ssl-images-amazon.com", ".media-amazon.com", ".amazon.com")

VENDOR_MERCADOLIVRE = "mercadolivre"
VENDOR_AMAZON = "amazon"


def sanitize_plain_text(value: object, *, limit: int = 800) -> str:
    text = " ".join(str(value or "").replace("\x00", " ").split())
    if "<" in text:
        text = text.replace("<", " ").replace(">", " ")
        text = " ".join(text.split())
    return text[:limit]


def vendor_from_source(value: object, link: str | None = None) -> str:
    raw = sanitize_plain_text(value, limit=40).casefold()
    if raw in {VENDOR_AMAZON, "paapi", "associate"}:
        return VENDOR_AMAZON
    if raw in {VENDOR_MERCADOLIVRE, "ml", "mercadolibre"}:
        return VENDOR_MERCADOLIVRE
    host = ""
    parsed = _https_url(str(link or ""))
    if parsed and parsed.hostname:
        host = parsed.hostname.lower()
    if host in AMAZON_HOSTS or host.endswith(".amazon.com.br"):
        return VENDOR_AMAZON
    return VENDOR_MERCADOLIVRE


def marketplace_label(vendor: str) -> str:
    return "Amazon" if vendor == VENDOR_AMAZON else "Mercado Livre"


def marketplace_price_prep(vendor: str) -> str:
    return "na" if vendor == VENDOR_AMAZON else "no"


def outbound_cta(vendor: str) -> str:
    return f"Ver {marketplace_price_prep(vendor)} {marketplace_label(vendor)}"


def separate_purchase_notice(vendor: str) -> str:
    name = marketplace_label(vendor)
    prep = "pela" if vendor == VENDOR_AMAZON else "pelo"
    return f"Compra e entrega realizadas separadamente {prep} {name}. Confira preço e disponibilidade no site de compra."


def is_allowed_outbound_url(value: str) -> bool:
    return keep_official_outbound_url(value) is not None


def is_allowed_ml_url(value: str) -> bool:
    return keep_official_ml_url(value) is not None


def keep_official_ml_url(value: object) -> str | None:
    return keep_official_outbound_url(value, vendors={VENDOR_MERCADOLIVRE})


def keep_official_outbound_url(value: object, *, vendors: set[str] | None = None) -> str | None:
    raw = str(value or "").strip()
    if not raw or raw.lower().startswith(("javascript:", "data:", "vbscript:")):
        return None
    parsed = _https_url(raw)
    if parsed is None or not parsed.hostname:
        return None
    host = parsed.hostname.lower()
    if parsed.username or parsed.password:
        return None
    allowed: set[str] = set()
    wanted = vendors or {VENDOR_MERCADOLIVRE, VENDOR_AMAZON}
    if VENDOR_MERCADOLIVRE in wanted:
        allowed |= ML_HOSTS
    if VENDOR_AMAZON in wanted:
        allowed |= AMAZON_HOSTS
    if host in ML_SEARCH_HOSTS:
        return None
    if host not in allowed:
        return None
    query = f"?{parsed.query}" if parsed.query else ""
    path = parsed.path or "/"
    return f"https://{host}{path}{query}"


def keep_image_url(value: object) -> str | None:
    raw = str(value or "").strip().replace("http://", "https://")
    if raw.startswith("/marketplace-api/image"):
        nested = parse_qs(urlparse("https://actionhub.com.br" + raw).query).get("url") or []
        raw = str(nested[0] if nested else "").strip().replace("http://", "https://")
    parsed = _https_url(raw)
    if parsed is None or not parsed.hostname:
        return None
    host = parsed.hostname.lower()
    if (
        host.endswith(ML_IMAGE_HOST_SUFFIXES)
        or host.endswith(AMAZON_IMAGE_HOST_SUFFIXES)
        or host in ML_HOSTS
        or host in AMAZON_HOSTS
    ):
        return raw.split("#", 1)[0][:500]
    return None


def _https_url(value: str):
    try:
        parsed = urlparse(value)
    except ValueError:
        return None
    if parsed.scheme.lower() != "https":
        return None
    if parsed.hostname is None:
        return None
    return parsed
