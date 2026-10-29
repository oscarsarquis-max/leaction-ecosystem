"""Calculadora de porcentagem de padeiro. Determinística: sem modelo."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.domain.errors import ConfirmationError

MODES = frozenset({"from_flour", "scale_flour", "scale_dough", "convert_levain"})
LEVAN_MODES = frozenset({"pff", "weight"})

MIN_FLOUR = Decimal("1")
MAX_FLOUR = Decimal("50000")
MIN_HYDRATION = Decimal("30")
MAX_HYDRATION = Decimal("150")
MIN_SALT = Decimal("0")
MAX_SALT = Decimal("5")
MIN_PFF = Decimal("0")
MAX_PFF = Decimal("50")
MIN_LEVAIN_H = Decimal("50")
MAX_LEVAIN_H = Decimal("150")


def _dec(value: object, field: str) -> Decimal:
    if value is None or value == "":
        raise ConfirmationError(f"informe {field}")
    try:
        raw = Decimal(str(value).replace(",", ".").strip())
    except Exception as exc:
        raise ConfirmationError(f"{field} inválido") from exc
    if not raw.is_finite():
        raise ConfirmationError(f"{field} inválido")
    return raw


def _grams(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _pct(value: Decimal, field: str, lo: Decimal, hi: Decimal) -> Decimal:
    if value < lo or value > hi:
        raise ConfirmationError(f"{field} deve ficar entre {lo} e {hi}")
    return value


def compute(payload: dict[str, Any]) -> dict[str, Any]:
    mode = str(payload.get("mode") or "from_flour").strip()
    if mode not in MODES:
        raise ConfirmationError("modo de cálculo não reconhecido")

    hydration = _pct(_dec(payload.get("hydration_pct"), "hidratação"), "hidratação", MIN_HYDRATION, MAX_HYDRATION)
    salt = _pct(_dec(payload.get("salt_pct"), "sal"), "sal", MIN_SALT, MAX_SALT)
    levain_h = _pct(
        _dec(payload.get("levain_hydration_pct"), "hidratação do levain"),
        "hidratação do levain",
        MIN_LEVAIN_H,
        MAX_LEVAIN_H,
    )
    levain_mode = str(payload.get("levain_mode") or "pff").strip()
    if levain_mode not in LEVAN_MODES:
        raise ConfirmationError("informe se o levain entra por farinha prefermentada ou pelo peso")

    extras = _extras(payload.get("extras"))

    if mode == "convert_levain":
        return _convert_levain(payload, hydration, salt, levain_h, levain_mode, extras)

    flour = _flour(payload.get("flour_g"))
    if mode == "scale_flour":
        flour = _flour(payload.get("target_flour_g"))
    result = _from_flour(flour, hydration, salt, levain_h, levain_mode, payload, extras)
    if mode == "scale_dough":
        target = _flour(payload.get("target_dough_g"), field="massa alvo")
        return _scale_to_dough(result, target)
    return result


def _flour(value: object, field: str = "farinha") -> Decimal:
    flour = _dec(value, field)
    if flour < MIN_FLOUR or flour > MAX_FLOUR:
        raise ConfirmationError(f"{field} deve ficar entre {MIN_FLOUR} g e {MAX_FLOUR} g")
    return flour


def _extras(raw: object) -> list[tuple[str, Decimal]]:
    if not raw:
        return []
    if not isinstance(raw, list):
        raise ConfirmationError("inclusões extras inválidas")
    items: list[tuple[str, Decimal]] = []
    for item in raw[:8]:
        if not isinstance(item, dict):
            continue
        name = " ".join(str(item.get("name") or "").split())[:40]
        if not name:
            continue
        pct = _pct(_dec(item.get("baker_pct"), f"porcentagem de {name}"), name, Decimal("0"), Decimal("40"))
        items.append((name, pct))
    return items


def _levain_parts(
    flour: Decimal,
    levain_h: Decimal,
    levain_mode: str,
    payload: dict[str, Any],
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    water_factor = levain_h / Decimal("100")
    if levain_mode == "weight":
        levain_weight = _dec(payload.get("levain_weight_g"), "peso do levain")
        if levain_weight < 0 or levain_weight > flour * Decimal("3"):
            raise ConfirmationError("peso do levain fora da faixa útil")
        levain_flour = levain_weight / (Decimal("1") + water_factor)
        pff = (levain_flour / flour * Decimal("100")) if flour else Decimal("0")
        if pff > MAX_PFF:
            raise ConfirmationError("o peso do levain usa mais farinha prefermentada do que o processo comporta")
        levain_water = levain_weight - levain_flour
        return pff, levain_flour, levain_water, levain_weight
    pff = _pct(_dec(payload.get("preferment_flour_pct"), "farinha prefermentada"), "farinha prefermentada", MIN_PFF, MAX_PFF)
    levain_flour = flour * pff / Decimal("100")
    levain_water = levain_flour * water_factor
    levain_weight = levain_flour + levain_water
    return pff, levain_flour, levain_water, levain_weight


def _from_flour(
    flour: Decimal,
    hydration: Decimal,
    salt: Decimal,
    levain_h: Decimal,
    levain_mode: str,
    payload: dict[str, Any],
    extras: list[tuple[str, Decimal]],
) -> dict[str, Any]:
    pff, levain_flour, levain_water, levain_weight = _levain_parts(flour, levain_h, levain_mode, payload)
    total_water = flour * hydration / Decimal("100")
    mix_water = total_water - levain_water
    if mix_water < 0:
        raise ConfirmationError(
            "a água do levain já ultrapassa a hidratação total; reduza o levain ou aumente a hidratação"
        )
    mix_flour = flour - levain_flour
    salt_g = flour * salt / Decimal("100")
    extra_rows = []
    extra_total = Decimal("0")
    for name, pct in extras:
        grams = flour * pct / Decimal("100")
        extra_total += grams
        extra_rows.append({"name": name, "baker_pct": _num(pct), "grams": _grams(grams)})
    dough = flour + total_water + salt_g + extra_total
    return {
        "mode": "from_flour",
        "flour_g": _grams(flour),
        "hydration_pct": _num(hydration),
        "salt_pct": _num(salt),
        "preferment_flour_pct": _num(pff),
        "levain_hydration_pct": _num(levain_h),
        "levain_mode": levain_mode,
        "final_mix": {
            "flour_g": _grams(mix_flour),
            "water_g": _grams(mix_water),
            "salt_g": _grams(salt_g),
            "levain_g": _grams(levain_weight),
            "extras": extra_rows,
        },
        "levain": {
            "flour_g": _grams(levain_flour),
            "water_g": _grams(levain_water),
            "weight_g": _grams(levain_weight),
        },
        "totals": {
            "flour_g": _grams(flour),
            "water_g": _grams(total_water),
            "salt_g": _grams(salt_g),
            "levain_g": _grams(levain_weight),
            "dough_g": _grams(dough),
        },
        "notes": [
            "A farinha do levain já está na farinha total (100%). Não some o levain outra vez como farinha extra.",
            "PFF é a farinha que entra no levain. O peso do levain inclui essa farinha e a água dele.",
        ],
    }


def _scale_to_dough(result: dict[str, Any], target: Decimal) -> dict[str, Any]:
    current = Decimal(result["totals"]["dough_g"])
    if current <= 0:
        raise ConfirmationError("não há massa para escalar")
    factor = target / current
    scaled_flour = Decimal(result["flour_g"]) * factor
    payload = {
        "preferment_flour_pct": result["preferment_flour_pct"],
        "levain_weight_g": Decimal(result["levain"]["weight_g"]) * factor,
        "extras": [
            {"name": row["name"], "baker_pct": row["baker_pct"]}
            for row in result["final_mix"]["extras"]
        ],
    }
    scaled = _from_flour(
        scaled_flour,
        Decimal(str(result["hydration_pct"])),
        Decimal(str(result["salt_pct"])),
        Decimal(str(result["levain_hydration_pct"])),
        result["levain_mode"],
        payload,
        [(row["name"], Decimal(str(row["baker_pct"]))) for row in result["final_mix"]["extras"]],
    )
    scaled["mode"] = "scale_dough"
    scaled["scale_factor"] = _num(factor)
    scaled["target_dough_g"] = _grams(target)
    return scaled


def _convert_levain(
    payload: dict[str, Any],
    hydration: Decimal,
    salt: Decimal,
    levain_h: Decimal,
    levain_mode: str,
    extras: list[tuple[str, Decimal]],
) -> dict[str, Any]:
    flour = _flour(payload.get("flour_g"))
    result = _from_flour(flour, hydration, salt, levain_h, levain_mode, payload, extras)
    result["mode"] = "convert_levain"
    return result


def _num(value: Decimal) -> float:
    quantized = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return float(quantized)
