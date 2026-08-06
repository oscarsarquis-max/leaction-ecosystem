"""Unit tests for guided show_when evaluation."""

from app.modules.guided.show_when import matches_show_when, visible_questions


def test_null_show_when_always_visible():
    assert matches_show_when(null := None, []) is True
    assert matches_show_when(null, [{"question_id": "a", "answer_value": "yes"}]) is True


def test_answer_in_rule():
    rule = {"answer": "c6-rsk-01", "in": ["yes", "partial"]}
    assert matches_show_when(rule, []) is False
    assert (
        matches_show_when(
            rule, [{"question_id": "c6-rsk-01", "answer_value": "yes"}]
        )
        is True
    )
    assert (
        matches_show_when(
            rule, [{"question_id": "c6-rsk-01", "answer_value": "no"}]
        )
        is False
    )


def test_visible_questions_filters_followups():
    questions = [
        {"id": "gate", "show_when": None},
        {
            "id": "follow",
            "show_when": {"answer": "gate", "in": ["yes", "partial"]},
        },
    ]
    assert len(visible_questions(questions, [])) == 1
    assert (
        len(
            visible_questions(
                questions, [{"question_id": "gate", "answer_value": "yes"}]
            )
        )
        == 2
    )


def test_catalog_includes_clauses_6_to_10():
    from app.modules.guided import catalog as catalog_mod

    catalog_mod.clear_catalog_cache()
    cat = catalog_mod.load_catalog()
    assert cat["catalog_version"] == "iso9001-2015-c4c10-v1"
    refs = {q["clause_ref"].split(".")[0] for q in cat["questions"]}
    assert {"4", "5", "6", "7", "8", "9", "10"}.issubset(refs)
    assert len(cat["questions"]) >= 40
