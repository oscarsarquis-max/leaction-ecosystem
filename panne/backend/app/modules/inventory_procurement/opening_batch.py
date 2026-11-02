"""Inventário inicial em lote: várias aberturas de saldo sem nota, tudo ou nada.

Não tem regra própria de estoque. Cada linha passa por `services.open_balance`
(a mesma abertura de `/inventory/openings`) e, quando o ingrediente é novo, por
`create_ingredient` (o mesmo cadastro sem nota). O lote só acrescenta:
validação por linha, ingrediente novo repetido no mesmo lote e atomicidade.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import Session

from app.modules.identity_organization.authorization import (
    PERMISSION_INGREDIENT_CREATE,
    PERMISSION_INVENTORY_ADJUST,
    Principal,
    require_permission,
)
from app.modules.ingredient_catalog.models import Ingredient, MeasurementUnit
from app.modules.inventory_procurement import services
from app.modules.inventory_procurement.models import InventoryItem, InventoryLocation
from app.modules.production_http.errors import _MESSAGES
from app.modules.production_planning.errors import (
    ConcurrencyError,
    IdempotencyConflictError,
    ImmutableError,
    InvalidStateError,
    ValidationError,
)

MAX_LINES = 200
DEFAULT_REASON = "Inventário inicial"
COMMAND = "inventory.opening.batch"

# Palavras de embalagem: viram a unidade "un" e exigem o conteúdo de cada embalagem.
PACKAGE_WORDS = frozenset(
    {
        "embalagem", "embalagens", "emb", "pacote", "pacotes", "pct", "pcts",
        "caixa", "caixas", "cx", "fardo", "fardos", "fd", "saco", "sacos",
        "lata", "latas", "garrafa", "garrafas", "pote", "potes", "frasco", "frascos",
        "balde", "baldes", "galao", "galão", "galoes", "galões", "bandeja", "bandejas",
    }
)

_UNIT_LABEL = {
    "un": "unidade ou embalagem",
    "g": "gramas",
    "kg": "quilos",
    "ml": "mililitros",
    "l": "litros",
}

_FIELD_BY_CODE = {
    "unidade_incompativel": "unit_code",
    "unidade incompatível": "unit_code",
    "unidade_obrigatoria": "unit_code",
    "unidade_nao_cadastrada": "unit_code",
    "unidade_volume_nao_suportada": "unit_code",
    "quantidade_invalida": "quantity",
    "quantidade_obrigatoria": "quantity",
    "custo_ou_desconhecido": "unit_cost",
    "custo_desconhecido_nao_aceita_valor": "unit_cost",
    "custo_invalido": "unit_cost",
    "conteudo_embalagem_incompleto": "package_content_quantity",
    "conteudo_embalagem_obrigatorio": "package_content_quantity",
    "conteudo_embalagem_unidade_invalida": "package_content_unit",
    "conteudo_embalagem_nao_se_aplica": "package_content_quantity",
    "validade_ambigua": "expires_on",
    "data_invalida": "expires_on",
    "recurso_nao_encontrado": "ingredient",
    "ingrediente_obrigatorio": "ingredient",
    "ingrediente_ja_existe": "ingredient",
    "nome_ingrediente_invalido": "ingredient",
    "lote_invalido": "lot_code",
}

_LINE_KEYS = {
    "ingredient_id",
    "new_ingredient",
    "quantity",
    "unit_code",
    "package_content_quantity",
    "package_content_unit",
    "lot_code",
    "expires_on",
    "no_expiry",
    "unit_cost",
    "cost_unknown",
}

_LINE_ERRORS = (
    ValidationError,
    InvalidStateError,
    ImmutableError,
    ConcurrencyError,
    IdempotencyConflictError,
    IntegrityError,
    DataError,
)


class OpeningBatchError(Exception):
    """Nada foi gravado. `errors` traz um item por problema, com a linha."""

    def __init__(self, errors: list[dict[str, Any]]) -> None:
        super().__init__("inventario_com_erros")
        self.errors = errors


class _Problem(Exception):
    def __init__(self, field: str, code: str, message: str | None = None) -> None:
        super().__init__(code)
        self.field = field
        self.code = code
        self.message = message


def _message(code: str, fallback: str | None = None) -> str:
    return _MESSAGES.get(code) or fallback or "Não foi possível gravar este item. Confira os campos da linha."


def _error(index: int | None, field: str, code: str, message: str | None = None) -> dict[str, Any]:
    return {"index": index, "field": field, "code": code, "message": message or _message(code)}


def _blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _number(raw: Any, *, code: str, field: str) -> Decimal:
    if isinstance(raw, bool) or isinstance(raw, float):
        raise _Problem(field, code)
    text = str(raw).strip().replace(" ", "").replace("R$", "")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise _Problem(field, code) from None
    if not value.is_finite():
        raise _Problem(field, code)
    return value


def _positive(raw: Any, *, code: str, field: str) -> Decimal:
    value = _number(raw, code=code, field=field)
    if value <= 0:
        raise _Problem(field, code)
    return value


def _date(raw: Any, field: str) -> date:
    text = str(raw).strip()
    match = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", text)
    try:
        if match:
            return date(int(match.group(3)), int(match.group(2)), int(match.group(1)))
        return date.fromisoformat(text[:10])
    except ValueError:
        raise _Problem(field, "data_invalida") from None


def _unit(session: Session, raw: Any, field: str) -> tuple[MeasurementUnit, bool]:
    text = str(raw or "").strip()
    if not text:
        raise _Problem(field, "unidade_obrigatoria")
    is_package = text.casefold() in PACKAGE_WORDS
    try:
        unit = services.resolve_measurement_unit(session, "un" if is_package else text)
    except ValidationError:
        raise _Problem(field, "unidade_nao_cadastrada") from None
    if unit.dimension not in {"mass", "count"}:
        raise _Problem(field, "unidade_volume_nao_suportada")
    return unit, is_package


def normalize_name(value: str) -> str:
    """Nome para comparar: sem acento, sem caixa e com espaços únicos."""
    plain = unicodedata.normalize("NFD", str(value or ""))
    plain = "".join(char for char in plain if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", plain).strip().casefold()


def _clean_name(raw: Any) -> str:
    name = re.sub(r"\s+", " ", str(raw or "")).strip()
    if not name or len(name) > 200:
        raise _Problem("ingredient", "nome_ingrediente_invalido")
    return name


def _gram(session: Session) -> MeasurementUnit:
    unit = session.scalar(select(MeasurementUnit).where(MeasurementUnit.code == "g"))
    if unit is None:
        raise ValidationError("unidade_obrigatoria")
    return unit


def _header(session: Session, org: UUID, body: dict) -> tuple[InventoryLocation | None, str, date | None, list[dict]]:
    errors: list[dict] = []
    location = None
    try:
        location = services._get(session, InventoryLocation, org, UUID(str(body.get("inventory_location_id"))))
        if location.status != "active":
            errors.append(_error(None, "inventory_location_id", "local_invalido"))
    except (ValidationError, ValueError, TypeError):
        errors.append(_error(None, "inventory_location_id", "local_invalido"))
    reason = re.sub(r"\s+", " ", str(body.get("reason") or "")).strip() or DEFAULT_REASON
    if len(reason) > 200:
        errors.append(_error(None, "reason", "contrato_invalido", "O motivo tem texto demais. Use até 200 caracteres."))
    counted_on = None
    if not _blank(body.get("counted_on")):
        try:
            counted_on = _date(body["counted_on"], "counted_on")
        except _Problem as problem:
            errors.append(_error(None, "counted_on", problem.code))
        else:
            from app.modules.inventory_procurement.operational_date import (
                inventory_operational_date,
            )

            if counted_on > inventory_operational_date():
                errors.append(_error(None, "counted_on", "data_contagem_futura"))
    return location, reason, counted_on, errors


def _resolve_ingredient(
    session: Session,
    principal: Principal,
    org: UUID,
    line: dict,
    created_here: dict[str, tuple[UUID, str]],
) -> tuple[UUID, str, str | None, bool]:
    """Devolve (id, nome, unidade de controle pedida para o novo, criado agora)."""
    has_id = not _blank(line.get("ingredient_id"))
    new = line.get("new_ingredient")
    if has_id and new:
        raise _Problem("ingredient", "escolha_insumo_ambigua")
    if has_id:
        try:
            ingredient_id = UUID(str(line["ingredient_id"]))
        except ValueError:
            raise _Problem("ingredient", "recurso_nao_encontrado") from None
        ingredient = session.get(Ingredient, ingredient_id)
        if ingredient is None or ingredient.organization_id != org:
            raise _Problem("ingredient", "recurso_nao_encontrado")
        return ingredient.id, ingredient.display_name, None, False
    if not isinstance(new, dict):
        raise _Problem("ingredient", "ingrediente_obrigatorio")
    unknown = set(new) - {"display_name", "unit_code"}
    if unknown:
        raise _Problem("ingredient", "linha_invalida")
    name = _clean_name(new.get("display_name"))
    unit, _is_package = _unit(session, new.get("unit_code") or line.get("unit_code"), "unit_code")
    key = normalize_name(name)
    if key in created_here:
        ingredient_id, shown = created_here[key]
        return ingredient_id, shown, unit.code, False
    for existing_id, existing_name in session.execute(
        select(Ingredient.id, Ingredient.display_name).where(Ingredient.organization_id == org)
    ):
        if normalize_name(existing_name) == key:
            raise _Problem(
                "ingredient",
                "ingrediente_ja_existe",
                f'Já existe "{existing_name}" no cadastro. Escolha esse ingrediente na lista '
                "em vez de criar outro com o mesmo nome.",
            )
    from app.modules.ingredient_catalog.commands import create_ingredient

    require_permission(principal, PERMISSION_INGREDIENT_CREATE)
    created = create_ingredient(
        session,
        principal,
        code=None,
        display_name=name,
        ingredient_type="simple",
        nutrition_basis_unit_id=_gram(session).id,
        notes=None,
        idempotency_key=uuid4(),
        code_mode="suggested",
    )
    return created.id, created.display_name, unit.code, True


def _apply_line(
    session: Session,
    principal: Principal,
    org: UUID,
    location: InventoryLocation,
    reason: str,
    counted_on: date | None,
    line: dict,
    created_here: dict[str, tuple[UUID, str]],
) -> dict[str, Any]:
    unknown = set(line) - _LINE_KEYS
    if unknown:
        raise _Problem("line", "linha_invalida")
    if _blank(line.get("quantity")):
        raise _Problem("quantity", "quantidade_obrigatoria")
    quantity = _positive(line["quantity"], code="quantidade_invalida", field="quantity")
    unit, is_package = _unit(session, line.get("unit_code"), "unit_code")

    lot_code = None if _blank(line.get("lot_code")) else str(line["lot_code"]).strip()
    if lot_code is not None and len(lot_code) > 80:
        raise _Problem("lot_code", "lote_invalido")

    expires_on = None
    if not _blank(line.get("expires_on")):
        if line.get("no_expiry"):
            raise _Problem("expires_on", "validade_ambigua")
        expires_on = _date(line["expires_on"], "expires_on").isoformat()

    cost_unknown = bool(line.get("cost_unknown"))
    unit_cost = None
    if not _blank(line.get("unit_cost")):
        if cost_unknown:
            raise _Problem("unit_cost", "custo_desconhecido_nao_aceita_valor")
        cost = _number(line["unit_cost"], code="custo_invalido", field="unit_cost")
        if cost < 0:
            raise _Problem("unit_cost", "custo_invalido")
        unit_cost = format(cost, "f")
    elif not cost_unknown:
        raise _Problem("unit_cost", "custo_ou_desconhecido")

    pack_qty = pack_unit = None
    has_qty = not _blank(line.get("package_content_quantity"))
    has_unit = not _blank(line.get("package_content_unit"))
    if has_qty or has_unit or is_package:
        if unit.dimension != "count":
            raise _Problem("package_content_quantity", "conteudo_embalagem_nao_se_aplica")
        if not has_qty and not has_unit:
            raise _Problem("package_content_quantity", "conteudo_embalagem_obrigatorio")
        if has_qty != has_unit:
            raise _Problem("package_content_quantity", "conteudo_embalagem_incompleto")
        content = _positive(
            line["package_content_quantity"], code="conteudo_embalagem_obrigatorio", field="package_content_quantity"
        )
        try:
            content_unit = services.resolve_measurement_unit(session, line["package_content_unit"])
        except ValidationError:
            raise _Problem("package_content_unit", "conteudo_embalagem_unidade_invalida") from None
        if content_unit.dimension not in {"mass", "volume"}:
            raise _Problem("package_content_unit", "conteudo_embalagem_unidade_invalida")
        pack_qty, pack_unit = format(content, "f"), content_unit.code

    ingredient_id, ingredient_name, new_unit, created = _resolve_ingredient(
        session, principal, org, line, created_here
    )
    if new_unit is not None and new_unit != unit.code:
        raise _Problem(
            "unit_code",
            "unidade_incompativel",
            f"O ingrediente novo foi criado em {_UNIT_LABEL.get(new_unit, new_unit)}. Use a mesma unidade na linha.",
        )
    item = session.scalar(
        select(InventoryItem).where(
            InventoryItem.organization_id == org,
            InventoryItem.ingredient_id == ingredient_id,
        )
    )
    if item is not None and item.unit_code.casefold() != unit.code.casefold():
        raise _Problem(
            "unit_code",
            "unidade_incompativel",
            f"Este ingrediente é controlado em {_UNIT_LABEL.get(item.unit_code, item.unit_code)}. "
            "Use essa unidade.",
        )

    lot = services.open_balance(
        session,
        principal,
        {
            "ingredient_id": str(ingredient_id),
            "inventory_location_id": str(location.id),
            "quantity": format(quantity, "f"),
            "unit_code": unit.code,
            "supplier_lot_code": lot_code,
            "expires_on": expires_on,
            "occurred_on": None if counted_on is None else counted_on.isoformat(),
            "reason": reason,
            "origin": reason,
            "unit_cost": unit_cost,
            "cost_unknown": cost_unknown,
            "package_content_quantity": pack_qty,
            "package_content_unit": pack_unit,
            "confirmed": True,
        },
        idempotency_key=None,
    )
    return {
        "ingredient_id": ingredient_id,
        "ingredient_name": ingredient_name,
        "ingredient_created": created,
        "inventory_lot_id": lot.id,
        "internal_lot_code": lot.internal_lot_code,
    }


def _line_error_from(exc: Exception, index: int) -> dict[str, Any]:
    if isinstance(exc, _Problem):
        return _error(index, exc.field, exc.code, exc.message)
    if isinstance(exc, ValidationError):
        reason = str(exc)
        code = reason if reason in _MESSAGES else "regra_de_dominio"
        return _error(index, _FIELD_BY_CODE.get(reason, "line"), code, _message(reason))
    if isinstance(exc, (InvalidStateError, ImmutableError, ConcurrencyError, IdempotencyConflictError)):
        reason = getattr(exc, "reason", "regra_de_dominio")
        return _error(index, "line", reason, _message(reason))
    return _error(index, "line", "regra_de_dominio")


def open_balance_batch(session: Session, principal: Principal, body: dict, *, idempotency_key) -> dict[str, Any]:
    """Grava todas as linhas ou nenhuma. Repetir a mesma chave não grava de novo."""
    require_permission(principal, PERMISSION_INVENTORY_ADJUST)
    org = services._org(principal)
    lines = body.get("lines") or []
    if not lines:
        raise OpeningBatchError([_error(None, "lines", "inventario_sem_linhas")])
    if len(lines) > MAX_LINES:
        raise OpeningBatchError([_error(None, "lines", "inventario_linhas_demais")])

    replay = services._replay(session, org, idempotency_key, COMMAND, body)
    if replay is not None:
        return {
            "batch_id": str(replay.resource_id),
            "line_count": len(lines),
            "created_ingredients": None,
            "lines": [],
            "replayed": True,
        }

    location, reason, counted_on, header_errors = _header(session, org, body)
    if header_errors:
        raise OpeningBatchError(header_errors)
    assert location is not None

    errors: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    created_here: dict[str, tuple[UUID, str]] = {}
    outer = session.begin_nested()
    try:
        for index, line in enumerate(lines):
            if not isinstance(line, dict):
                errors.append(_error(index, "line", "linha_invalida"))
                continue
            try:
                with session.begin_nested():
                    done = _apply_line(session, principal, org, location, reason, counted_on, line, created_here)
            except (_Problem, *_LINE_ERRORS) as exc:
                errors.append(_line_error_from(exc, index))
                continue
            if done["ingredient_created"]:
                name = normalize_name(done["ingredient_name"])
                created_here[name] = (done["ingredient_id"], done["ingredient_name"])
            results.append({"index": index, **done})
        if errors:
            outer.rollback()
            raise OpeningBatchError(errors)
        batch_id = uuid4()
        services._store_command(
            session, org, idempotency_key, COMMAND, body, "inventory_opening_batch", batch_id, principal.user_id
        )
        outer.commit()
    except OpeningBatchError:
        raise
    except Exception:
        if outer.is_active:
            outer.rollback()
        raise
    return {
        "batch_id": str(batch_id),
        "line_count": len(results),
        "created_ingredients": sum(1 for row in results if row["ingredient_created"]),
        "lines": [
            {
                "index": row["index"],
                "ingredient_id": str(row["ingredient_id"]),
                "ingredient_name": row["ingredient_name"],
                "ingredient_created": row["ingredient_created"],
                "inventory_lot_id": str(row["inventory_lot_id"]),
                "internal_lot_code": row["internal_lot_code"],
            }
            for row in results
        ],
        "replayed": False,
    }
