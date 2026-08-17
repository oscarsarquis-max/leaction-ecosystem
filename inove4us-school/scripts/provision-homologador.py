#!/usr/bin/env python3
"""Provisiona homologador School + convite Inove (idempotente).

Padrão: suiane@inove4us.com.br na Escola Teste, 3 zonas RBAC (full School),
registro em school_homologadores (escopo=proprio), vínculo professor + TEACHER_INVITE
e alocação em turma/disciplina de teste.

Uso (host School / prod):
  cd /var/www/inove4us-school
  PYTHONPATH=backend backend/.venv/bin/python scripts/provision-homologador.py

Env opcional:
  HOMOLOG_EMAIL  (default suianyholanda@gmail.com)
  HOMOLOG_NOME   (default Suiany)
  HOMOLOG_DOMAIN_INST (default escolateste.edu.br)
  HOMOLOG_PASSWORD  (opcional; se omitido gera I4u-…)
  HOMOLOG_SEND_EMAIL  (default 1) — envia 1 e-mail SES via Inove
    com senha School + link Inove
"""
from __future__ import annotations

import hashlib
from urllib.parse import quote
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from psycopg2.extras import RealDictCursor  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

from b2c_integration_service import (  # noqa: E402
    dispatch_event_to_b2c,
    dispatch_teacher_allocated,
)
from db import get_conn  # noqa: E402
from provision_selfserve import acesso_url, generate_temp_password  # noqa: E402

EMAIL = (os.environ.get("HOMOLOG_EMAIL") or "suianyholanda@gmail.com").strip().lower()
NOME = (os.environ.get("HOMOLOG_NOME") or "Suiany").strip()
SEND_EMAIL = os.environ.get("HOMOLOG_SEND_EMAIL", "1").strip().lower() in (
    "1", "true", "yes", "on",
)
INST_DOMAIN = (os.environ.get("HOMOLOG_DOMAIN_INST") or "escolateste.edu.br").strip().lower()
ZONAS = ("administrativo", "operacional", "pedagogico")


def _provisional_b2c_id(email: str) -> int:
    digest = hashlib.sha256(
        f"inove4us-school:convite:{email.strip().lower()}".encode("utf-8")
    ).digest()
    n = int.from_bytes(digest[:4], "big") & 0x7FFFFFFF
    return -(n or 1)


def _invite_url(email: str) -> str:
    frontend = (
        os.getenv("INOVE4US_B2C_FRONTEND_URL")
        or os.getenv("INOVE4US_FRONTEND_URL")
        or "https://inove4us.com.br"
    ).rstrip("/")
    return f"{frontend}/acesso?email={email}&school_invite=1"


def main() -> int:
    report: dict = {"email": EMAIL, "nome": NOME}
    password_out = None

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, razao_social, dominio_email
                FROM public.school_instituicoes
                WHERE lower(dominio_email) = %s
                ORDER BY created_at NULLS LAST
                LIMIT 1
                """,
                (INST_DOMAIN,),
            )
            inst = cur.fetchone()
            if not inst:
                raise RuntimeError(
                    f"Instituição com domínio {INST_DOMAIN} não encontrada. "
                    "Rode o seed Escola Teste antes."
                )
            inst_id = str(inst["id"])
            report["instituicao"] = {
                "id": inst_id,
                "razao_social": inst["razao_social"],
                "dominio_email": inst["dominio_email"],
            }

            cur.execute(
                "SELECT id, instituicao_id FROM public.school_gestores WHERE lower(email) = %s",
                (EMAIL,),
            )
            g = cur.fetchone()
            # Com e-mail: sempre temos senha conhecida (gera/rotaciona).
            pwd = (os.environ.get("HOMOLOG_PASSWORD") or "").strip()
            if not pwd and (SEND_EMAIL or not g):
                pwd = generate_temp_password()
            if g:
                if str(g["instituicao_id"]) != inst_id:
                    raise RuntimeError("E-mail já pertence a outra instituição")
                gestor_id = str(g["id"])
                if pwd:
                    cur.execute(
                        """
                        UPDATE public.school_gestores
                        SET nome = %s, senha_hash = %s, cargo = 'Outro',
                            ativo = TRUE, updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        (NOME, generate_password_hash(pwd), gestor_id),
                    )
                    password_out = pwd
                    report["password_status"] = "atualizada"
                else:
                    cur.execute(
                        """
                        UPDATE public.school_gestores
                        SET nome = %s, cargo = 'Outro', ativo = TRUE,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        (NOME, gestor_id),
                    )
                    report["password_status"] = "inalterada"
            else:
                if not pwd:
                    pwd = generate_temp_password()
                password_out = pwd
                cur.execute(
                    """
                    INSERT INTO public.school_gestores (
                        instituicao_id, nome, email, senha_hash, cargo, ativo
                    ) VALUES (%s, %s, %s, %s, 'Outro', TRUE)
                    RETURNING id
                    """,
                    (inst_id, NOME, EMAIL, generate_password_hash(pwd)),
                )
                gestor_id = str(cur.fetchone()["id"])
                report["password_status"] = "gerada"

            for zona in ZONAS:
                cur.execute(
                    """
                    INSERT INTO public.school_gestor_perfis (gestor_id, zona, ativo)
                    VALUES (%s, %s, TRUE)
                    ON CONFLICT (gestor_id, zona) DO UPDATE SET
                        ativo = TRUE, updated_at = CURRENT_TIMESTAMP
                    """,
                    (gestor_id, zona),
                )
            report["gestor_id"] = gestor_id
            report["zonas"] = list(ZONAS)

            cur.execute(
                """
                INSERT INTO public.school_homologadores (
                    instituicao_id, gestor_id, email, nome, funcao, escopo_dados, ativo
                ) VALUES (%s, %s, %s, %s, 'homologador', 'proprio', TRUE)
                ON CONFLICT (gestor_id) DO UPDATE SET
                    email = EXCLUDED.email,
                    nome = EXCLUDED.nome,
                    funcao = 'homologador',
                    escopo_dados = 'proprio',
                    ativo = TRUE,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id, email, escopo_dados
                """,
                (inst_id, gestor_id, EMAIL, NOME),
            )
            h = cur.fetchone()
            report["homologador"] = {
                "id": str(h["id"]),
                "email": h["email"],
                "escopo_dados": h["escopo_dados"],
            }

            # vínculo professor
            b2c_id = _provisional_b2c_id(EMAIL)
            cur.execute(
                """
                SELECT id, status_vinculo, professor_b2c_id
                FROM public.school_professores_vinculo
                WHERE instituicao_id = %s
                  AND (lower(email_convite) = %s OR professor_b2c_id = %s)
                LIMIT 1
                """,
                (inst_id, EMAIL, b2c_id),
            )
            vin = cur.fetchone()
            if vin and vin["status_vinculo"] != "revogado":
                vinculo_id = str(vin["id"])
                created_vin = False
            elif vin:
                cur.execute(
                    """
                    UPDATE public.school_professores_vinculo
                    SET email_convite = %s, professor_b2c_id = %s,
                        status_vinculo = 'pendente', updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    RETURNING id, status_vinculo, professor_b2c_id
                    """,
                    (EMAIL, b2c_id, str(vin["id"])),
                )
                vin = cur.fetchone()
                vinculo_id = str(vin["id"])
                created_vin = True
            else:
                cur.execute(
                    """
                    INSERT INTO public.school_professores_vinculo
                        (instituicao_id, professor_b2c_id, email_convite, status_vinculo)
                    VALUES (%s, %s, %s, 'pendente')
                    RETURNING id, status_vinculo, professor_b2c_id
                    """,
                    (inst_id, b2c_id, EMAIL),
                )
                vin = cur.fetchone()
                vinculo_id = str(vin["id"])
                created_vin = True

            report["vinculo"] = {
                "id": vinculo_id,
                "status": vin["status_vinculo"],
                "created": created_vin,
                "invite_url": _invite_url(EMAIL),
            }

            # alocação: reusa primeira turma/disciplina da instituição
            cur.execute(
                """
                SELECT t.id AS turma_id, d.id AS disciplina_id,
                       t.unidade_id AS unidade_id,
                       t.periodo_letivo_id AS periodo_id
                FROM public.school_turmas t
                JOIN public.school_disciplinas d ON d.instituicao_id = t.instituicao_id
                WHERE t.instituicao_id = %s
                ORDER BY t.created_at NULLS LAST
                LIMIT 1
                """,
                (inst_id,),
            )
            acad = cur.fetchone()
            aloc_id = None
            if acad:
                cur.execute(
                    """
                    SELECT id FROM public.school_alocacoes_docentes
                    WHERE instituicao_id = %s
                      AND professor_vinculo_id = %s
                      AND turma_id = %s
                      AND disciplina_id = %s
                    LIMIT 1
                    """,
                    (
                        inst_id,
                        vinculo_id,
                        str(acad["turma_id"]),
                        str(acad["disciplina_id"]),
                    ),
                )
                existing_aloc = cur.fetchone()
                if existing_aloc:
                    aloc_id = str(existing_aloc["id"])
                else:
                    cur.execute(
                        """
                        INSERT INTO public.school_alocacoes_docentes (
                            instituicao_id, unidade_id, periodo_id,
                            disciplina_id, professor_vinculo_id, turma_id
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (
                            inst_id,
                            str(acad["unidade_id"]),
                            str(acad["periodo_id"]),
                            str(acad["disciplina_id"]),
                            vinculo_id,
                            str(acad["turma_id"]),
                        ),
                    )
                    aloc_id = str(cur.fetchone()["id"])
            report["alocacao_id"] = aloc_id

    # pushes B2C (fora da txn principal ok)
    if report["vinculo"]["status"] != "ativo":
        report["teacher_invite_push"] = dispatch_event_to_b2c(
            "TEACHER_INVITE",
            {
                "instituicao_id": report["instituicao"]["id"],
                "instituicao_nome": report["instituicao"]["razao_social"],
                "vinculo_id": report["vinculo"]["id"],
                "professor_email": EMAIL,
                "email": EMAIL,
                "professor_b2c_id": str(_provisional_b2c_id(EMAIL)),
                "invite_url": report["vinculo"]["invite_url"],
            },
        )
    else:
        report["teacher_invite_push"] = {"skipped": True, "reason": "já ativo"}

    if report.get("alocacao_id"):
        report["teacher_allocated_push"] = dispatch_teacher_allocated(report["alocacao_id"])

    # Um e-mail: senha School + link Inove (via webhook SES no B2C)
    if SEND_EMAIL:
        if not password_out:
            raise RuntimeError(
                "HOMOLOG_SEND_EMAIL=1 exige senha conhecida. "
                "Defina HOMOLOG_PASSWORD ou deixe o script gerar."
            )
        master = (os.environ.get("PRODUCTION_MASTER_KEY") or "").strip()
        school_origin = (
            os.getenv("FRONTEND_ORIGIN") or "https://school.inove4us.com.br"
        ).rstrip("/")
        inove_origin = (
            os.getenv("INOVE4US_B2C_FRONTEND_URL")
            or os.getenv("INOVE4US_FRONTEND_URL")
            or "https://inove4us.com.br"
        ).rstrip("/")
        school_bypass = (
            f"{school_origin}/gatekeeper/bypass?secret={quote(master, safe='')}"
            if master
            else ""
        )
        inove_bypass = (
            f"{inove_origin}/gatekeeper/bypass?secret={quote(master, safe='')}"
            if master
            else ""
        )
        report["credentials_email"] = dispatch_event_to_b2c(
            "SCHOOL_HOMOLOGADOR_CREDENTIALS",
            {
                "instituicao_id": report["instituicao"]["id"],
                "email": EMAIL,
                "gestor_email": EMAIL,
                "nome": NOME,
                "senha_temporaria": password_out,
                "acesso_url": acesso_url(),
                "invite_url": report["vinculo"]["invite_url"],
                "razao_social": report["instituicao"]["razao_social"],
                "school_bypass_url": school_bypass,
                "inove_bypass_url": inove_bypass,
            },
        )
    else:
        report["credentials_email"] = {"skipped": True, "reason": "HOMOLOG_SEND_EMAIL=0"}

    print("--- REPORT ---", flush=True)
    print(json.dumps(report, default=str, ensure_ascii=False, indent=2), flush=True)
    if password_out:
        print("--- CREDENTIALS (não versionar) ---", flush=True)
        print(
            json.dumps(
                {"email": EMAIL, "password": password_out, "role": "homologador"},
                ensure_ascii=False,
            ),
            flush=True,
        )
    print("=== provision homologador OK ===", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"PROVISION_FAILED: {exc}", file=sys.stderr, flush=True)
        raise
