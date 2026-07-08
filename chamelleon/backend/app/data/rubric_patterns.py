"""Padrão PanelDX (ctdi_rubricas): label_rubr curto + desc_rubr obrigatório."""

from __future__ import annotations

from typing import Any

# Escala Presente PanelDX (grad 0–5) — apenas fallback textual, não como label fixo.
PANELDX_PRESENTE_SHORT: dict[int, str] = {
    0: "Inexistente",
    1: "Incipiente",
    2: "Experimental",
    3: "Estabelecido",
    4: "Consolidado",
    5: "Otimizado",
}

PANELDX_PRESENTE_GENERIC_DESC: dict[int, str] = {
    0: "Não há prática formalizada ou estruturada nesta capacidade.",
    1: "Prática incipiente, sem planos estruturados ou comunicação ampla.",
    2: "Prática em experimentação ou estruturação inicial.",
    3: "Prática documentada, estabelecida e comunicada oficialmente.",
    4: "Prática consolidada, monitorada e integrada à operação.",
    5: "Prática otimizada, revisada dinamicamente com base em dados.",
}

# Escala Futuro PanelDX (grad 0–5) — horizonte de adoção/evolução.
PANELDX_FUTURO_SHORT: dict[int, str] = {
    0: "Sem Previsão",
    1: "Longo Prazo",
    2: "Médio Prazo (P)",
    3: "Médio Prazo (E)",
    4: "Curto Prazo (P)",
    5: "Curto Prazo (T)",
}

PANELDX_FUTURO_GENERIC_DESC: dict[int, str] = {
    0: "Não há expectativa ou plano para a adoção desta prática no setor.",
    1: "Adoção ou evolução prevista apenas para um horizonte de longo prazo.",
    2: "Adoção parcialmente prevista ou em planejamento para o médio prazo.",
    3: "Adoção totalmente prevista e orçamentada para o médio prazo.",
    4: "Adoção parcialmente iniciada com previsão de conclusão no curto prazo.",
    5: "Prioridade total para adoção imediata (próximos 90 dias).",
}

SHORT_MATURITY_LABELS: dict[int, str] = PANELDX_PRESENTE_SHORT
LONG_MATURITY_DESCRIPTIONS: dict[int, str] = PANELDX_PRESENTE_GENERIC_DESC

GENERIC_MATURITY_LABELS = frozenset(PANELDX_PRESENTE_SHORT.values())
GENERIC_FUTURO_LABELS = frozenset(PANELDX_FUTURO_SHORT.values())

_LABEL_PREFIXES = (
    "apenas ",
    "não há ",
    "uso de ",
)

_TRAILING_PREPOSITIONS = frozenset(
    {"de", "da", "do", "das", "dos", "em", "na", "no", "nas", "nos", "com", "para", "por", "ao", "aos"}
)

_MODIFIER_WORDS = frozenset(
    {
        "totalmente",
        "parcialmente",
        "predominantemente",
        "completamente",
        "amplamente",
    }
)


def derive_short_label(description: str, *, max_len: int = 25) -> str:
    """Deriva label curto contextual a partir da descrição (padrão ctdi_rubricas)."""
    text = (description or "").strip()
    if not text:
        return ""

    for sep in (";", ",", "."):
        if sep in text:
            text = text.split(sep, 1)[0].strip()

    lowered = text.lower()
    for prefix in _LABEL_PREFIXES:
        if lowered.startswith(prefix):
            text = text[len(prefix) :].strip()
            lowered = text.lower()

    words = [word for word in text.split() if word]
    if not words:
        return ""

    if len(words) == 1:
        candidate = words[0]
    else:
        second = words[1].lower()
        if second in _MODIFIER_WORDS and len(words) >= 3:
            candidate = f"{words[0]} {words[2]}"
        else:
            candidate = f"{words[0]} {words[1]}"
        if words[1].lower() in _TRAILING_PREPOSITIONS and len(words) >= 3:
            third = f"{words[0]} {words[1]} {words[2]}"
            if len(third) <= max_len:
                candidate = third

    if len(candidate) > max_len:
        candidate = candidate[: max_len + 1].rsplit(" ", 1)[0] or candidate[:max_len]

    return candidate[:1].upper() + candidate[1:] if candidate else candidate


def _parse_grad(option: dict[str, Any], index: int) -> int:
    grad = option.get("grad_rubr", option.get("weight", index))
    try:
        grad = int(grad)
    except (TypeError, ValueError):
        grad = index
    return max(0, min(5, grad))


def is_generic_futuro_label(label: str) -> bool:
    return (label or "").strip() in GENERIC_FUTURO_LABELS


def is_generic_maturity_label(label: str) -> bool:
    return (label or "").strip() in GENERIC_MATURITY_LABELS


def _is_fragment_label(label: str) -> bool:
    """Detecta labels derivados quebrados (ex.: 'Adoção ou', 'Prática em')."""
    text = (label or "").strip()
    if not text:
        return True
    parts = text.split()
    if parts[-1].lower() in _TRAILING_PREPOSITIONS:
        return True
    if len(parts) >= 2 and parts[0].lower() == "adoção":
        return True
    if text.lower() in {"adoção ou", "adoção parcialmente", "não há", "prática em"}:
        return True
    return False


def _paneldx_short_label(description: str, grad: int) -> str | None:
    """Retorna label canônico PanelDX quando a descrição é genérica conhecida."""
    desc = (description or "").strip()
    if desc == PANELDX_FUTURO_GENERIC_DESC.get(grad):
        return PANELDX_FUTURO_SHORT[grad]
    if desc == PANELDX_PRESENTE_GENERIC_DESC.get(grad):
        return PANELDX_PRESENTE_SHORT[grad]
    return None


def _infer_temporal_key(description: str) -> str | None:
    lowered = (description or "").lower()
    if any(token in lowered for token in ("adoção", "evolução prevista", "horizonte de longo prazo")):
        return "future"
    return None


def _extract_label_desc(option: dict[str, Any]) -> tuple[str, str]:
    label = (option.get("label_rubr") or option.get("label") or option.get("text") or "").strip()
    description = (
        option.get("desc_rubr") or option.get("description") or option.get("desc") or ""
    ).strip()
    return label, description


def _label_needs_rederivation(label: str, description: str) -> bool:
    label = (label or "").strip()
    description = (description or "").strip()
    if _is_fragment_label(label):
        return True
    if not label or not description:
        return True
    if label == description:
        return True
    if len(label) > 40:
        return True
    if is_generic_maturity_label(label) or is_generic_futuro_label(label):
        return False
    trailing = label.split()[-1].lower()
    if trailing in _TRAILING_PREPOSITIONS:
        return True
    label_lower = label.lower()
    desc_lower = description.lower()
    if label_lower in desc_lower and not desc_lower.startswith(label_lower):
        return True
    if desc_lower.startswith(label_lower):
        trailing = label.split()[-1].lower()
        if trailing in _MODIFIER_WORDS or trailing in _TRAILING_PREPOSITIONS:
            return True
    return False


def reconcile_label(
    label: str,
    description: str,
    grad: int,
    *,
    temporal_key: str | None = None,
) -> str:
    """Preserva labels contextuais PanelDX; usa escalas Presente/Futuro quando aplicável."""
    label = (label or "").strip()
    description = (description or "").strip()
    temporal = temporal_key or _infer_temporal_key(description)

    if not description and label:
        description = label
    if not description:
        if temporal == "future":
            description = PANELDX_FUTURO_GENERIC_DESC.get(grad, f"Descrição do nível {grad}.")
        else:
            description = PANELDX_PRESENTE_GENERIC_DESC.get(grad, f"Descrição do nível {grad}.")

    canonical = _paneldx_short_label(description, grad)
    if canonical:
        return canonical

    if temporal == "future" and (_is_fragment_label(label) or not label):
        return PANELDX_FUTURO_SHORT.get(grad, label or f"Nível {grad}")

    if label and not _label_needs_rederivation(label, description):
        return label

    if temporal == "future":
        return PANELDX_FUTURO_SHORT.get(grad, derive_short_label(description) or f"Nível {grad}")

    derived = derive_short_label(description)
    if derived and not _is_fragment_label(derived) and derived.lower() != description.lower():
        return derived

    return PANELDX_PRESENTE_SHORT.get(grad, label or derived or f"Nível {grad}")


def default_maturity_options() -> list[dict[str, Any]]:
    return normalize_question_options([], pad_to_six=True)


def default_futuro_options() -> list[dict[str, Any]]:
    """Rubricas padrão Futuro (horizonte temporal PanelDX)."""
    result: list[dict[str, Any]] = []
    for grad in range(6):
        result.append(
            from_ctdi_rubrica(
                {
                    "grad_rubr": grad,
                    "label_rubr": PANELDX_FUTURO_SHORT[grad],
                    "desc_rubr": PANELDX_FUTURO_GENERIC_DESC[grad],
                },
                display_order=grad + 1,
            )
        )
    validate_rubric_options(result)
    return result


def normalize_question_options(
    options: list[dict[str, Any]],
    *,
    pad_to_six: bool = True,
    temporal_key: str | None = None,
) -> list[dict[str, Any]]:
    """Normaliza rubricas para padrão PanelDX: 6 níveis, label curto contextual + desc_rubr."""
    by_grad: dict[int, dict[str, str]] = {}

    for index, option in enumerate(options):
        grad = _parse_grad(option, index)
        label, description = _extract_label_desc(option)
        if not description and label:
            description = label
        label = reconcile_label(label, description, grad, temporal_key=temporal_key)
        by_grad[grad] = {"label_rubr": label, "desc_rubr": description}

    if pad_to_six:
        for grad in range(6):
            if grad in by_grad:
                continue
            if temporal_key == "future":
                description = PANELDX_FUTURO_GENERIC_DESC[grad]
                label = PANELDX_FUTURO_SHORT[grad]
            else:
                description = PANELDX_PRESENTE_GENERIC_DESC[grad]
                label = reconcile_label("", description, grad, temporal_key=temporal_key)
            by_grad[grad] = {"label_rubr": label, "desc_rubr": description}

    ordered_grads = sorted(by_grad.keys())
    result = [
        from_ctdi_rubrica({"grad_rubr": grad, **by_grad[grad]}, display_order=position + 1)
        for position, grad in enumerate(ordered_grads)
    ]
    validate_rubric_options(result)
    return result


def normalize_sector_question_options(
    options: list[dict[str, Any]],
    *,
    temporal_key: str | None = None,
) -> list[dict[str, Any]]:
    """Normaliza rubricas setoriais preservando label_rubr/desc_rubr gerados pela IA."""
    if not options:
        return normalize_question_options([], pad_to_six=True, temporal_key=temporal_key)

    indexed = sorted(
        enumerate(options),
        key=lambda pair: _parse_grad(pair[1], pair[0]),
    )
    normalized = [
        normalize_rubric_option(opt, _parse_grad(opt, idx), temporal_key=temporal_key)
        for idx, opt in indexed
    ]
    by_grad: dict[int, dict[str, Any]] = {}
    for opt in normalized:
        by_grad[_parse_grad(opt, 0)] = opt
    if len(by_grad) < 6:
        padded = (
            default_futuro_options()
            if temporal_key == "future"
            else normalize_question_options([], pad_to_six=True)
        )
        for grad in range(6):
            if grad not in by_grad:
                by_grad[grad] = padded[grad]
        normalized = [by_grad[grad] for grad in range(6)]

    validate_rubric_options(normalized)
    return normalized


def repair_rubric_options(
    options: list[dict[str, Any]],
    *,
    temporal_key: str | None = None,
) -> list[dict[str, Any]]:
    """Repara labels truncados/fragmentados em rubricas já gravadas (ex.: 'Adoção ou')."""
    if not options:
        return options
    repaired: list[dict[str, Any]] = []
    for index, option in enumerate(options):
        if not isinstance(option, dict):
            continue
        grad = _parse_grad(option, index)
        label, description = _extract_label_desc(option)
        fixed_label = reconcile_label(label, description, grad, temporal_key=temporal_key)
        repaired.append(
            from_ctdi_rubrica(
                {
                    "grad_rubr": grad,
                    "label_rubr": fixed_label,
                    "desc_rubr": description or label,
                },
                display_order=option.get("display_order", grad + 1),
            )
        )
    if len(repaired) == 6:
        validate_rubric_options(repaired)
    return repaired


def from_ctdi_rubrica(rub: dict[str, Any], *, display_order: int | None = None) -> dict[str, Any]:
    """Mapeia uma linha de ctdi_rubricas sem alterar o conteúdo PanelDX."""
    label = (rub.get("label_rubr") or rub.get("label") or "").strip()
    description = (rub.get("desc_rubr") or rub.get("description") or "").strip()

    if not description:
        raise ValueError("Rubrica PanelDX exige desc_rubr preenchido.")

    if not label:
        grad = rub.get("grad_rubr", rub.get("weight", 0))
        try:
            grad_int = int(grad)
        except (TypeError, ValueError):
            grad_int = 0
        label = reconcile_label("", description, grad_int) or description.strip()
    elif _is_fragment_label(label):
        grad = rub.get("grad_rubr", rub.get("weight", 0))
        try:
            grad_int = int(grad)
        except (TypeError, ValueError):
            grad_int = 0
        label = reconcile_label(label, description, grad_int)

    grad = rub.get("grad_rubr", rub.get("weight", 0))
    try:
        weight = int(grad)
    except (TypeError, ValueError):
        weight = 0

    order = display_order if display_order is not None else weight + 1

    return {
        "text": label,
        "description": description,
        "label_rubr": label,
        "desc_rubr": description,
        "weight": weight,
        "grad_rubr": weight,
        "display_order": order,
    }


def normalize_rubric_option(
    option: dict[str, Any],
    index: int = 0,
    *,
    temporal_key: str | None = None,
) -> dict[str, Any]:
    """Normaliza uma opção na gravação — preserva labels contextuais PanelDX."""
    grad = _parse_grad(option, index)
    label, description = _extract_label_desc(option)

    if not description and label:
        description = label
    if not description:
        if temporal_key == "future":
            description = PANELDX_FUTURO_GENERIC_DESC.get(grad, f"Descrição do nível {grad}.")
        else:
            description = LONG_MATURITY_DESCRIPTIONS.get(grad, f"Descrição do nível {grad}.")

    label = reconcile_label(label, description, grad, temporal_key=temporal_key)

    return from_ctdi_rubrica(
        {
            "label_rubr": label,
            "desc_rubr": description,
            "grad_rubr": grad,
        },
        display_order=option.get("display_order", grad + 1),
    )


def normalize_rubric_options(options: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not options:
        return default_maturity_options()

    grads = {_parse_grad(opt, idx) for idx, opt in enumerate(options)}
    if len(options) == 6 and grads == set(range(6)):
        normalized = [
            normalize_rubric_option(opt, _parse_grad(opt, idx))
            for idx, opt in sorted(
                enumerate(options),
                key=lambda pair: _parse_grad(pair[1], pair[0]),
            )
        ]
        validate_rubric_options(normalized)
        return normalized

    return normalize_question_options(options, pad_to_six=True)


def validate_rubric_options(options: list[dict[str, Any]]) -> None:
    """Garante padrão PanelDX: toda rubrica com descrição."""
    for idx, opt in enumerate(options):
        description = (opt.get("desc_rubr") or opt.get("description") or "").strip()
        label = (opt.get("label_rubr") or opt.get("text") or opt.get("label") or "").strip()
        if not description:
            raise ValueError(f"Rubrica {idx + 1} sem desc_rubr/description.")
        if not label:
            raise ValueError(f"Rubrica {idx + 1} sem label_rubr/text.")
        if label == description and len(label) > 40:
            raise ValueError(f"Rubrica {idx + 1} com label igual ao texto longo.")
