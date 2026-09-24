"""146 — idempotência, aceite e preferência do resumo."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from onboarding_mail import b2c_handled  # noqa: E402


def test_b2c_handled_exige_sent():
    ok = {
        "ok": True,
        "response": '{"result":{"handled":true,"sent":true}}',
    }
    assert b2c_handled(ok) is True
    assert b2c_handled({"ok": True, "response": '{"result":{"handled":false}}'}) is False
    assert b2c_handled({"ok": False, "response": '{"result":{"handled":true,"sent":true}}'}) is False
    assert b2c_handled({"ok": True, "response": '{"result":{"handled":true,"sent":false}}'}) is False


def test_run_job_idempotente_e_para_no_aceite():
    from onboarding_mail import run_job

    calls = []

    def fake_dispatch(event, payload):
        calls.append((event, payload.get("email")))
        return {
            "ok": True,
            "response": '{"result":{"handled":true,"sent":true}}',
        }

    teachers_pendente = [
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "email": "prof@example.com",
            "instituicao_id": "e9aeac41-55aa-4eab-b223-f9f03be2fea0",
            "escola": "Helenita",
            "disciplinas": "História",
            "nome": "Prof",
        }
    ]

    class FakeCur:
        def __init__(self):
            self.claims = set()
            self.released = []

        def execute(self, sql, params=None):
            self.sql = sql
            self.params = params

        def fetchone(self):
            if "INSERT INTO public.school_onboarding_mail_log" in (self.sql or ""):
                key = tuple(self.params)
                if key in self.claims:
                    return None
                self.claims.add(key)
                return {"id": "ok"}
            return None

        def fetchall(self):
            return []

    fake_cur = FakeCur()

    class FakeConn:
        def cursor(self, **kwargs):
            class Ctx:
                def __enter__(self_inner):
                    return fake_cur

                def __exit__(self_inner, *a):
                    return False

            return Ctx()

        def commit(self):
            return None

    with patch("onboarding_mail.get_conn") as gc, patch(
        "onboarding_mail.pending_teachers", return_value=teachers_pendente
    ), patch("onboarding_mail.digest_gestores", return_value=[]), patch(
        "onboarding_mail.dispatch_teacher",
        side_effect=lambda row: fake_dispatch("TEACHER_INVITE_REMINDER", row),
    ), patch("onboarding_mail.dispatch_digest"):
        gc.return_value.__enter__.return_value = FakeConn()
        gc.return_value.__exit__.return_value = False
        first = run_job(control=False, allowlist=None, dry_run=False)
        second = run_job(control=False, allowlist=None, dry_run=False)

    assert first["teachers"][0]["status"] == "sent"
    assert second["teachers"][0]["status"] == "already_sent"
    assert len(calls) == 1

    with patch("onboarding_mail.get_conn") as gc, patch(
        "onboarding_mail.pending_teachers", return_value=[]
    ), patch("onboarding_mail.digest_gestores", return_value=[]), patch(
        "onboarding_mail.dispatch_teacher"
    ) as dt:
        gc.return_value.__enter__.return_value = FakeConn()
        gc.return_value.__exit__.return_value = False
        third = run_job(control=False, allowlist=None, dry_run=False)
    assert third["teachers"] == []
    dt.assert_not_called()


if __name__ == "__main__":
    test_b2c_handled_exige_sent()
    test_run_job_idempotente_e_para_no_aceite()
    print("ok")
