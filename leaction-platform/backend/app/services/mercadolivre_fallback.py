"""Catálogo curado de fallback — vitrine operacional quando a API ML exige OAuth."""

from __future__ import annotations

import unicodedata
from typing import Any

# Links apontam para buscas curadas no Mercado Livre (navegação pública no browser).
_LIST_BASE = "https://lista.mercadolivre.com.br"

# Paths relativos — o frontend resolve com a origin do browser (evita localhost fixo).
_PLACEHOLDER = "/marketplace/placeholders"

_SHELVES: list[dict[str, Any]] = [
    {
        "keywords": ("livro", "lideranca", "liderança", "executiv", "gestao", "gestão"),
        "offers": [
            {
                "id": "fallback-exec-1",
                "title": "Liderança em Tempos de Transformação Digital",
                "price": 79.9,
                "currency": "BRL",
                "price_label": "R$ 79,90",
                "image": f"{_PLACEHOLDER}/livro.svg",
                "link": f"{_LIST_BASE}/livros-lideranca-transformacao-digital",
            },
            {
                "id": "fallback-exec-2",
                "title": "Gestão Estratégica e Inovação Corporativa",
                "price": 92.5,
                "currency": "BRL",
                "price_label": "R$ 92,50",
                "image": f"{_PLACEHOLDER}/gestao.svg",
                "link": f"{_LIST_BASE}/livros-gestao-estrategica",
            },
            {
                "id": "fallback-exec-3",
                "title": "Transformação Digital para Executivos",
                "price": 68.0,
                "currency": "BRL",
                "price_label": "R$ 68,00",
                "image": f"{_PLACEHOLDER}/digital.svg",
                "link": f"{_LIST_BASE}/livros-transformacao-digital",
            },
            {
                "id": "fallback-exec-4",
                "title": "Cultura Organizacional e Change Management",
                "price": 74.9,
                "currency": "BRL",
                "price_label": "R$ 74,90",
                "image": f"{_PLACEHOLDER}/gestao.svg",
                "link": f"{_LIST_BASE}/livros-change-management",
            },
        ],
    },
    {
        "keywords": ("rede", "automacao", "automação", "infra", "switch", "conectividade", "equipamento"),
        "offers": [
            {
                "id": "fallback-infra-1",
                "title": "Switch Gerenciável Gigabit — Infraestrutura de Rede",
                "price": 489.9,
                "currency": "BRL",
                "price_label": "R$ 489,90",
                "image": f"{_PLACEHOLDER}/rede.svg",
                "link": f"{_LIST_BASE}/switch-gerenciavel-gigabit",
            },
            {
                "id": "fallback-infra-2",
                "title": "Roteador Wi-Fi 6 Empresarial",
                "price": 629.0,
                "currency": "BRL",
                "price_label": "R$ 629,00",
                "image": f"{_PLACEHOLDER}/rede.svg",
                "link": f"{_LIST_BASE}/roteador-wifi-6-empresarial",
            },
            {
                "id": "fallback-infra-3",
                "title": "Access Point Corporativo Dual Band",
                "price": 399.9,
                "currency": "BRL",
                "price_label": "R$ 399,90",
                "image": f"{_PLACEHOLDER}/rede.svg",
                "link": f"{_LIST_BASE}/access-point-corporativo",
            },
            {
                "id": "fallback-infra-4",
                "title": "Automação Industrial — CLP e Sensores",
                "price": 1150.0,
                "currency": "BRL",
                "price_label": "R$ 1.150,00",
                "image": f"{_PLACEHOLDER}/equipamento.svg",
                "link": f"{_LIST_BASE}/automacao-industrial-clp",
            },
        ],
    },
    {
        "keywords": ("software", "licenca", "licença", "microsoft", "antivirus", "office", "365"),
        "offers": [
            {
                "id": "fallback-sw-1",
                "title": "Microsoft 365 Business — Licença Anual",
                "price": 899.0,
                "currency": "BRL",
                "price_label": "R$ 899,00",
                "image": f"{_PLACEHOLDER}/digital.svg",
                "link": f"{_LIST_BASE}/microsoft-365-business",
            },
            {
                "id": "fallback-sw-2",
                "title": "Antivírus Corporativo Endpoint Protection",
                "price": 249.9,
                "currency": "BRL",
                "price_label": "R$ 249,90",
                "image": f"{_PLACEHOLDER}/digital.svg",
                "link": f"{_LIST_BASE}/antivirus-corporativo-endpoint",
            },
            {
                "id": "fallback-sw-3",
                "title": "Windows Server — Licença Standard",
                "price": 1899.0,
                "currency": "BRL",
                "price_label": "R$ 1.899,00",
                "image": f"{_PLACEHOLDER}/digital.svg",
                "link": f"{_LIST_BASE}/windows-server-licenca",
            },
            {
                "id": "fallback-sw-4",
                "title": "Ferramentas de Gestão e Produtividade Digital",
                "price": 159.0,
                "currency": "BRL",
                "price_label": "R$ 159,00",
                "image": f"{_PLACEHOLDER}/digital.svg",
                "link": f"{_LIST_BASE}/software-gestao-corporativa",
            },
        ],
    },
    {
        "keywords": ("digital", "maturidade", "educacao", "educação", "consultoria", "tecnologia"),
        "offers": [
            {
                "id": "fallback-gen-1",
                "title": "Curso Online — Maturidade Digital Organizacional",
                "price": 197.0,
                "currency": "BRL",
                "price_label": "R$ 197,00",
                "image": f"{_PLACEHOLDER}/digital.svg",
                "link": f"{_LIST_BASE}/curso-maturidade-digital",
            },
            {
                "id": "fallback-gen-2",
                "title": "Notebook Profissional — Produtividade Digital",
                "price": 3299.0,
                "currency": "BRL",
                "price_label": "R$ 3.299,00",
                "image": f"{_PLACEHOLDER}/equipamento.svg",
                "link": f"{_LIST_BASE}/notebook-profissional",
            },
            {
                "id": "fallback-gen-3",
                "title": "Tablet para Reuniões e Apresentações",
                "price": 1899.9,
                "currency": "BRL",
                "price_label": "R$ 1.899,90",
                "image": f"{_PLACEHOLDER}/equipamento.svg",
                "link": f"{_LIST_BASE}/tablet-corporativo",
            },
            {
                "id": "fallback-gen-4",
                "title": "Webcam 4K — Colaboração Híbrida",
                "price": 459.9,
                "currency": "BRL",
                "price_label": "R$ 459,90",
                "image": f"{_PLACEHOLDER}/equipamento.svg",
                "link": f"{_LIST_BASE}/webcam-4k-reuniao",
            },
        ],
    },
]


def _normalize(text: str) -> str:
    lowered = text.lower().strip()
    normalized = unicodedata.normalize("NFKD", lowered)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def get_fallback_offers(query: str | None, *, limit: int = 12) -> list[dict[str, Any]]:
    """Seleciona prateleira curada por palavras-chave da busca."""
    haystack = _normalize(query or "")
    selected = _SHELVES[-1]["offers"]

    best_score = 0
    for shelf in _SHELVES:
        score = sum(1 for kw in shelf["keywords"] if _normalize(kw) in haystack)
        if score > best_score:
            best_score = score
            selected = shelf["offers"]

    safe_limit = max(1, min(limit, 24))
    return [
        {**offer, "fallback": True}
        for offer in selected[:safe_limit]
    ]
