from datetime import date
from decimal import Decimal

import pytest
from app.modules.formula_lab.models import (
    Approval,
    FormulationRecipeReference,
    ProcessStep,
    RecipeReference,
    Trial,
    TrialMeasurement,
)
from app.modules.formula_lab.rules import latest_approval_decision, publish_formulation_version
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from tests import helpers


def test_process_step_sequence_and_invalid_duration(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-step")
    product = helpers.technical_product(db_session, organization, "PAO-ST")
    recipe = helpers.formulation(db_session, product, "REC-ST")
    version = helpers.formulation_version(db_session, recipe)
    db_session.add(
        ProcessStep(
            organization_id=organization.id,
            formulation_version_id=version.id,
            sequence=1,
            title="Mistura",
            instructions="Misturar a farinha e a água.",
            duration_seconds=600,
            temperature_celsius=Decimal("24.50"),
        )
    )
    db_session.flush()
    db_session.add(
        ProcessStep(
            organization_id=organization.id,
            formulation_version_id=version.id,
            sequence=1,
            title="Duplicado",
            instructions="Não.",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_process_step_negative_duration_rejected(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-step-neg")
    product = helpers.technical_product(db_session, organization, "PAO-SN")
    recipe = helpers.formulation(db_session, product, "REC-SN")
    version = helpers.formulation_version(db_session, recipe)
    db_session.add(
        ProcessStep(
            organization_id=organization.id,
            formulation_version_id=version.id,
            sequence=1,
            title="Forno",
            instructions="Assar.",
            duration_seconds=-1,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_trial_rejects_foreign_organization(db_session: Session) -> None:
    one = helpers.org(db_session, "org-tr-a")
    two = helpers.org(db_session, "org-tr-b")
    product = helpers.technical_product(db_session, one, "PAO-TR")
    recipe = helpers.formulation(db_session, product, "REC-TR")
    version = helpers.formulation_version(db_session, recipe)
    db_session.add(
        Trial(
            organization_id=two.id,
            formulation_version_id=version.id,
            code="TR-1",
            status="planned",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_trial_measurement_invalid_type_and_preservation(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-tr-m")
    actor = helpers.user(db_session, "trial@panne.test")
    product = helpers.technical_product(db_session, organization, "PAO-TM")
    recipe = helpers.formulation(db_session, product, "REC-TM")
    version = helpers.formulation_version(db_session, recipe)
    trial = Trial(
        organization_id=organization.id,
        formulation_version_id=version.id,
        code="TR-OK",
        status="in_progress",
        planned_on=date(2026, 8, 22),
        created_by_user_id=actor.id,
    )
    db_session.add(trial)
    db_session.flush()
    db_session.add(
        TrialMeasurement(
            organization_id=organization.id,
            trial_id=trial.id,
            measurement_type="aroma",
            value=Decimal("1"),
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_completed_trial_and_measurement_preserved(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-tr-c")
    unit = helpers.gram(db_session)
    product = helpers.technical_product(db_session, organization, "PAO-TC")
    recipe = helpers.formulation(db_session, product, "REC-TC")
    version = helpers.formulation_version(db_session, recipe)
    trial = Trial(
        organization_id=organization.id,
        formulation_version_id=version.id,
        code="TR-C",
        status="in_progress",
    )
    db_session.add(trial)
    db_session.flush()
    db_session.add(
        TrialMeasurement(
            organization_id=organization.id,
            trial_id=trial.id,
            measurement_type="dough_mass",
            value=Decimal("1650"),
            measurement_unit_id=unit.id,
        )
    )
    db_session.flush()
    trial.status = "completed"
    db_session.flush()
    trial.notes = "alterar"
    with pytest.raises(Exception, match="trial_preserved"):
        db_session.flush()


def test_approval_append_only_and_revocation_keeps_history(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-appr")
    actor = helpers.user(db_session, "appr@panne.test")
    product = helpers.technical_product(db_session, organization, "PAO-AP")
    recipe = helpers.formulation(db_session, product, "REC-AP")
    version = helpers.formulation_version(db_session, recipe)
    first = helpers.approve_version(db_session, version, actor, "approved")
    first.decision = "revoked"
    with pytest.raises(Exception, match="append_only"):
        db_session.flush()


def test_revocation_preserves_prior_approval_row(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-rev")
    actor = helpers.user(db_session, "rev@panne.test")
    unit = helpers.gram(db_session)
    product = helpers.technical_product(db_session, organization, "PAO-RV")
    recipe = helpers.formulation(db_session, product, "REC-RV")
    version = helpers.formulation_version(db_session, recipe)
    flour = helpers.published_ingredient(db_session, organization, unit, "FAR-RV")
    helpers.formulation_item(
        db_session, version, flour, unit, 1, Decimal("800"), is_flour_basis=True
    )
    approved = helpers.approve_version(db_session, version, actor, "approved")
    revoked = helpers.approve_version(db_session, version, actor, "revoked")
    rows = db_session.query(Approval).filter_by(formulation_version_id=version.id).all()
    assert {row.decision for row in rows} == {"approved", "revoked"}
    assert approved.id != revoked.id
    assert latest_approval_decision(db_session, version.id) == "revoked"
    with pytest.raises(Exception):
        publish_formulation_version(db_session, version)


def test_recipe_reference_same_organization_only(db_session: Session) -> None:
    one = helpers.org(db_session, "org-ref-a")
    two = helpers.org(db_session, "org-ref-b")
    product = helpers.technical_product(db_session, one, "PAO-RF")
    recipe = helpers.formulation(db_session, product, "REC-RF")
    reference = RecipeReference(
        organization_id=two.id,
        title="Receita externa",
        source_type="external",
        source_url="https://exemplo.invalid/receita",
        license_or_usage_notes="somente procedência",
    )
    db_session.add(reference)
    db_session.flush()
    db_session.add(
        FormulationRecipeReference(
            organization_id=one.id,
            formulation_id=recipe.id,
            recipe_reference_id=reference.id,
            role="inspiration",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
