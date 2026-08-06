"""Structural tests for versioned guided ISO catalogs."""

from __future__ import annotations

from collections import Counter

import pytest

from app.modules.guided import catalog as catalog_mod
from app.modules.guided.catalog import UnknownCatalogVersion

REQUIRED_FIELDS = {
    "id",
    "version",
    "theme",
    "clause_ref",
    "question",
    "explanation",
    "practice_examples",
    "evidence_examples",
    "answer_type",
    "required",
    "show_when",
}


@pytest.fixture(autouse=True)
def _clear_cache():
    catalog_mod.clear_catalog_cache()
    yield
    catalog_mod.clear_catalog_cache()


def test_available_versions_include_c4c5_and_c4c10():
    versions = catalog_mod.available_catalog_versions()
    assert "iso9001-2015-c4c5-v1" in versions
    assert "iso9001-2015-c4c10-v1" in versions
    assert catalog_mod.catalog_version() == "iso9001-2015-c4c10-v1"


def test_load_catalog_by_version():
    c45 = catalog_mod.load_catalog("iso9001-2015-c4c5-v1")
    c410 = catalog_mod.load_catalog("iso9001-2015-c4c10-v1")
    assert c45["catalog_version"] == "iso9001-2015-c4c5-v1"
    assert c410["catalog_version"] == "iso9001-2015-c4c10-v1"
    assert len(c45["questions"]) == 15
    assert len(c410["questions"]) >= 50


def test_unknown_version_raises():
    with pytest.raises(UnknownCatalogVersion):
        catalog_mod.load_catalog("iso9001-does-not-exist")


def test_c4c5_ids_preserved_in_c4c10():
    c45_ids = {q["id"] for q in catalog_mod.list_questions("iso9001-2015-c4c5-v1")}
    c410_ids = {q["id"] for q in catalog_mod.list_questions("iso9001-2015-c4c10-v1")}
    assert c45_ids <= c410_ids


def test_c4c10_structure_and_clause_coverage():
    cat = catalog_mod.load_catalog("iso9001-2015-c4c10-v1")
    questions = cat["questions"]
    ids = [q["id"] for q in questions]
    assert len(ids) == len(set(ids)), "duplicate question ids"

    by_clause = Counter(str(q["clause_ref"]).split(".")[0] for q in questions)
    for clause in ("4", "5", "6", "7", "8", "9", "10"):
        assert by_clause[clause] >= 1, f"missing clause {clause}"

    # ~35–45 net new beyond the 15 of c4–c5
    new_count = len(questions) - 15
    assert 35 <= new_count <= 45, f"expected 35–45 new questions, got {new_count}"

    for q in questions:
        missing = REQUIRED_FIELDS - set(q)
        assert not missing, f"{q.get('id')}: missing {missing}"
        assert isinstance(q["practice_examples"], list) and q["practice_examples"]
        assert isinstance(q["evidence_examples"], list) and q["evidence_examples"]
        assert isinstance(q["question"], str) and q["question"].strip()
        assert isinstance(q["explanation"], str) and q["explanation"].strip()
        assert q["show_when"] is None or isinstance(q["show_when"], dict)


def test_default_load_is_latest():
    assert catalog_mod.load_catalog()["catalog_version"] == catalog_mod.catalog_version()
