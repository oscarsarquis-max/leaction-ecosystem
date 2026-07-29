"""Interface comum dos providers context7."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, runtime_checkable


ALLOWED_TIPOS = frozenset({"PRD", "SDD", "DOC", "PLAYBOOK", "ADR"})


@dataclass
class Hit:
    """Hit normalizado para o contrato de artefato (L3 / UI)."""

    titulo: str
    tipo: str
    resumo: str
    score: float
    url: Optional[str] = None
    id: Optional[str] = None
    trecho: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "titulo": self.titulo,
            "tipo": self.tipo,
            "resumo": self.resumo,
            "score": self.score,
        }
        if self.url:
            data["url"] = self.url
        if self.id:
            data["id"] = self.id
        if self.trecho:
            data["trecho"] = self.trecho
        return data


@dataclass
class Context7SearchResult:
    hits: list[Hit]
    keywords: list[str] = field(default_factory=list)
    source: str = "context7"
    meta: dict[str, Any] = field(default_factory=dict)

    def hits_as_dicts(self) -> list[dict[str, Any]]:
        return [h.to_dict() for h in self.hits]


@runtime_checkable
class Context7Provider(Protocol):
    """Protocolo: busca hits a partir de keywords (+ desafio opcional)."""

    name: str

    def search(
        self,
        keywords: list[str],
        *,
        top_k: int = 2,
        filtros: Optional[dict[str, Any]] = None,
        challenge: str = "",
    ) -> Context7SearchResult:
        ...


def normalize_tipo(raw: Any) -> str:
    tipo = str(raw or "DOC").strip().upper()
    return tipo if tipo in ALLOWED_TIPOS else "DOC"


def clamp_score(raw: Any, default: float = 0.75) -> float:
    try:
        score = float(raw if raw is not None else default)
    except (TypeError, ValueError):
        score = default
    return max(0.0, min(1.0, score))


def hit_from_mapping(item: dict[str, Any]) -> Hit:
    return Hit(
        titulo=str(item.get("titulo") or item.get("title") or "Documento").strip(),
        tipo=normalize_tipo(item.get("tipo") or item.get("type")),
        resumo=str(
            item.get("resumo")
            or item.get("summary")
            or item.get("arquitetura")
            or item.get("trecho")
            or ""
        ).strip(),
        score=clamp_score(item.get("score")),
        url=(str(item["url"]).strip() if item.get("url") else None),
        id=(str(item["id"]).strip() if item.get("id") is not None else None),
        trecho=(str(item["trecho"]).strip() if item.get("trecho") else None),
    )


def apply_min_score(
    hits: list[Hit],
    min_score: Optional[float],
) -> list[Hit]:
    if min_score is None:
        return hits
    return [h for h in hits if h.score >= min_score]
