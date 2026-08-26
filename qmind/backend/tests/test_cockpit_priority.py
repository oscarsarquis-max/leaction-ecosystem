"""Pure unit tests for cockpit priority precedence (ISOI-010)."""

from __future__ import annotations

import pytest

from app.modules.cockpit.priority import (
    CasePrioritySnapshot,
    band_for_reasons,
    collect_priority_reasons,
    compute_priority,
)


def _snap(**overrides) -> CasePrioritySnapshot:
    base = dict(
        case_status="acting",
        intelligence_freshness="never_analyzed",
        execution_posture=None,
        has_overdue_action=False,
        has_active_impediment=False,
        has_open_dependency=False,
        has_overdue_dependency=False,
        measurement_posture="not_planned",
        target_posture="unknown",
        claims_execution_without_approved_evidence=False,
        has_current_attention_signal=False,
        has_stale_check_in=False,
        awaiting_human_observation=False,
        has_outcome_observation=False,
        has_active_execution=True,
    )
    base.update(overrides)
    return CasePrioritySnapshot(**base)


def test_immediate_stalled_current():
    band, reasons = compute_priority(
        _snap(intelligence_freshness="current", execution_posture="stalled")
    )
    assert band == "immediate_attention"
    assert "ei_current_stalled" in {r.code for r in reasons}


def test_immediate_overdue_plus_impediment():
    band, reasons = compute_priority(
        _snap(has_overdue_action=True, has_active_impediment=True)
    )
    assert band == "immediate_attention"
    codes = {r.code for r in reasons}
    assert "overdue_action_with_active_impediment" in codes
    assert "overdue_action" not in codes
    assert "active_impediment" not in codes


def test_immediate_overdue_dependency_plus_overdue_action():
    band, reasons = compute_priority(
        _snap(has_overdue_action=True, has_overdue_dependency=True, has_open_dependency=True)
    )
    assert band == "immediate_attention"
    assert "overdue_dependency_with_overdue_action" in {r.code for r in reasons}


def test_attention_overdue_alone():
    band, reasons = compute_priority(_snap(has_overdue_action=True))
    assert band == "attention"
    assert "overdue_action" in {r.code for r in reasons}


@pytest.mark.parametrize(
    ("overrides", "expected_code"),
    [
        ({"execution_posture": "attention_required", "intelligence_freshness": "current"}, "ei_current_attention_required"),
        ({"has_active_impediment": True}, "active_impediment"),
        ({"has_open_dependency": True}, "active_dependency"),
        ({"measurement_posture": "overdue"}, "measurement_overdue"),
        ({"target_posture": "not_met"}, "target_not_met"),
        ({"target_posture": "mixed"}, "target_mixed"),
        ({"claims_execution_without_approved_evidence": True}, "claims_execution_without_approved_evidence"),
        ({"has_current_attention_signal": True}, "current_oi_attention_signal"),
    ],
)
def test_attention_reasons(overrides, expected_code):
    band, reasons = compute_priority(_snap(**overrides))
    assert band == "attention"
    assert expected_code in {r.code for r in reasons}


@pytest.mark.parametrize(
    ("overrides", "expected_code"),
    [
        ({"intelligence_freshness": "stale"}, "ei_stale"),
        ({"intelligence_freshness": "never_analyzed"}, "ei_never_analyzed"),
        ({"execution_posture": "awaiting_result_evaluation", "intelligence_freshness": "current"}, "awaiting_result_evaluation"),
        ({"measurement_posture": "awaiting_baseline", "intelligence_freshness": "current", "execution_posture": "progressing"}, "awaiting_baseline"),
        ({"measurement_posture": "awaiting_measurement", "intelligence_freshness": "current", "execution_posture": "progressing"}, "awaiting_measurement"),
        ({"has_stale_check_in": True, "intelligence_freshness": "current", "execution_posture": "progressing"}, "stale_check_in"),
        ({"awaiting_human_observation": True, "intelligence_freshness": "current", "execution_posture": "progressing"}, "pending_human_observation"),
    ],
)
def test_follow_up_reasons(overrides, expected_code):
    band, reasons = compute_priority(_snap(**overrides))
    assert band == "follow_up"
    assert expected_code in {r.code for r in reasons}


def test_stale_check_in_not_added_when_stalled():
    reasons = collect_priority_reasons(
        _snap(
            intelligence_freshness="current",
            execution_posture="stalled",
            has_stale_check_in=True,
        )
    )
    assert "stale_check_in" not in {r.code for r in reasons}
    assert band_for_reasons(reasons, _snap(intelligence_freshness="current", execution_posture="stalled")) == "immediate_attention"


def test_on_course_progressing():
    band, reasons = compute_priority(
        _snap(
            intelligence_freshness="current",
            execution_posture="progressing",
            has_active_execution=True,
        )
    )
    assert band == "on_course"
    assert "ei_current_progressing" in {r.code for r in reasons}


def test_completed_closed():
    band, reasons = compute_priority(
        _snap(
            case_status="closed",
            has_outcome_observation=True,
            has_active_execution=False,
            intelligence_freshness="current",
            execution_posture="result_observed",
        )
    )
    assert band == "completed_or_observed"
    codes = {r.code for r in reasons}
    assert "case_closed" in codes or "outcome_observed" in codes


def test_worst_band_wins_with_multiple_reasons():
    band, reasons = compute_priority(
        _snap(
            intelligence_freshness="stale",
            has_overdue_action=True,
            has_active_impediment=True,
            measurement_posture="overdue",
        )
    )
    assert band == "immediate_attention"
    codes = {r.code for r in reasons}
    assert "overdue_action_with_active_impediment" in codes
    assert "ei_stale" in codes
    assert "measurement_overdue" in codes


def test_reason_labels_are_human_portuguese():
    _, reasons = compute_priority(_snap(has_overdue_action=True))
    assert reasons[0].label
    assert "action:" not in reasons[0].label.lower()
    assert "@" not in reasons[0].label


def test_stale_check_in_boundary_exact_72h():
    """Exactly 72h is still recent; >72h is stale (CHECK_IN_STALE_WINDOW_HOURS)."""
    from datetime import UTC, datetime, timedelta
    from uuid import uuid4

    from app.modules.agile.schemas import CHECK_IN_STALE_WINDOW_HOURS
    from app.modules.cockpit.batch_fingerprint import case_action_aggregates
    from app.modules.improvement_cases.execution_intelligence_schemas import (
        ExecutionActionFacts,
        ExecutionCaseFacts,
        ExecutionFacts,
        ExecutionIntelligenceInput,
        MeasurementFacts,
    )
    from app.modules.oi.schemas import SourceRef

    as_of = datetime(2026, 8, 26, 12, 0, 0, tzinfo=UTC)
    exactly = as_of - timedelta(hours=CHECK_IN_STALE_WINDOW_HOURS)
    just_over = exactly - timedelta(seconds=1)
    created = as_of - timedelta(days=10)

    def _snapshot(last_check_in_at: datetime) -> ExecutionIntelligenceInput:
        return ExecutionIntelligenceInput(
            schema_version="1.0",
            core_organization_id=uuid4(),
            improvement_case_id=uuid4(),
            request_id="r1",
            correlation_id="r1",
            captured_at=as_of,
            source=SourceRef(system="qmind-core", component="test"),
            case=ExecutionCaseFacts(status="acting"),
            execution=ExecutionFacts(
                actions=[
                    ExecutionActionFacts(
                        action_ref="a1",
                        label="Ação",
                        status="in_progress",
                        owner_assigned=True,
                        created_at=created,
                        last_check_in_at=last_check_in_at,
                        check_in_count=1,
                        is_terminal=False,
                        claims_execution=False,
                    )
                ]
            ),
            measurement=MeasurementFacts(),
            outcome=None,
            fact_refs=["case.status"],
        )

    at_boundary = case_action_aggregates(_snapshot(exactly), as_of=as_of)
    assert at_boundary["has_stale_check_in"] is False
    assert at_boundary["stale_check_in_count"] == 0

    past_boundary = case_action_aggregates(_snapshot(just_over), as_of=as_of)
    assert past_boundary["has_stale_check_in"] is True
    assert past_boundary["stale_check_in_count"] == 1

    # Priority reason follows the aggregate flag
    band, reasons = compute_priority(
        _snap(
            has_stale_check_in=past_boundary["has_stale_check_in"],
            intelligence_freshness="current",
            execution_posture="progressing",
        )
    )
    assert band == "follow_up"
    assert "stale_check_in" in {r.code for r in reasons}

    band_ok, reasons_ok = compute_priority(
        _snap(
            has_stale_check_in=at_boundary["has_stale_check_in"],
            intelligence_freshness="current",
            execution_posture="progressing",
        )
    )
    assert "stale_check_in" not in {r.code for r in reasons_ok}
    assert band_ok == "on_course"
