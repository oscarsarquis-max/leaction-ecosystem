"""Provisionamento self-serve School a partir do webhook LICENSES_GRANTED.

Idempotente por order_id. E-mail de credencial é fail-soft (depois do commit).
"""
from __future__ import annotations

import os
import secrets
import string
import sys
import uuid
from typing import Any

from psycopg2 import IntegrityError
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash

from db import get_conn

def _as_uuid(value: Any) -> str | None:
    if value is None or value == "":
        return None
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        return None


def licenses_qty(payload: dict) -> int:
    for key in (
        "licenses_granted",
        "licenses",
        "licencas",
        "seats",
        "quantity",
        "quantidade",
    ):
        if key in payload and payload[key] is not None:
            try:
                n = int(payload[key])
                if n > 0:
                    return n
            except (TypeError, ValueError):
                pass
    direitos = payload.get("direitos") or payload.get("entitlements") or {}
    if isinstance(direitos, dict):
        for key in ("licenses_granted", "licenses", "licencas", "seats"):
            if key in direitos and direitos[key] is not None:
                try:
                    n = int(direitos[key])
                    if n > 0:
                        return n
                except (TypeError, ValueError):
                    pass
    items = payload.get("items")
    if isinstance(items, list):
        total = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            itype = str(item.get("item_type") or "").lower()
            if itype in ("seat", "addon", "plan"):
                try:
                    total += max(0, int(item.get("quantity") or 0))
                except (TypeError, ValueError):
                    pass
        if total > 0:
            return total
    return 0


def resolve_instituicao_id(payload: dict) -> str | None:
    for key in ("instituicao_id", "institution_id", "school_id"):
        found = _as_uuid(payload.get(key))
        if found:
            return found
    subject_type = str(payload.get("subject_type") or "").strip().lower()
    subject = payload.get("subject_id")
    if subject_type in ("instituicao", "institution", "school"):
        return _as_uuid(subject)
    return _as_uuid(subject)

ZONAS = ("administrativo", "operacional", "pedagogico")


def _log(msg: str) -> None:
    print(f"[selfserve] {msg}", flush=True)


def only_digits(value: Any) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def format_cnpj(raw: Any) -> str | None:
    d = only_digits(raw)
    if len(d) != 14:
        return None
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:14]}"


def generate_temp_password() -> str:
    alphabet = string.ascii_letters + string.digits
    return "I4u-" + "".join(secrets.choice(alphabet) for _ in range(12))


def acesso_url() -> str:
    origin = (
        os.getenv("FRONTEND_ORIGIN")
        or (os.getenv("CORS_ORIGINS") or "").split(",")[0].strip()
        or "https://school.inove4us.com.br"
    ).rstrip("/")
    return f"{origin}/acesso"


def _order_id(payload: dict) -> str | None:
    raw = str(payload.get("order_id") or "").strip()
    return raw or None


def _doc_tipo(payload: dict) -> str | None:
    tipo = str(payload.get("payer_document_type") or "").strip().lower()
    return tipo if tipo in ("cnpj", "cpf") else None


def count_professores_ativos(cur: Any, instituicao_id: str) -> int:
    cur.execute(
        """
        SELECT count(*)::int AS n
        FROM public.school_professores_vinculo
        WHERE instituicao_id = %s AND status_vinculo = 'ativo'
        """,
        (instituicao_id,),
    )
    row = cur.fetchone()
    return int(row["n"] or 0) if row else 0


def credit_licenses(
    cur: Any,
    *,
    instituicao_id: str,
    qty: int,
    sku: str | None,
    contract_id: str | None,
) -> dict[str, Any]:
    em_uso = count_professores_ativos(cur, instituicao_id)
    cur.execute(
        """
        INSERT INTO public.school_licencas (
            instituicao_id,
            total_assentos,
            assentos_em_uso,
            sku_ultimo,
            contrato_hub_id
        )
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (instituicao_id) DO UPDATE SET
            total_assentos = public.school_licencas.total_assentos + EXCLUDED.total_assentos,
            assentos_em_uso = EXCLUDED.assentos_em_uso,
            sku_ultimo = COALESCE(EXCLUDED.sku_ultimo, public.school_licencas.sku_ultimo),
            contrato_hub_id = COALESCE(
                EXCLUDED.contrato_hub_id, public.school_licencas.contrato_hub_id
            ),
            updated_at = CURRENT_TIMESTAMP
        RETURNING id, total_assentos, assentos_em_uso
        """,
        (instituicao_id, qty, em_uso, sku, contract_id),
    )
    lic = cur.fetchone()
    cur.execute(
        """
        UPDATE public.school_instituicoes
        SET licencas_contratadas = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        """,
        (int(lic["total_assentos"]), instituicao_id),
    )
    return {
        "total_assentos": int(lic["total_assentos"]),
        "assentos_em_uso": int(lic["assentos_em_uso"]),
    }


def _mark_processed(cur: Any, order_id: str, instituicao_id: str, event_type: str) -> None:
    cur.execute(
        """
        INSERT INTO public.school_hub_eventos_processados (
            order_id, instituicao_id, event_type
        ) VALUES (%s, %s, %s)
        ON CONFLICT (order_id) DO NOTHING
        """,
        (order_id, instituicao_id, event_type),
    )


def _already_processed(cur: Any, order_id: str) -> dict[str, Any] | None:
    cur.execute(
        """
        SELECT order_id, instituicao_id, event_type, processed_at
        FROM public.school_hub_eventos_processados
        WHERE order_id = %s
        """,
        (order_id,),
    )
    return cur.fetchone()


def _record_email(
    cur: Any,
    *,
    instituicao_id: str,
    order_id: str | None,
    gestor_email: str,
    status: str,
    erro: str | None,
) -> None:
    cur.execute(
        """
        INSERT INTO public.school_provisionamento_email (
            instituicao_id, order_id, gestor_email, status, erro
        ) VALUES (%s, %s, %s, %s, %s)
        """,
        (instituicao_id, order_id, gestor_email, status, (erro or "")[:1000] or None),
    )


def provision_institution(
    cur: Any,
    *,
    instituicao_id: str,
    payload: dict,
    qty: int,
    sku: str | None,
    contract_id: str | None,
) -> dict[str, Any]:
    razao = str(payload.get("razao_social") or "").strip() or "Escola inove4us"
    payer_email = str(payload.get("payer_email") or payload.get("email") or "").strip().lower()
    doc_tipo = _doc_tipo(payload)
    doc_digits = only_digits(payload.get("payer_document"))
    cnpj_oficial = format_cnpj(doc_digits) if doc_tipo == "cnpj" else None
    dominio = payer_email.split("@", 1)[1] if "@" in payer_email else None

    cur.execute("SAVEPOINT inst_ins")
    try:
        cur.execute(
            """
            INSERT INTO public.school_instituicoes (
                id, razao_social, cnpj, dominio_email, status,
                documento_responsavel_pagamento, documento_responsavel_tipo
            ) VALUES (%s, %s, %s, %s, 'ativa', %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                instituicao_id,
                razao[:255],
                cnpj_oficial,
                dominio,
                doc_digits or None,
                doc_tipo,
            ),
        )
        cur.execute("RELEASE SAVEPOINT inst_ins")
    except IntegrityError:
        cur.execute("ROLLBACK TO SAVEPOINT inst_ins")
        cur.execute(
            """
            INSERT INTO public.school_instituicoes (
                id, razao_social, cnpj, dominio_email, status,
                documento_responsavel_pagamento, documento_responsavel_tipo
            ) VALUES (%s, %s, NULL, %s, 'ativa', %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                instituicao_id,
                razao[:255],
                dominio,
                doc_digits or None,
                doc_tipo,
            ),
        )

    temp_password = None
    gestor_id = None
    if payer_email and "@" in payer_email:
        cur.execute(
            "SELECT id, instituicao_id FROM public.school_gestores WHERE lower(email) = %s",
            (payer_email,),
        )
        existing = cur.fetchone()
        same_inst = True
        if existing:
            same_inst = str(existing["instituicao_id"]) == instituicao_id
            if same_inst:
                gestor_id = str(existing["id"])
            else:
                _log(
                    f"email {payer_email} já pertence a outra instituição — gestor não recriado"
                )
        else:
            temp_password = generate_temp_password()
            nome = razao[:200] if razao else payer_email.split("@", 1)[0]
            cur.execute(
                """
                INSERT INTO public.school_gestores (
                    instituicao_id, nome, email, senha_hash, cargo, ativo
                ) VALUES (%s, %s, %s, %s, 'Diretor', TRUE)
                RETURNING id
                """,
                (
                    instituicao_id,
                    nome,
                    payer_email,
                    generate_password_hash(temp_password),
                ),
            )
            gestor_id = str(cur.fetchone()["id"])

        if gestor_id and same_inst:
            for zona in ZONAS:
                cur.execute(
                    """
                    INSERT INTO public.school_gestor_perfis (gestor_id, zona, ativo)
                    VALUES (%s, %s, TRUE)
                    ON CONFLICT (gestor_id, zona) DO UPDATE SET
                        ativo = TRUE,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (gestor_id, zona),
                )

    lic = credit_licenses(
        cur,
        instituicao_id=instituicao_id,
        qty=qty,
        sku=sku,
        contract_id=contract_id,
    )
    return {
        "created": True,
        "gestor_id": gestor_id,
        "gestor_email": payer_email or None,
        "temp_password": temp_password,
        **lic,
    }


def dispatch_credentials_email(
    *,
    instituicao_id: str,
    order_id: str | None,
    email: str,
    password: str,
    razao_social: str,
) -> dict[str, Any]:
    from b2c_integration_service import dispatch_event_to_b2c

    result = dispatch_event_to_b2c(
        "SCHOOL_GESTOR_CREDENTIALS",
        {
            "instituicao_id": instituicao_id,
            "email": email,
            "payer_email": email,
            "senha_temporaria": password,
            "acesso_url": acesso_url(),
            "razao_social": razao_social,
            "order_id": order_id,
        },
    )
    sent = bool(result.get("ok"))
    status = "enviado" if sent else "falhou"
    erro = None if sent else str(result.get("error") or result.get("response") or "b2c_mail_failed")
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                _record_email(
                    cur,
                    instituicao_id=instituicao_id,
                    order_id=order_id,
                    gestor_email=email,
                    status=status,
                    erro=erro,
                )
    except Exception as exc:
        print(f"[selfserve] falha ao registrar status do e-mail: {exc}", file=sys.stderr, flush=True)
    return {"sent": sent, "status": status, "b2c": {k: v for k, v in result.items() if k != "response"}}


def apply_licenses_granted(payload: dict, *, event_label: str) -> dict[str, Any]:
    instituicao_id = resolve_instituicao_id(payload)
    qty = licenses_qty(payload)
    sku = str(payload.get("sku") or "").strip() or None
    contract_id = str(payload.get("contract_id") or "").strip() or None
    order_id = _order_id(payload)

    if not instituicao_id:
        _log(f"{event_label} sem instituicao_id/subject_id UUID — ignorado")
        return {
            "handled": False,
            "reason": "instituicao_id_missing",
            "event": event_label,
            "http_status": 200,
        }
    if qty <= 0:
        _log(f"{event_label} instituicao={instituicao_id} qty=0 — ack sem aplicar")
        return {
            "handled": False,
            "reason": "licenses_qty_zero",
            "instituicao_id": instituicao_id,
            "event": event_label,
            "http_status": 200,
        }

    email_job: dict[str, Any] | None = None
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT pg_advisory_xact_lock(hashtext(%s))",
                    (f"school-lic:{instituicao_id}",),
                )
                if order_id:
                    done = _already_processed(cur, order_id)
                    if done:
                        _log(f"{event_label} order_id={order_id} já processado — noop")
                        return {
                            "handled": True,
                            "idempotent": True,
                            "event": event_label,
                            "instituicao_id": str(done["instituicao_id"]),
                            "order_id": order_id,
                            "http_status": 200,
                        }

                cur.execute(
                    "SELECT id FROM public.school_instituicoes WHERE id = %s",
                    (instituicao_id,),
                )
                exists = cur.fetchone()
                if exists:
                    lic = credit_licenses(
                        cur,
                        instituicao_id=instituicao_id,
                        qty=qty,
                        sku=sku,
                        contract_id=contract_id,
                    )
                    created = False
                    result_extra: dict[str, Any] = {}
                else:
                    result_extra = provision_institution(
                        cur,
                        instituicao_id=instituicao_id,
                        payload=payload,
                        qty=qty,
                        sku=sku,
                        contract_id=contract_id,
                    )
                    created = True
                    lic = {
                        "total_assentos": result_extra["total_assentos"],
                        "assentos_em_uso": result_extra["assentos_em_uso"],
                    }
                    if result_extra.get("temp_password") and result_extra.get("gestor_email"):
                        email_job = {
                            "instituicao_id": instituicao_id,
                            "order_id": order_id,
                            "email": result_extra["gestor_email"],
                            "password": result_extra["temp_password"],
                            "razao_social": str(payload.get("razao_social") or "").strip(),
                        }

                if order_id:
                    _mark_processed(cur, order_id, instituicao_id, event_label)
    except Exception as exc:
        _log(f"{event_label} erro persistindo: {exc}")
        print(f"[selfserve] {exc}", file=sys.stderr, flush=True)
        return {
            "handled": False,
            "error": str(exc),
            "event": event_label,
            "instituicao_id": instituicao_id,
            "http_status": 500,
        }

    mail_result = None
    if email_job:
        try:
            mail_result = dispatch_credentials_email(**email_job)
        except Exception as exc:
            _log(f"e-mail fail-soft: {exc}")
            mail_result = {"sent": False, "status": "falhou", "error": str(exc)}
            try:
                with get_conn() as conn:
                    with conn.cursor() as cur:
                        _record_email(
                            cur,
                            instituicao_id=email_job["instituicao_id"],
                            order_id=email_job.get("order_id"),
                            gestor_email=email_job["email"],
                            status="falhou",
                            erro=str(exc)[:1000],
                        )
            except Exception:
                pass

    _log(
        f"{event_label} instituicao={instituicao_id} +{qty} "
        f"total={lic['total_assentos']} created={created} sku={sku}"
    )
    out = {
        "handled": True,
        "event": event_label,
        "created": created,
        "instituicao_id": instituicao_id,
        "licenses_granted": qty,
        "total_assentos": lic["total_assentos"],
        "assentos_em_uso": lic["assentos_em_uso"],
        "sku": sku,
        "contract_id": contract_id,
        "order_id": order_id,
        "http_status": 200,
    }
    if mail_result is not None:
        out["email"] = {
            "status": mail_result.get("status"),
            "sent": bool(mail_result.get("sent")),
        }
    return out
