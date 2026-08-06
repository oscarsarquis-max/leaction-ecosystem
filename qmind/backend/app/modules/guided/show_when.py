"""Evaluate catalog show_when rules against guided answers."""

from __future__ import annotations

from typing import Any, Mapping


def _answer_map(answers: list[Any] | None) -> dict[str, str | None]:
    out: dict[str, str | None] = {}
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


def matches_show_when(
    show_when: Any,
    answers: list[Any] | None,
) -> bool:
    """Return True if the question should be shown.

    Supported shapes:
      null / missing → always show
      {"answer": "qid", "in": ["yes", "partial"]}
      {"all": [ ...conditions ]}
      {"any": [ ...conditions ]}
    """
    if show_when is None:
        return True
    if not isinstance(show_when, Mapping):
        return True

    if "all" in show_when:
        conds = show_when.get("all") or []
        return all(matches_show_when(c, answers) for c in conds)
    if "any" in show_when:
        conds = show_when.get("any") or []
        return any(matches_show_when(c, answers) for c in conds)

    qid = show_when.get("answer")
    allowed = show_when.get("in")
    if not qid or not isinstance(allowed, list):
        return True
    current = _answer_map(answers).get(str(qid))
    return current in allowed


def visible_questions(
    questions: list[dict[str, Any]],
    answers: list[Any] | None,
) -> list[dict[str, Any]]:
    return [q for q in questions if matches_show_when(q.get("show_when"), answers)]
