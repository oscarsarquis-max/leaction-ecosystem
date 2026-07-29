"""Testes da fila build_order / module_prompts (sem LLM)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from services.build_order import (  # noqa: E402
    build_initial_queue,
    extract_build_order_from_inputs,
    mark_module_entregue,
    normalize_build_order,
)
from services.phase_sdd import _normalize_sdd  # noqa: E402


FINANCE_BUILD_ORDER = [
    {"modulo": "ledger-service", "depende_de": [], "escopo": "núcleo double-entry, ACID, append-only"},
    {
        "modulo": "scheduler-service",
        "depende_de": ["ledger-service"],
        "escopo": "agenda de pagamentos, idempotência",
    },
    {
        "modulo": "bank-integration-service",
        "depende_de": ["ledger-service"],
        "escopo": "Open Finance + PIX",
    },
    {
        "modulo": "reconciliation-service",
        "depende_de": ["ledger-service", "bank-integration-service"],
        "escopo": "casamento extrato x lançamentos",
    },
    {
        "modulo": "notification-service",
        "depende_de": ["scheduler-service"],
        "escopo": "alertas",
    },
]


def test_normalize_and_initial_statuses_finance_case():
    queue = build_initial_queue(FINANCE_BUILD_ORDER, {
        m["modulo"]: f"prompt {m['modulo']}" for m in FINANCE_BUILD_ORDER
    })
    by_mod = {q["modulo"]: q for q in queue}
    assert by_mod["ledger-service"]["status"] == "liberado"
    assert by_mod["scheduler-service"]["status"] == "pendente"
    assert by_mod["bank-integration-service"]["status"] == "pendente"
    assert by_mod["reconciliation-service"]["status"] == "pendente"
    assert by_mod["notification-service"]["status"] == "pendente"


def test_deliver_ledger_unlocks_scheduler_and_bank():
    queue = build_initial_queue(FINANCE_BUILD_ORDER)
    updated = mark_module_entregue(queue, "ledger-service")
    by_mod = {q["modulo"]: q["status"] for q in updated}
    assert by_mod["ledger-service"] == "entregue"
    assert by_mod["scheduler-service"] == "liberado"
    assert by_mod["bank-integration-service"] == "liberado"
    assert by_mod["reconciliation-service"] == "pendente"
    assert by_mod["notification-service"] == "pendente"


def test_deliver_bank_then_unlocks_reconciliation():
    queue = build_initial_queue(FINANCE_BUILD_ORDER)
    queue = mark_module_entregue(queue, "ledger-service")
    queue = mark_module_entregue(queue, "bank-integration-service")
    by_mod = {q["modulo"]: q["status"] for q in queue}
    assert by_mod["reconciliation-service"] == "liberado"
    assert by_mod["notification-service"] == "pendente"


def test_cannot_deliver_pending_module():
    queue = build_initial_queue(FINANCE_BUILD_ORDER)
    with pytest.raises(ValueError, match="não está liberado"):
        mark_module_entregue(queue, "scheduler-service")


def test_sdd_without_build_order_keeps_empty_list():
    normalized = _normalize_sdd({"sdd_markdown": "# SDD\n\nMonolito simples."})
    assert normalized["sdd_markdown"].startswith("# SDD")
    assert normalized["build_order"] == []


def test_extract_build_order_from_inputs_nested():
    inputs = {
        "generate_sdd": {
            "artifact_data": {
                "sdd_markdown": "# x",
                "build_order": FINANCE_BUILD_ORDER,
            }
        }
    }
    order = extract_build_order_from_inputs(inputs)
    assert len(order) == 5
    assert order[0]["modulo"] == "ledger-service"


def test_normalize_build_order_aliases():
    raw = [
        {"module": "a", "depends_on": ["b"], "scope": "x"},
        {"modulo": "b", "depende_de": [], "escopo": "y"},
    ]
    order = normalize_build_order(raw)
    assert {o["modulo"] for o in order} == {"a", "b"}
    a = next(o for o in order if o["modulo"] == "a")
    assert a["depende_de"] == ["b"]
    assert a["escopo"] == "x"
