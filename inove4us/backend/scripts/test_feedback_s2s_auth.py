"""Auth S2S de feedbacks — sem banco."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["CRM_TRACKING_SECRET"] = "nina-test-secret"

from flask import Flask

from feedback_routes import _s2s_deny


def _status(denied):
    if denied is None:
        return None
    _resp, code = denied
    return code


def main() -> None:
    app = Flask(__name__)
    with app.test_request_context("/internal/feedbacks"):
        assert _status(_s2s_deny()) == 401
    with app.test_request_context(
        "/internal/feedbacks", headers={"x-crm-secret": "errado"}
    ):
        assert _status(_s2s_deny()) == 401
    with app.test_request_context(
        "/internal/feedbacks", headers={"x-crm-secret": "nina-test-secret"}
    ):
        assert _s2s_deny() is None
    os.environ["CRM_TRACKING_SECRET"] = ""
    with app.test_request_context(
        "/internal/feedbacks", headers={"x-crm-secret": "nina-test-secret"}
    ):
        assert _status(_s2s_deny()) == 503
    print("test_feedback_s2s_auth.py ok")


if __name__ == "__main__":
    main()
