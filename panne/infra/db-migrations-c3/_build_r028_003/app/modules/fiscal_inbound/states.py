"""Máquina de estados do documento fiscal de entrada."""

from app.modules.fiscal_inbound.constants import (
    DOCUMENT_STATUSES,
    TERMINAL_STATUSES,
    TRANSITIONS,
)
from app.modules.production_planning.errors import (
    ImmutableError,
    InvalidStateError,
    ValidationError,
)


def assert_known(status: str) -> str:
    if status not in DOCUMENT_STATUSES:
        raise ValidationError("contrato_invalido")
    return status


def allowed_targets(status: str) -> frozenset[str]:
    return TRANSITIONS.get(assert_known(status), frozenset())


def assert_transition(current: str, target: str) -> str:
    assert_known(current)
    assert_known(target)
    if target not in allowed_targets(current):
        raise InvalidStateError("transicao_invalida")
    return target


def assert_mutable(status: str) -> str:
    if assert_known(status) in TERMINAL_STATUSES:
        raise ImmutableError("transicao_invalida")
    return status
