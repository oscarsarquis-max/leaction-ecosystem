#!/usr/bin/env python3
"""117 — B2C: aceite, alocações, 403 origem_school, freemium aula solta, crédito 98."""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta

import requests

BASE = "https://inove4us.com.br"
HOMOLOG = "homologador@leaction.com.br"
SOLO = "inovador@inove4us.com.br"
TEST_EMAIL = "varredura117@leaction.com.br"
INST = "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50"
MARKER = "[TESTE VARREDURA 117]"


def login(email: str):
    s = requests.Session()
    r = s.post(f"{BASE}/api/auth/check-email", json={"email": email}, timeout=30)
    data = r.json() if r.content else {}
    return s, r.status_code, data


def slim_user(u: dict) -> dict:
    u = u or {}
    user = u.get("user") or u
    return {
        "id_clie": user.get("id_clie"),
        "mail_clie": user.get("mail_clie"),
        "is_institutional": user.get("is_institutional"),
        "instituicao_b2b_id": user.get("instituicao_b2b_id"),
        "institutional_name": user.get("institutional_name"),
        "creditos_ia": user.get("creditos_ia"),
        "status": u.get("status"),
    }


def main():
    out = {}
    health = requests.get(f"{BASE}/api/health", timeout=20)
    hj = health.json() if health.content else {}
    out["health"] = {
        "http": health.status_code,
        "ok": hj.get("ok") or hj.get("status"),
        "git_sha": hj.get("git_sha") or hj.get("sha"),
    }

    s_h, http_h, auth_h = login(HOMOLOG)
    out["login_homologador"] = {"http": http_h, "user": slim_user(auth_h)}
    me = s_h.get(f"{BASE}/api/auth/me", timeout=20)
    mej = me.json() if me.content else {}
    out["me_homologador"] = slim_user(mej)

    # 1.2 aceite (replay — já vinculado)
    acc1 = s_h.post(
        f"{BASE}/api/school/aceitar-convite",
        json={"instituicao_id": INST, "email": HOMOLOG},
        timeout=30,
    )
    a1 = acc1.json() if acc1.content else {}
    pool1 = (a1.get("result") or {}).get("ia_pool") or a1.get("ia_pool") or {}
    out["aceite_replay_1"] = {
        "http": acc1.status_code,
        "ok": a1.get("ok"),
        "error": a1.get("error") or a1.get("reason"),
        "school_ack": (a1.get("result") or {}).get("school_ack"),
        "ia_pool": pool1,
        "creditos_ia": (a1.get("user") or {}).get("creditos_ia"),
        "is_institutional": (a1.get("user") or {}).get("is_institutional"),
    }
    acc2 = s_h.post(
        f"{BASE}/api/school/aceitar-convite",
        json={"instituicao_id": INST, "email": HOMOLOG},
        timeout=30,
    )
    a2 = acc2.json() if acc2.content else {}
    pool2 = (a2.get("result") or {}).get("ia_pool") or a2.get("ia_pool") or {}
    out["aceite_replay_2"] = {
        "http": acc2.status_code,
        "ok": a2.get("ok"),
        "ia_pool": pool2,
        "creditos_ia": (a2.get("user") or {}).get("creditos_ia"),
        "credits_nao_duplicou": int(pool2.get("credits_added") or 0) == 0
        or pool2.get("idempotent") is True
        or pool2.get("reason") == "already_granted",
    }

    # 1.3 alocações
    al = s_h.get(f"{BASE}/api/me/alocacoes-escola", timeout=20)
    alb = al.json() if al.content else {}
    items = alb.get("alocacoes") or []
    out["alocacoes"] = {
        "http": al.status_code,
        "count": alb.get("count") if alb.get("count") is not None else len(items),
        "amostra": [
            {
                "id": i.get("id"),
                "turma_nome": i.get("turma_nome"),
                "disciplina_nome": i.get("disciplina_nome"),
                "curso_nome": i.get("curso_nome"),
                "periodo_nome": i.get("periodo_nome"),
                "instituicao_nome": i.get("instituicao_nome"),
                "school_alocacao_id": i.get("school_alocacao_id"),
                "ativo": i.get("ativo"),
            }
            for i in items[:8]
        ],
    }

    # 1.5 403 origem_school — cursos + instituições
    cursos = s_h.get(f"{BASE}/api/me/cursos", timeout=20)
    cj = cursos.json() if cursos.content else {}
    curso_list = cj if isinstance(cj, list) else (cj.get("cursos") or cj.get("items") or [])
    insts = s_h.get(f"{BASE}/api/instituicoes", timeout=20)
    ij = insts.json() if insts.content else {}
    inst_list = ij if isinstance(ij, list) else (ij.get("instituicoes") or ij.get("items") or [])
    out["cursos_list"] = {
        "http": cursos.status_code,
        "n": len(curso_list) if isinstance(curso_list, list) else None,
        "amostra": [
            {
                "id": x.get("id"),
                "nome": x.get("nome"),
                "origem_school": x.get("origem_school"),
                "school_curso_id": x.get("school_curso_id"),
            }
            for x in (curso_list or [])[:6]
            if isinstance(x, dict)
        ],
    }
    out["instituicoes_list"] = {
        "http": insts.status_code,
        "n": len(inst_list) if isinstance(inst_list, list) else None,
        "amostra": [
            {
                "id": x.get("id"),
                "nome": x.get("nome"),
                "origem_school": x.get("origem_school"),
                "school_instituicao_id": x.get("school_instituicao_id"),
            }
            for x in (inst_list or [])[:6]
            if isinstance(x, dict)
        ],
    }
    forbid = {}
    school_curso = next(
        (
            x
            for x in (curso_list or [])
            if isinstance(x, dict) and (x.get("origem_school") or x.get("school_curso_id"))
        ),
        (curso_list or [None])[0] if curso_list else None,
    )
    if isinstance(school_curso, dict) and school_curso.get("id"):
        put_c = s_h.put(
            f"{BASE}/api/cursos/{school_curso['id']}",
            json={"nome": f"{MARKER} nao deve gravar"},
            timeout=20,
        )
        pb = put_c.json() if put_c.content else {}
        forbid["put_curso"] = {
            "http": put_c.status_code,
            "code": pb.get("code"),
            "error": pb.get("error"),
            "curso_id": school_curso.get("id"),
            "origem_school": school_curso.get("origem_school"),
        }
    school_inst = next(
        (
            x
            for x in (inst_list or [])
            if isinstance(x, dict) and (x.get("origem_school") or x.get("school_instituicao_id"))
        ),
        (inst_list or [None])[0] if inst_list else None,
    )
    if isinstance(school_inst, dict) and school_inst.get("id"):
        put_i = s_h.put(
            f"{BASE}/api/instituicoes/{school_inst['id']}",
            json={"nome": f"{MARKER} nao deve gravar"},
            timeout=20,
        )
        pib = put_i.json() if put_i.content else {}
        forbid["put_instituicao"] = {
            "http": put_i.status_code,
            "code": pib.get("code"),
            "error": pib.get("error"),
            "inst_id": school_inst.get("id"),
        }
    post_i = s_h.post(
        f"{BASE}/api/instituicoes",
        json={"nome": f"{MARKER} instituicao"},
        timeout=20,
    )
    pib2 = post_i.json() if post_i.content else {}
    forbid["post_instituicao"] = {
        "http": post_i.status_code,
        "code": pib2.get("code"),
        "error": pib2.get("error"),
    }
    out["trava_403"] = forbid

    # 1.6 freemium: aula solta sem vínculo pedagógico obrigatório
    dia = (date.today() + timedelta(days=1)).isoformat()
    plan = s_h.post(
        f"{BASE}/api/daily/planejar",
        json={
            "data_planejada": dia,
            "tema_aula": f"{MARKER} aula solta",
            "origem": "manual",
            "tipo_registro": "aula",
        },
        timeout=30,
    )
    pj = plan.json() if plan.content else {}
    aula_id = pj.get("id") or (pj.get("aula") or {}).get("id") or pj.get("aula_id")
    out["aula_solta"] = {
        "http": plan.status_code,
        "success": pj.get("success"),
        "error": pj.get("error"),
        "code": pj.get("code"),
        "aula_id": aula_id,
        "keys": list(pj.keys())[:20],
    }
    if aula_id:
        dlt = s_h.delete(f"{BASE}/api/daily/{aula_id}", timeout=20)
        out["aula_solta_delete"] = {"http": dlt.status_code}

    # e-mail de teste (ainda não cadastrado?)
    s_t, http_t, auth_t = login(TEST_EMAIL)
    out["login_teste"] = {"http": http_t, "body": {k: auth_t.get(k) for k in ("status", "email", "message", "error")}}

    # aceite do convite novo com sessão do TESTE — só se granted
    if auth_t.get("status") == "granted":
        acc_t = s_t.post(
            f"{BASE}/api/school/aceitar-convite",
            json={"instituicao_id": INST, "email": TEST_EMAIL},
            timeout=30,
        )
        at = acc_t.json() if acc_t.content else {}
        out["aceite_teste"] = {
            "http": acc_t.status_code,
            "ok": at.get("ok"),
            "error": at.get("error") or at.get("reason"),
            "ia_pool": (at.get("result") or {}).get("ia_pool"),
            "school_ack": (at.get("result") or {}).get("school_ack"),
        }
        al_t = s_t.get(f"{BASE}/api/me/alocacoes-escola", timeout=20)
        alt = al_t.json() if al_t.content else {}
        out["alocacoes_teste"] = {"http": al_t.status_code, "count": alt.get("count"), "n": len(alt.get("alocacoes") or [])}
    else:
        out["aceite_teste"] = {"skipped": "email_sem_conta_granted", "status": auth_t.get("status")}

    # solo intacto (não convidar)
    s_s, http_s, auth_s = login(SOLO)
    me_s = s_s.get(f"{BASE}/api/auth/me", timeout=20)
    ms = me_s.json() if me_s.content else {}
    out["solo_intacto"] = {
        "login_http": http_s,
        "user": slim_user(ms if ms.get("user") or ms.get("id_clie") else auth_s),
    }

    # billing institucional ainda bloqueado (98)
    bill = s_h.post(f"{BASE}/api/billing/checkout", json={"sku": "golive-50"}, timeout=20)
    bj = bill.json() if bill.content else {}
    out["billing_institucional"] = {
        "http": bill.status_code,
        "code": bj.get("code"),
        "error": bj.get("error"),
    }

    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
