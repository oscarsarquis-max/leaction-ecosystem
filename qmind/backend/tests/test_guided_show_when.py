"""Unit tests for guided show_when evaluation."""

from app.modules.guided.show_when import matches_show_when, visible_questions


def test_null_show_when_always_visible():
    assert matches_show_when(None, []) is True
    assert matches_show_when(None, [{"question_id": "a", "answer_value": "yes"}]) is True


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


def test_answer_equals_and_not_equals():
    assert (
        matches_show_when(
            {"answer": "g", "equals": "yes"},
            [{"question_id": "g", "answer_value": "yes"}],
        )
        is True
    )
    assert (
        matches_show_when(
            {"answer": "g", "not_equals": "no"},
            [{"question_id": "g", "answer_value": "yes"}],
        )
        is True
    )
    assert (
        matches_show_when(
            {"answer": "g", "not_equals": "yes"},
            [{"question_id": "g", "answer_value": "yes"}],
        )
        is False
    )


def test_context_not_empty():
    rule = {"context": "qms_scope.exclusions", "not_empty": True}
    assert matches_show_when(rule, [], {"qms_scope": {"exclusions": ""}}) is False
    assert matches_show_when(rule, [], {"qms_scope": {"exclusions": "  "}}) is False
    assert (
        matches_show_when(
            rule, [], {"qms_scope": {"exclusions": "Desenvolvimento de produto"}}
        )
        is True
    )


def test_all_and_any():
    answers = [{"question_id": "a", "answer_value": "yes"}]
    ctx = {"qms_scope": {"exclusions": "X"}}
    assert (
        matches_show_when(
            {
                "all": [
                    {"answer": "a", "equals": "yes"},
                    {"context": "qms_scope.exclusions", "not_empty": True},
                ]
            },
            answers,
            ctx,
        )
        is True
    )
    assert (
        matches_show_when(
            {
                "any": [
                    {"answer": "a", "equals": "no"},
                    {"context": "qms_scope.exclusions", "not_empty": True},
                ]
            },
            answers,
            ctx,
        )
        is True
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


def test_hidden_not_in_applicable_total():
    questions = [
        {"id": "always", "show_when": None},
        {
            "id": "excl",
            "show_when": {"context": "qms_scope.exclusions", "not_empty": True},
        },
    ]
    visible = visible_questions(questions, [], {"qms_scope": {"exclusions": ""}})
    assert [q["id"] for q in visible] == ["always"]


def test_catalog_four_branch_conditions_present():
    from app.modules.guided import catalog as catalog_mod

    catalog_mod.clear_catalog_cache()
    by_id = {q["id"]: q for q in catalog_mod.list_questions()}

    assert by_id["c4-scp-02"]["show_when"] == {
        "context": "qms_scope.exclusions",
        "not_empty": True,
    }
    assert by_id["c8-des-02"]["show_when"] == {
        "answer": "c8-des-01",
        "in": ["yes", "partial"],
    }
    assert by_id["c7-res-02"]["show_when"] == {
        "answer": "c7-msr-01",
        "in": ["yes", "partial"],
    }
    assert by_id["c8-prd-03"]["show_when"] == {
        "answer": "c8-prop-01",
        "in": ["yes", "partial"],
    }


def test_catalog_includes_clauses_6_to_10():
    from app.modules.guided import catalog as catalog_mod

    catalog_mod.clear_catalog_cache()
    cat = catalog_mod.load_catalog()
    assert cat["catalog_version"] == "iso9001-2015-c4c10-v1"
    refs = {q["clause_ref"].split(".")[0] for q in cat["questions"]}
    assert {"4", "5", "6", "7", "8", "9", "10"}.issubset(refs)
    assert len(cat["questions"]) >= 50
