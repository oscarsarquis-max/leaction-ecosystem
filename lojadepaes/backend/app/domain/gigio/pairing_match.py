"""Correspondência oferta↔perfil sem transferir qualidade de estilo para SKU."""

from __future__ import annotations

import re
import unicodedata

from app.domain.offer_contract import offer_fits_contract

_YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")

_GENERIC_WINE = ("vinho tinto", "vinho branco", "vinho rose", "vinho rosé", "espumante", "750 ml", "750ml")
_REGION_OR_NAME_ONLY = frozenset({"dao", "dão", "canastra"})
_IG_MARKERS = ("indicacao geografica", "indicação geográfica", "ig201002", "ip canastra", "aprocan")
_NON_PAIRING_EVIDENCE = frozenset(
    {"official_register", "research_project", "method_help", "style_unverified", "guide_evaluation"}
)


def _fold(value: object) -> str:
    text = " ".join(str(value or "").split()).casefold()
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(char for char in nfkd if not unicodedata.combining(char))


def _tokens(value: object) -> set[str]:
    return {part for part in _fold(value).replace("-", " ").split() if len(part) > 2}


def _identity_value(identity: dict, *keys: str) -> str:
    for key in keys:
        raw = identity.get(key)
        if raw:
            return _fold(raw)
    return ""


def _offer_vintage(offer: dict) -> str:
    explicit = _fold(offer.get("vintage") or offer.get("safra") or "")
    if explicit:
        return explicit
    years = _YEAR_RE.findall(str(offer.get("title") or offer.get("name") or ""))
    if len(years) == 1:
        return years[0]
    return ""


def nature_matches(offer: dict, ref: dict) -> bool:
    category = str(offer.get("category") or "")
    if category != str(ref.get("category") or ""):
        return False
    title = str(offer.get("title") or offer.get("name") or "")
    return offer_fits_contract(title=title, category=category)


def _usable_for_pairing(ref: dict) -> tuple[bool, str]:
    role = str(ref.get("retrieval_role") or "")
    if role in {"informational", "excluded", "evaluation"}:
        return False, "referência fora da recuperação de harmonização"
    evidence = str(ref.get("evidence_type") or "")
    if evidence in _NON_PAIRING_EVIDENCE:
        return False, "tipo de evidência não fundamenta correspondência de oferta"
    if str(ref.get("verification_status") or "") == "inaccessible":
        return False, "fonte inacessível nesta verificação"
    return True, ""


def _region_name_only(ref: dict) -> bool:
    hints = [_fold(item) for item in (ref.get("match_hints") or []) if str(item).strip()]
    return bool(hints) and all(hint in _REGION_OR_NAME_ONLY for hint in hints)


def profile_compatible(offer: dict, ref: dict) -> bool:
    if not nature_matches(offer, ref):
        return False
    if _region_name_only(ref):
        return False
    scope = str(ref.get("scope") or "")
    hints = [_fold(item) for item in (ref.get("match_hints") or []) if str(item).strip()]
    if scope == "general":
        return False
    if not hints:
        return False
    hay = _fold(
        " ".join(
            [
                str(offer.get("title") or offer.get("name") or ""),
                str(offer.get("brand") or ""),
                str(offer.get("variety") or ""),
                str(offer.get("line") or ""),
            ]
        )
    )
    return any(hint in hay for hint in hints)


def identity_matches(offer: dict, ref: dict) -> tuple[bool, str]:
    identity = ref.get("identity") or {}
    if str(ref.get("scope") or "") != "product":
        return False, "referência de estilo ou geral não identifica um produto"
    brand = _identity_value(identity, "brand", "producer", "marca")
    line = _identity_value(identity, "line", "linha")
    variety = _identity_value(identity, "variety", "variedade")
    volume = _identity_value(identity, "volume")
    vintage = _identity_value(identity, "vintage", "safra")
    if not brand or not (line or variety):
        return False, "identidade da referência incompleta"
    offer_brand = _fold(offer.get("brand") or "")
    offer_title = _fold(offer.get("title") or offer.get("name") or "")
    offer_line = _fold(offer.get("line") or "")
    offer_variety = _fold(offer.get("variety") or "")
    offer_volume = _fold(offer.get("volume") or "")
    offer_vintage = _offer_vintage(offer)
    if brand not in offer_brand and brand not in offer_title:
        return False, "marca ou produtor não confere"
    if line and line not in offer_line and line not in offer_title:
        return False, "linha não confere"
    if variety and variety not in offer_variety and variety not in offer_title:
        return False, "variedade não confere"
    if volume and offer_volume and volume != offer_volume:
        return False, "volume divergente"
    if vintage and offer_vintage and vintage != offer_vintage:
        return False, "safra divergente não herda análise"
    if vintage and not offer_vintage:
        return False, "safra da oferta ausente"
    return True, "identidade confere"


def data_complete(offer: dict, ref: dict) -> tuple[bool, str]:
    title = " ".join(str(offer.get("title") or offer.get("name") or "").split())
    if not title or not offer.get("category"):
        return False, "título ou categoria ausentes"
    folded = _fold(title)
    extras = _tokens(title) - _tokens(" ".join(_GENERIC_WINE))
    if str(ref.get("scope") or "") == "product" and not (offer.get("brand") or extras):
        return False, "aproximação de nome genérico insuficiente"
    if str(offer.get("category") or "") == "vinhos" and extras <= {"vinho", "tinto", "branco", "rose", "garrafa", "ml"}:
        if not offer.get("brand"):
            return False, "anúncio genérico sem marca"
    return True, "dados suficientes para o estágio"


def match_offer_to_reference(offer: dict, ref: dict) -> dict:
    usable, usable_reason = _usable_for_pairing(ref)
    nature = nature_matches(offer, ref)
    title = _fold(offer.get("title") or offer.get("name") or "")
    if "canastra" in title and not any(marker in title for marker in _IG_MARKERS):
        if str(ref.get("evidence_type") or "") == "official_register" or "canastra" in [
            _fold(item) for item in (ref.get("match_hints") or [])
        ]:
            return {
                "nature": nature,
                "profile": False,
                "data_complete": False,
                "data_reason": "palavra Canastra não prova IG do anúncio",
                "identity": False,
                "identity_reason": "faltam marcas de registro autorizado",
                "editorial_approved": False,
                "correspondence": "none",
                "caution": "A palavra Canastra no título não prova produto da IG.",
                "excellence": None,
                "commission_used": False,
            }
    profile = profile_compatible(offer, ref) if nature and usable else False
    complete, complete_reason = data_complete(offer, ref)
    identity_ok, identity_reason = identity_matches(offer, ref) if str(ref.get("scope") or "") == "product" else (False, "")
    editorial = bool(ref.get("loja_choice")) and str(ref.get("editorial_status") or "") == "published"
    correspondence = "none"
    caution = ""
    if not usable:
        caution = usable_reason
    elif _region_name_only(ref):
        caution = "região ou nome geográfico não prova correspondência"
    elif nature and str(ref.get("scope") or "") == "product" and identity_ok and complete:
        correspondence = "specific"
    elif nature and profile and str(ref.get("scope") or "") == "style":
        correspondence = "style"
        caution = "Perfil de estilo; não certifica esta garrafa ou lote."
    elif nature and not profile:
        caution = "Natureza correta, sem atributo que comprove o perfil."
    elif not nature:
        caution = "Natureza incompatível."
    if not complete and correspondence == "specific":
        correspondence = "none"
        caution = complete_reason
    return {
        "nature": nature,
        "profile": profile,
        "data_complete": complete,
        "data_reason": complete_reason,
        "identity": identity_ok,
        "identity_reason": identity_reason,
        "editorial_approved": editorial,
        "correspondence": correspondence,
        "caution": caution,
        "excellence": None,
        "commission_used": False,
    }


def match_offer_to_evaluation(offer: dict, ref: dict) -> dict:
    """Nota de guia só com identidade comprovada. Estilo não herda pontuação."""
    role = str(ref.get("retrieval_role") or "")
    evidence = str(ref.get("evidence_type") or "")
    if role != "evaluation" or evidence != "guide_evaluation":
        return {
            "correspondence": "none",
            "caution": "não é avaliação de guia verificada",
            "identity": False,
        }
    if str(ref.get("verification_status") or "") != "verified":
        return {"correspondence": "none", "caution": "avaliação pendente ou inacessível", "identity": False}
    if str(ref.get("editorial_status") or "") != "published":
        return {"correspondence": "none", "caution": "avaliação não publicada", "identity": False}
    if str(ref.get("scope") or "") != "product":
        return {"correspondence": "none", "caution": "avaliação sem rótulo identificado", "identity": False}
    identity_ok, identity_reason = identity_matches(offer, ref)
    complete, complete_reason = data_complete(offer, ref)
    if identity_ok and complete:
        return {
            "correspondence": "specific",
            "caution": "Avaliação do guia para este rótulo e safra; não prova harmonização.",
            "identity": True,
            "identity_reason": identity_reason,
            "data_complete": True,
        }
    return {
        "correspondence": "none",
        "caution": identity_reason or complete_reason,
        "identity": identity_ok,
        "identity_reason": identity_reason,
        "data_complete": complete,
    }


def _offer_tier(offer: dict, refs: list[dict]) -> str:
    best = ""
    for ref in refs:
        result = match_offer_to_reference(offer, ref)
        if not result["data_complete"]:
            continue
        if result["correspondence"] == "specific":
            return "specific"
        if result["correspondence"] == "style":
            best = "style"
    return best


def catalog_match_tier(offers: list[dict], refs: list[dict]) -> tuple[list[str], str]:
    """Primeiro a sugestão identificada do catálogo; senão, alternativa do mesmo perfil."""
    specific: list[str] = []
    style: list[str] = []
    for offer in offers:
        offer_id = str(offer.get("hub_offer_id") or offer.get("id") or "")
        if not offer_id:
            continue
        tier = _offer_tier(offer, refs)
        if tier == "specific" and offer_id not in specific:
            specific.append(offer_id)
        elif tier == "style" and offer_id not in style:
            style.append(offer_id)
    if specific:
        return specific, "specific"
    if style:
        return style, "style"
    return [], "none"


def compatible_offer_ids(offers: list[dict], refs: list[dict]) -> list[str]:
    """Só inclui oferta com correspondência comprovável. Não completa grade por inferência."""
    picked: list[str] = []
    seen: set[str] = set()
    for offer in offers:
        offer_id = str(offer.get("hub_offer_id") or offer.get("id") or "")
        if not offer_id or offer_id in seen:
            continue
        if _offer_tier(offer, refs) in {"style", "specific"}:
            seen.add(offer_id)
            picked.append(offer_id)
    return picked
