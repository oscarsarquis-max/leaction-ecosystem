"""146 — e-mails diários de onboarding (lembrete professor + resumo gestor).

Job no EC2 do School (crontab 08:00 America/Sao_Paulo), mesmo host do snapshot.
Envio via ponte School → Inove → SES (eventos TEACHER_INVITE_REMINDER e
SCHOOL_GESTOR_DAILY_DIGEST).

Idempotência: INSERT em school_onboarding_mail_log (unique kind+email+inst+dia)
antes de despachar. Falha no B2C solta o claim (DELETE) para retry.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
import json

try:
    from zoneinfo import ZoneInfo

    TZ = ZoneInfo("America/Sao_Paulo")
except Exception:
    TZ = timezone(timedelta(hours=-3))

from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
load_dotenv(Path(__file__).resolve().parent / ".env")

from db import get_conn  # noqa: E402

logger = logging.getLogger("onboarding_mail")

KIND_TEACHER = "teacher_reminder"
KIND_DIGEST = "gestor_digest"
CONTROL_EMAIL = "oscar@oscarsarquis.com.br"
SEED_INSTITUICOES = {
    "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50",  # escola teste / homologação
    "736c53fc-2f3a-41aa-9a6b-fd642da6d1dc",  # unlock-verify
}
SKIP_EMAIL_DOMAINS = ("escolateste.edu.br", "example.com")

ETAPAS = [
    (1, "contratou", "Contratou"),
    (2, "gestor_login", "Gestor fez o primeiro login"),
    (3, "senha_alterar", "Gestor alterou a senha temporária"),
    (4, "criou_turmas", "Criou turmas"),
    (5, "cadastrou_alunos", "Cadastrou alunos"),
    (6, "convidou_professores", "Convidou professores"),
    (7, "professores_aceitaram", "Professores aceitaram"),
    (8, "professores_usaram", "Professores usaram"),
    (9, "uso_recorrente", "Uso recorrente"),
]


def hoje_sp() -> str:
    return datetime.now(TZ).date().isoformat()


def parse_allowlist(raw: str | None) -> set[str]:
    out = set()
    for part in str(raw or "").split(","):
        email = part.strip().lower()
        if email and "@" in email:
            out.add(email)
    return out


def control_mode(explicit: bool | None = None) -> bool:
    if explicit is not None:
        return bool(explicit)
    flag = (os.getenv("ONBOARDING_MAIL_CONTROL") or "").strip().lower()
    return flag in ("1", "true", "yes", "on")


def allowlist_from_env() -> set[str]:
    listed = parse_allowlist(os.getenv("ONBOARDING_MAIL_ALLOWLIST"))
    if control_mode() and not listed:
        return {CONTROL_EMAIL}
    return listed


def instituicoes_from_env() -> set[str] | None:
    raw = (os.getenv("ONBOARDING_MAIL_INSTITUICOES") or "").strip()
    if not raw:
        return None
    out = {part.strip().lower() for part in raw.split(",") if part.strip()}
    return out or None


def skip_test_recipient(email: str, instituicao_id: str | None) -> bool:
    inst = str(instituicao_id or "").strip().lower()
    if inst in SEED_INSTITUICOES:
        return True
    allowed = instituicoes_from_env()
    if allowed is not None and inst not in allowed:
        return True
    domain = (email or "").split("@")[-1].lower()
    return domain in SKIP_EMAIL_DOMAINS


def _nome_de_email(email: str) -> str:
    local = (email or "").split("@", 1)[0].replace(".", " ").replace("_", " ").strip()
    return local.title() if local else "professor(a)"


def _invite_url(email: str) -> str:
    frontend = (
        os.getenv("INOVE4US_B2C_FRONTEND_URL")
        or os.getenv("INOVE4US_FRONTEND_URL")
        or "https://inove4us.com.br"
    ).rstrip("/")
    return f"{frontend}/acesso?email={email}&school_invite=1"


def _school_panel_url() -> str:
    return (
        os.getenv("FRONTEND_ORIGIN")
        or os.getenv("CORS_ORIGINS")
        or "https://school.inove4us.com.br"
    ).split(",")[0].strip().rstrip("/") or "https://school.inove4us.com.br"


def claim_send(
    cur,
    *,
    kind: str,
    email: str,
    instituicao_id: str,
    ref_id: str | None,
    sent_on: str,
) -> bool:
    """True se este processo ganhou o slot do dia (pode enviar)."""
    cur.execute(
        """
        INSERT INTO public.school_onboarding_mail_log
            (kind, recipient_email, instituicao_id, ref_id, sent_on)
        VALUES (%s, %s, %s::uuid, %s, %s::date)
        ON CONFLICT (kind, recipient_email, instituicao_id, sent_on)
        DO NOTHING
        RETURNING id
        """,
        (kind, email, instituicao_id, ref_id, sent_on),
    )
    return cur.fetchone() is not None


def release_claim(cur, *, kind: str, email: str, instituicao_id: str, sent_on: str) -> None:
    cur.execute(
        """
        DELETE FROM public.school_onboarding_mail_log
         WHERE kind = %s
           AND recipient_email = %s
           AND instituicao_id = %s::uuid
           AND sent_on = %s::date
        """,
        (kind, email, instituicao_id, sent_on),
    )


def fetch_pos_venda(instituicao_id: str) -> dict[str, Any] | None:
    """S2S no Hub (mesmo secret do snapshot). 404/falha → None."""
    import requests

    secret = (os.getenv("CRM_TRACKING_SECRET") or "").strip()
    base = (
        os.getenv("ACTION_HUB_API_URL")
        or os.getenv("HUB_API_URL")
        or "http://127.0.0.1:4001"
    ).rstrip("/")
    if not secret:
        return None
    url = f"{base}/api/crm/contas/{instituicao_id}/pos-venda"
    try:
        resp = requests.get(url, headers={"x-crm-secret": secret}, timeout=8)
    except requests.RequestException as exc:
        logger.warning("pos-venda indisponível: %s", exc)
        return None
    if resp.status_code != 200:
        logger.warning("pos-venda HTTP %s", resp.status_code)
        return None
    try:
        data = resp.json()
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def local_digest(cur, instituicao_id: str) -> dict[str, Any]:
    cur.execute(
        """
        SELECT razao_social
          FROM public.school_instituicoes
         WHERE id = %s::uuid
        """,
        (instituicao_id,),
    )
    inst = cur.fetchone() or {}
    cur.execute(
        "SELECT COUNT(*)::int AS n FROM public.school_turmas WHERE instituicao_id = %s::uuid",
        (instituicao_id,),
    )
    turmas = int((cur.fetchone() or {}).get("n") or 0)
    cur.execute(
        """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
             WHERE table_schema = 'public' AND table_name = 'school_alunos'
        )
        """
    )
    if (cur.fetchone() or {}).get("exists"):
        cur.execute(
            "SELECT COUNT(*)::int AS n FROM public.school_alunos WHERE instituicao_id = %s::uuid",
            (instituicao_id,),
        )
        alunos = int((cur.fetchone() or {}).get("n") or 0)
    else:
        alunos = 0
    cur.execute(
        """
        SELECT COUNT(*) FILTER (WHERE status_vinculo = 'pendente')::int AS pendente,
               COUNT(*) FILTER (WHERE status_vinculo = 'ativo')::int AS ativo,
               COUNT(*)::int AS total
          FROM public.school_professores_vinculo
         WHERE instituicao_id = %s::uuid
        """,
        (instituicao_id,),
    )
    v = cur.fetchone() or {}
    cur.execute(
        """
        SELECT total_assentos
          FROM public.school_licencas
         WHERE instituicao_id = %s::uuid
         LIMIT 1
        """,
        (instituicao_id,),
    )
    lic = cur.fetchone() or {}
    cur.execute(
        """
        SELECT COUNT(*) FILTER (WHERE updated_at IS DISTINCT FROM created_at)::int AS trocou
          FROM public.school_gestores
         WHERE instituicao_id = %s::uuid AND ativo IS TRUE
        """,
        (instituicao_id,),
    )
    senha = int((cur.fetchone() or {}).get("trocou") or 0) > 0

    feitos = {
        "contratou": True,
        "gestor_login": False,
        "senha_alterar": senha,
        "criou_turmas": turmas > 0,
        "cadastrou_alunos": alunos > 0,
        "convidou_professores": int(v.get("total") or 0) > 0,
        "professores_aceitaram": int(v.get("ativo") or 0) > 0,
        "professores_usaram": False,
        "uso_recorrente": False,
    }
    etapa_atual = 0
    rotulo = "—"
    for n, chave, label in ETAPAS:
        if feitos.get(chave):
            etapa_atual = n
            rotulo = label
    aceitos = int(v.get("ativo") or 0)
    return {
        "escola": inst.get("razao_social") or "sua escola",
        "etapa_atual": etapa_atual,
        "etapa_rotulo": rotulo,
        "aceitos": aceitos,
        "convidados": int(v.get("total") or 0),
        "usando": 0,
        "licencas_uso": aceitos,
        "licencas_total": int(lic.get("total_assentos") or 0),
        "dias_ativos_7": 0,
        "fonte": "school",
    }


def merge_digest(local: dict[str, Any], hub: dict[str, Any] | None) -> dict[str, Any]:
    if not hub:
        return local
    etapa = hub.get("etapa_atual")
    etapas = hub.get("etapas") if isinstance(hub.get("etapas"), dict) else {}
    rotulo = local["etapa_rotulo"]
    if isinstance(etapa, int) and 1 <= etapa <= 9:
        rotulo = ETAPAS[etapa - 1][2]
        atual = etapas.get(ETAPAS[etapa - 1][1]) if etapas else None
        if isinstance(atual, dict) and atual.get("rotulo"):
            rotulo = str(atual["rotulo"])
        local["etapa_atual"] = etapa
        local["etapa_rotulo"] = rotulo
    prof = hub.get("professores") if isinstance(hub.get("professores"), dict) else {}
    lic = hub.get("licencas") if isinstance(hub.get("licencas"), dict) else {}
    if prof:
        local["aceitos"] = int(prof.get("aceitos") or local["aceitos"])
        local["convidados"] = int(prof.get("convidados") or local["convidados"])
        local["usando"] = int(prof.get("usando") or 0)
    if lic:
        local["licencas_uso"] = int(lic.get("em_uso") if lic.get("em_uso") is not None else local["licencas_uso"])
        local["licencas_total"] = int(lic.get("total") if lic.get("total") is not None else local["licencas_total"])
    if hub.get("dias_ativos_7") is not None:
        local["dias_ativos_7"] = int(hub.get("dias_ativos_7") or 0)
    elif isinstance(hub.get("uso"), dict) and hub["uso"].get("dias_ativos_7") is not None:
        local["dias_ativos_7"] = int(hub["uso"]["dias_ativos_7"] or 0)
    local["fonte"] = "sponge"
    return local


def pending_teachers(cur, allowlist: set[str] | None) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT v.id, v.email_convite, v.instituicao_id::text,
               i.razao_social AS escola,
               (
                 SELECT string_agg(DISTINCT d.nome, ', ' ORDER BY d.nome)
                   FROM public.school_alocacoes_docentes a
                   JOIN public.school_disciplinas d ON d.id = a.disciplina_id
                  WHERE a.professor_vinculo_id = v.id
                    AND a.ativo IS TRUE
               ) AS disciplinas
          FROM public.school_professores_vinculo v
          JOIN public.school_instituicoes i ON i.id = v.instituicao_id
         WHERE v.status_vinculo = 'pendente'
           AND v.email_convite IS NOT NULL
           AND BTRIM(v.email_convite) <> ''
         ORDER BY i.razao_social, v.email_convite
        """
    )
    rows = []
    for raw in cur.fetchall() or []:
        email = str(raw.get("email_convite") or "").strip().lower()
        if allowlist is not None and email not in allowlist:
            continue
        if skip_test_recipient(email, raw.get("instituicao_id")):
            continue
        rows.append(
            {
                "id": str(raw["id"]),
                "email": email,
                "instituicao_id": str(raw["instituicao_id"]),
                "escola": raw.get("escola") or "sua escola",
                "disciplinas": raw.get("disciplinas") or "sua turma",
                "nome": _nome_de_email(email),
            }
        )
    return rows


def digest_gestores(cur, allowlist: set[str] | None) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT g.id::text, g.nome, g.email, g.instituicao_id::text,
               i.razao_social AS escola,
               g.recebe_resumo_diario
          FROM public.school_gestores g
          JOIN public.school_instituicoes i ON i.id = g.instituicao_id
          JOIN public.school_licencas l ON l.instituicao_id = g.instituicao_id
         WHERE g.ativo IS TRUE
         ORDER BY i.razao_social, g.email
        """
    )
    rows = []
    for raw in cur.fetchall() or []:
        email = str(raw.get("email") or "").strip().lower()
        if allowlist is not None and email not in allowlist:
            continue
        if not raw.get("recebe_resumo_diario"):
            continue
        if skip_test_recipient(email, raw.get("instituicao_id")):
            continue
        rows.append(
            {
                "id": raw["id"],
                "nome": raw.get("nome") or _nome_de_email(email),
                "email": email,
                "instituicao_id": raw["instituicao_id"],
                "escola": raw.get("escola") or "sua escola",
            }
        )
    return rows


def b2c_handled(push: dict[str, Any]) -> bool:
    if not push.get("ok"):
        return False
    raw = push.get("response") or ""
    try:
        body = json.loads(raw) if isinstance(raw, str) else raw
    except ValueError:
        return False
    if not isinstance(body, dict):
        return False
    result = body.get("result") if isinstance(body.get("result"), dict) else {}
    return bool(result.get("handled")) and bool(result.get("sent", True))


def dispatch_teacher(row: dict[str, Any]) -> dict[str, Any]:
    from b2c_integration_service import dispatch_event_to_b2c

    return dispatch_event_to_b2c(
        "TEACHER_INVITE_REMINDER",
        {
            "email": row["email"],
            "nome": row["nome"],
            "instituicao_id": row["instituicao_id"],
            "instituicao_nome": row["escola"],
            "disciplina": row["disciplinas"],
            "invite_url": _invite_url(row["email"]),
        },
    )


def dispatch_digest(gestor: dict[str, Any], digest: dict[str, Any]) -> dict[str, Any]:
    from b2c_integration_service import dispatch_event_to_b2c

    return dispatch_event_to_b2c(
        "SCHOOL_GESTOR_DAILY_DIGEST",
        {
            "email": gestor["email"],
            "nome": gestor["nome"],
            "instituicao_id": gestor["instituicao_id"],
            "instituicao_nome": digest["escola"],
            "etapa_atual": digest["etapa_atual"],
            "etapa_rotulo": digest["etapa_rotulo"],
            "aceitos": digest["aceitos"],
            "convidados": digest["convidados"],
            "usando": digest["usando"],
            "licencas_uso": digest["licencas_uso"],
            "licencas_total": digest["licencas_total"],
            "dias_ativos_7": digest["dias_ativos_7"],
            "painel_url": _school_panel_url(),
        },
    )


def run_job(
    *,
    control: bool | None = None,
    allowlist: set[str] | None = None,
    dry_run: bool = False,
    preview_teacher: bool = False,
) -> dict[str, Any]:
    use_control = control_mode(control)
    if allowlist is not None:
        filter_emails = allowlist
    elif use_control:
        filter_emails = allowlist_from_env()
    else:
        filter_emails = None
    sent_on = hoje_sp()
    report: dict[str, Any] = {
        "ok": True,
        "sent_on": sent_on,
        "control": use_control,
        "allowlist": sorted(filter_emails or []),
        "dry_run": dry_run,
        "teachers": [],
        "gestores": [],
    }

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            teachers = pending_teachers(cur, filter_emails)
            if preview_teacher and filter_emails:
                pending_emails = {t["email"] for t in teachers}
                sample = teachers[0] if teachers else None
                if sample is None:
                    cur.execute(
                        """
                        SELECT id::text, razao_social
                          FROM public.school_instituicoes
                         ORDER BY created_at DESC
                         LIMIT 1
                        """
                    )
                    inst = cur.fetchone() or {}
                    sample = {
                        "escola": inst.get("razao_social") or "sua escola",
                        "disciplinas": "sua turma",
                        "instituicao_id": inst.get("id"),
                    }
                for email in sorted(filter_emails):
                    if email in pending_emails:
                        continue
                    teachers.append(
                        {
                            "id": None,
                            "email": email,
                            "instituicao_id": sample.get("instituicao_id"),
                            "escola": sample.get("escola") or "sua escola",
                            "disciplinas": sample.get("disciplinas") or "sua turma",
                            "nome": _nome_de_email(email),
                            "preview": True,
                        }
                    )
            for row in teachers:
                if not row.get("instituicao_id"):
                    report["teachers"].append({"email": row["email"], "status": "skip_no_inst"})
                    continue
                item = {
                    "email": row["email"],
                    "instituicao_id": row["instituicao_id"],
                    "preview": bool(row.get("preview")),
                }
                if dry_run:
                    item["status"] = "dry_run"
                    report["teachers"].append(item)
                    continue
                won = claim_send(
                    cur,
                    kind=KIND_TEACHER,
                    email=row["email"],
                    instituicao_id=row["instituicao_id"],
                    ref_id=row.get("id"),
                    sent_on=sent_on,
                )
                if not won:
                    item["status"] = "already_sent"
                    report["teachers"].append(item)
                    continue
                push = dispatch_teacher(row)
                if not b2c_handled(push):
                    release_claim(
                        cur,
                        kind=KIND_TEACHER,
                        email=row["email"],
                        instituicao_id=row["instituicao_id"],
                        sent_on=sent_on,
                    )
                    item["status"] = "failed"
                    item["error"] = push.get("error") or push.get("response")
                    report["ok"] = False
                else:
                    item["status"] = "sent"
                report["teachers"].append(item)

            gestores = digest_gestores(cur, filter_emails)
            digest_cache: dict[str, dict[str, Any]] = {}
            for g in gestores:
                item = {"email": g["email"], "instituicao_id": g["instituicao_id"]}
                if dry_run:
                    item["status"] = "dry_run"
                    report["gestores"].append(item)
                    continue
                won = claim_send(
                    cur,
                    kind=KIND_DIGEST,
                    email=g["email"],
                    instituicao_id=g["instituicao_id"],
                    ref_id=g["id"],
                    sent_on=sent_on,
                )
                if not won:
                    item["status"] = "already_sent"
                    report["gestores"].append(item)
                    continue
                inst = g["instituicao_id"]
                if inst not in digest_cache:
                    digest_cache[inst] = merge_digest(
                        local_digest(cur, inst),
                        fetch_pos_venda(inst),
                    )
                    digest_cache[inst]["escola"] = g["escola"]
                push = dispatch_digest(g, digest_cache[inst])
                if not b2c_handled(push):
                    release_claim(
                        cur,
                        kind=KIND_DIGEST,
                        email=g["email"],
                        instituicao_id=inst,
                        sent_on=sent_on,
                    )
                    item["status"] = "failed"
                    item["error"] = push.get("error") or push.get("response")
                    report["ok"] = False
                else:
                    item["status"] = "sent"
                    item["etapa"] = digest_cache[inst]["etapa_atual"]
                report["gestores"].append(item)
            conn.commit()
    return report


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="[onboarding-mail] %(message)s")
    parser = argparse.ArgumentParser(description="Job diário de e-mails de onboarding")
    parser.add_argument("--control", action="store_true", help="Só allowlist (Oscar)")
    parser.add_argument("--allowlist", default="", help="e-mails separados por vírgula")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--preview-teacher",
        action="store_true",
        help="Envia o lembrete de professor também aos e-mails da allowlist (teste de controle)",
    )
    args = parser.parse_args(argv)
    listed = parse_allowlist(args.allowlist) or None
    report = run_job(
        control=True if args.control else None,
        allowlist=listed,
        dry_run=args.dry_run,
        preview_teacher=args.preview_teacher,
    )
    print(report)
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
