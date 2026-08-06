"""Evaluate catalog show_when rules against guided answers and context."""

from __future__ import annotations

from typing import Any, Mapping


def _answer_map(answers: list[Any] | None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for a in answers or []:
        if isinstance(a, Mapping):
            qid = a.get("question_id")
            val = a.get("answer_value")
        else:
            qid = getattr(a, "question_id", None)
            val = getattr(a, "answer_value", None)
        if qid:
            out[str(qid)] = val
    return out


def _resolve_path(root: Any, path: str) -> Any:
    cur = root
    for part in path.split("."):
        if cur is None:
            return None
        if isinstance(cur, Mapping):
            cur = cur.get(part)
        else:
            cur = getattr(cur, part, None)
    return cur


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def _compare_leaf(rule: Mapping[str, Any], value: Any) -> bool:
    """Apply equals / not_equals / in / not_empty to a resolved value."""
    if "not_empty" in rule:
        want = bool(rule.get("not_empty"))
        empty = _is_empty(value)
        return (not empty) if want else empty

    if "equals" in rule:
        return value == rule.get("equals")

    if "not_equals" in rule:
        return value != rule.get("not_equals")

    if "in" in rule:
        allowed = rule.get("in")
        if not isinstance(allowed, list):
            return True
        return value in allowed

    # Unknown leaf operators → do not hide the question.
    return True


def matches_show_when(
    show_when: Any,
    answers: list[Any] | None,
    context: Mapping[str, Any] | None = None,
) -> bool:
    """Return True if the question should be shown.

    Supported shapes:
      null / missing → always show
      {"all": [ ... ]} / {"any": [ ... ]}
      {"answer": "qid", "in"|"equals"|"not_equals"|"not_empty": ...}
      {"context": "dotted.path", "in"|"equals"|"not_equals"|"not_empty": ...}
    """
    if show_when is None:
        return True
    if not isinstance(show_when, Mapping):
        return True

    if "all" in show_when:
        conds = show_when.get("all") or []
        return all(matches_show_when(c, answers, context) for c in conds)
    if "any" in show_when:
        conds = show_when.get("any") or []
        return any(matches_show_when(c, answers, context) for c in conds)

    if "answer" in show_when:
        qid = show_when.get("answer")
        if not qid:
            return True
        current = _answer_map(answers).get(str(qid))
        return _compare_leaf(show_when, current)

    if "context" in show_when:
        path = show_when.get("context")
        if not path or not isinstance(path, str):
            return True
        current = _resolve_path(context or {}, path)
        return _compare_leaf(show_when, current)

    return True


def visible_questions(
    questions: list[dict[str, Any]],
    answers: list[Any] | None,
    context: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return [
        q
        for q in questions
        if matches_show_when(q.get("show_when"), answers, context)
    ]
