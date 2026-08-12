"""Espelho acadêmico School → B2C (instituição/período/curso/disciplina/turma/alocação).

Catálogo curso↔disciplina é N:N (`inove_curso_disciplinas`), construído de forma
incremental no webhook TEACHER_ALLOCATED — o espelho B2C é por professor, então
associar disciplina a curso no School sem alocação não tem destinatário aqui.
`_synthetic_curso_school_id` foi removido: o School (034) sempre envia curso da turma.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from psycopg2.extras import Json, RealDictCursor

from db import ensure_instituicao_b2b_columns, find_cliente_by_email, get_conn


def _log(msg: str) -> None:
    print(f"[school-mirror] {msg}", flush=True)


def _as_uuid(value: Any) -> str | None:
    if value is None or value == "":
        return None
    try:
        return str(UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        return None


def _as_date(value: Any, fallback: date | None = None) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value or "").strip()[:10]
    if not s:
        return fallback
    try:
        return date.fromisoformat(s)
    except ValueError:
        return fallback


def _map_tipo_periodo(raw: Any) -> str:
    t = str(raw or "anual").strip().lower()
    allowed = {"anual", "semestral", "trimestral", "modular", "quinzenal", "mensal"}
    return t if t in allowed else "anual"


def store_pending(
    *,
    email: str,
    event_type: str,
    payload: dict,
    school_key: str | None = None,
) -> dict:
    mail = (email or "").strip().lower()
    if not mail or "@" not in mail:
        return {"ok": False, "reason": "email_invalid"}
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if school_key:
                cur.execute(
                    """
                    UPDATE public.inove_school_pending
                       SET payload = %s,
                           created_at = CURRENT_TIMESTAMP
                     WHERE event_type = %s
                       AND school_key = %s
                       AND processed_at IS NULL
                    RETURNING id
                    """,
                    (Json(payload or {}), event_type, school_key),
                )
                row = cur.fetchone()
                if row:
                    return {"ok": True, "pending_id": int(row["id"]), "updated": True}
            cur.execute(
                """
                INSERT INTO public.inove_school_pending (email, event_type, payload, school_key)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (mail, event_type, Json(payload or {}), school_key),
            )
            row = cur.fetchone()
    return {"ok": True, "pending_id": int(row["id"]), "updated": False}


def bind_professor_to_institution(
    *,
    id_clie: int,
    instituicao_b2b_id: str,
    institutional_name: str | None = None,
) -> dict:
    ensure_instituicao_b2b_columns()
    inst = _as_uuid(instituicao_b2b_id)
    if not inst:
        return {"ok": False, "reason": "instituicao_id_invalid"}
    nome = (institutional_name or "").strip() or None
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                UPDATE public.ctdi_clie
                   SET instituicao_b2b_id = %s::uuid,
                       institutional_name = COALESCE(%s, institutional_name)
                 WHERE id_clie = %s
                RETURNING id_clie, instituicao_b2b_id, institutional_name, mail_clie
                """,
                (inst, nome, int(id_clie)),
            )
            row = cur.fetchone()
    if not row:
        return {"ok": False, "reason": "cliente_not_found"}
    return {
        "ok": True,
        "id_clie": int(row["id_clie"]),
        "instituicao_b2b_id": str(row["instituicao_b2b_id"]),
        "institutional_name": row.get("institutional_name"),
        "email": row.get("mail_clie"),
    }


def dispatch_invite_accepted(
    *,
    id_clie: int,
    email: str,
    instituicao_id: str,
    vinculo_id: str | None = None,
    institutional_name: str | None = None,
) -> dict:
    from school_outbound import dispatch_event_to_school

    payload = {
        "professor_b2c_id": int(id_clie),
        "professor_email": (email or "").strip().lower(),
        "email": (email or "").strip().lower(),
        "instituicao_id": instituicao_id,
        "vinculo_id": vinculo_id,
        "institutional_name": institutional_name,
    }
    return dispatch_event_to_school("TEACHER_INVITE_ACCEPTED", payload)


def _upsert_instituicao(cur, id_clie: int, payload: dict) -> int | None:
    school_id = _as_uuid(payload.get("instituicao_id"))
    if not school_id:
        return None
    nome = (
        str(payload.get("instituicao_nome") or "").strip()
        or str(payload.get("unidade_nome") or "").strip()
        or "Instituição"
    )[:255]
    cur.execute(
        """
        SELECT id FROM public.inove_instituicoes
         WHERE id_clie = %s AND school_instituicao_id = %s::uuid AND ativo = TRUE
         LIMIT 1
        """,
        (id_clie, school_id),
    )
    row = cur.fetchone()
    if row:
        cur.execute(
            """
            UPDATE public.inove_instituicoes
               SET nome = %s,
                   origem_school = TRUE,
                   updated_at = CURRENT_TIMESTAMP
             WHERE id = %s
            RETURNING id
            """,
            (nome, int(row["id"])),
        )
        return int(cur.fetchone()["id"])
    cur.execute(
        """
        INSERT INTO public.inove_instituicoes (
            id_clie, nome, tipo_instituicao, origem_school, school_instituicao_id
        )
        VALUES (%s, %s, 'escola', TRUE, %s::uuid)
        RETURNING id
        """,
        (id_clie, nome, school_id),
    )
    return int(cur.fetchone()["id"])


def _upsert_periodo(cur, instituicao_id: int, payload: dict) -> int | None:
    school_id = _as_uuid(payload.get("periodo_id"))
    if not school_id:
        return None
    rotulo = str(payload.get("periodo_nome") or "Período letivo").strip()[:160]
    tipo = _map_tipo_periodo(payload.get("tipo_periodo"))
    di = _as_date(payload.get("data_inicio_periodo")) or date(date.today().year, 1, 1)
    df = _as_date(payload.get("data_fim_periodo")) or date(di.year, 12, 31)
    if df <= di:
        df = date(di.year, 12, 31) if di.month < 12 or di.day < 31 else date(di.year + 1, 1, 31)
    ano = di.year
    cur.execute(
        """
        SELECT id FROM public.inove_periodos_letivos
         WHERE instituicao_id = %s AND school_periodo_id = %s::uuid AND ativo = TRUE
         LIMIT 1
        """,
        (instituicao_id, school_id),
    )
    row = cur.fetchone()
    if row:
        cur.execute(
            """
            UPDATE public.inove_periodos_letivos
               SET rotulo = %s,
                   ano_letivo = %s,
                   tipo_periodo = %s,
                   data_inicio = %s,
                   data_fim = %s,
                   origem_school = TRUE,
                   updated_at = CURRENT_TIMESTAMP
             WHERE id = %s
            RETURNING id
            """,
            (rotulo, ano, tipo, di, df, int(row["id"])),
        )
        return int(cur.fetchone()["id"])
    cur.execute(
        """
        INSERT INTO public.inove_periodos_letivos (
            instituicao_id, rotulo, ano_letivo, tipo_periodo,
            data_inicio, data_fim, status, origem_school, school_periodo_id
        )
        VALUES (%s, %s, %s, %s, %s, %s, 'em_andamento', TRUE, %s::uuid)
        RETURNING id
        """,
        (instituicao_id, rotulo, ano, tipo, di, df, school_id),
    )
    return int(cur.fetchone()["id"])


def _upsert_curso(cur, periodo_id: int, payload: dict) -> int | None:
    school_curso = _as_uuid(payload.get("curso_id"))
    if not school_curso:
        # School 034: turma.curso_id é NOT NULL. Placeholder sintético (era híbrida)
        # removido — sem curso no payload a materialização falha de forma explícita.
        return None
    nome = str(payload.get("curso_nome") or "").strip()
    if not nome:
        unidade = str(payload.get("unidade_nome") or "").strip()
        nome = f"Curso · {unidade}" if unidade else "Curso institucional"
    nome = nome[:255]
    cur.execute(
        """
        SELECT id FROM public.inove_cursos
         WHERE periodo_letivo_id = %s AND school_curso_id = %s::uuid AND ativo = TRUE
         LIMIT 1
        """,
        (periodo_id, school_curso),
    )
    row = cur.fetchone()
    if row:
        cur.execute(
            """
            UPDATE public.inove_cursos
               SET nome = %s,
                   origem_school = TRUE,
                   updated_at = CURRENT_TIMESTAMP
             WHERE id = %s
            RETURNING id
            """,
            (nome, int(row["id"])),
        )
        return int(cur.fetchone()["id"])
    cur.execute(
        """
        INSERT INTO public.inove_cursos (
            periodo_letivo_id, nome, origem_school, school_curso_id
        )
        VALUES (%s, %s, TRUE, %s::uuid)
        RETURNING id
        """,
        (periodo_id, nome, school_curso),
    )
    return int(cur.fetchone()["id"])


def _associate_curso_disciplina(cur, curso_id: int, disciplina_id: int) -> None:
    """Idempotente. Catálogo N:N local (espelha school_curso_disciplinas)."""
    cur.execute(
        """
        INSERT INTO public.inove_curso_disciplinas (curso_id, disciplina_id)
        VALUES (%s, %s)
        ON CONFLICT (curso_id, disciplina_id) DO NOTHING
        """,
        (int(curso_id), int(disciplina_id)),
    )


def _upsert_disciplina(
    cur, instituicao_id: int, curso_id: int, payload: dict
) -> int | None:
    """Uma linha por (instituição do professor, school_disciplina_id)."""
    school_id = _as_uuid(payload.get("disciplina_id"))
    if not school_id:
        return None
    nome = str(payload.get("disciplina_nome") or "Disciplina").strip()[:255]
    ementa = str(payload.get("ementa_macro") or "").strip() or None
    cur.execute(
        """
        SELECT id FROM public.inove_disciplinas
         WHERE instituicao_id = %s
           AND school_disciplina_id = %s::uuid
           AND ativo = TRUE
         LIMIT 1
        """,
        (int(instituicao_id), school_id),
    )
    row = cur.fetchone()
    if row:
        did = int(row["id"])
        cur.execute(
            """
            UPDATE public.inove_disciplinas
               SET nome = %s,
                   ementa = COALESCE(%s, ementa),
                   origem_school = TRUE,
                   updated_at = CURRENT_TIMESTAMP
             WHERE id = %s
            RETURNING id
            """,
            (nome, ementa, did),
        )
        _associate_curso_disciplina(cur, curso_id, did)
        return did
    cur.execute(
        """
        INSERT INTO public.inove_disciplinas (
            curso_id, instituicao_id, nome, ementa,
            origem_school, school_disciplina_id
        )
        VALUES (%s, %s, %s, %s, TRUE, %s::uuid)
        RETURNING id
        """,
        (curso_id, int(instituicao_id), nome, ementa, school_id),
    )
    did = int(cur.fetchone()["id"])
    _associate_curso_disciplina(cur, curso_id, did)
    return did


def _upsert_turma(cur, curso_id: int, payload: dict) -> int | None:
    school_id = _as_uuid(payload.get("turma_id"))
    if not school_id:
        return None
    nome = str(payload.get("turma_nome") or "Turma").strip()[:120]
    turno = str(payload.get("turma_turno") or "").strip()[:40] or None
    cur.execute(
        """
        SELECT id FROM public.inove_turmas
         WHERE curso_id = %s AND school_turma_id = %s::uuid AND ativo = TRUE
         LIMIT 1
        """,
        (curso_id, school_id),
    )
    row = cur.fetchone()
    if row:
        cur.execute(
            """
            UPDATE public.inove_turmas
               SET nome = %s,
                   turno = COALESCE(%s, turno),
                   origem_school = TRUE,
                   updated_at = CURRENT_TIMESTAMP
             WHERE id = %s
            RETURNING id
            """,
            (nome, turno, int(row["id"])),
        )
        return int(cur.fetchone()["id"])
    cur.execute(
        """
        INSERT INTO public.inove_turmas (
            curso_id, nome, turno, origem_school, school_turma_id
        )
        VALUES (%s, %s, %s, TRUE, %s::uuid)
        RETURNING id
        """,
        (curso_id, nome, turno, school_id),
    )
    return int(cur.fetchone()["id"])


def _parse_event_dt(raw: Any) -> datetime:
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, date):
        return datetime(raw.year, raw.month, raw.day, 8, 0, 0)
    s = str(raw or "").strip()
    if not s:
        return datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
    try:
        if "T" in s or " " in s:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
        d = date.fromisoformat(s[:10])
        return datetime(d.year, d.month, d.day, 8, 0, 0)
    except ValueError:
        return datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)


def ensure_agenda_for_allocation(*, id_clie: int, payload: dict) -> dict:
    """Mantém compromisso de planejamento institucional (idempotente por alocacao_id)."""
    alocacao_id = _as_uuid(payload.get("alocacao_id"))
    disciplina_nome = str(payload.get("disciplina_nome") or "").strip() or "Disciplina"
    ementa_macro = str(payload.get("ementa_macro") or "").strip()
    titulo = f"Planejamento Institucional: {disciplina_nome}"[:200]
    data_evento = _parse_event_dt(payload.get("data_inicio_periodo"))
    meta = {
        "alocacao_escola": True,
        "is_from_school": True,
        "professor_b2c_id": str(payload.get("professor_b2c_id") or id_clie),
        "disciplina_nome": disciplina_nome,
        "ementa_macro": ementa_macro,
        "instituicao_id": payload.get("instituicao_id"),
        "unidade_nome": payload.get("unidade_nome"),
        "periodo_nome": payload.get("periodo_nome"),
        "alocacao_id": alocacao_id,
        "status_planejamento": "pendente",
    }
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                ALTER TABLE public.inove_agenda_eventos
                    ADD COLUMN IF NOT EXISTS is_from_school BOOLEAN NOT NULL DEFAULT FALSE
                """
            )
            if alocacao_id:
                cur.execute(
                    """
                    SELECT id_evento
                      FROM public.inove_agenda_eventos
                     WHERE id_clie = %s
                       AND origem = 'alocacao_escola'
                       AND id_externo_importacao = %s
                     LIMIT 1
                    """,
                    (id_clie, alocacao_id),
                )
                existing = cur.fetchone()
                if existing:
                    return {
                        "ok": True,
                        "idempotent": True,
                        "id_evento": int(existing["id_evento"]),
                    }
            cur.execute(
                """
                INSERT INTO public.inove_agenda_eventos (
                    id_clie, data_evento, titulo, nota_texto, status, tipo,
                    origem, is_from_school, id_externo_importacao, meta_json
                )
                VALUES (
                    %s, %s, %s, %s,
                    'planejado', 'geral', 'alocacao_escola', TRUE,
                    %s, %s
                )
                RETURNING id_evento
                """,
                (
                    id_clie,
                    data_evento,
                    titulo,
                    ementa_macro or None,
                    alocacao_id,
                    Json(meta),
                ),
            )
            row = cur.fetchone()
    return {"ok": True, "idempotent": False, "id_evento": int(row["id_evento"])}


def materialize_allocation(*, id_clie: int, payload: dict) -> dict:
    """Upsert árvore acadêmica + inove_alocacoes_escola a partir de TEACHER_ALLOCATED."""
    aloc_school = _as_uuid(payload.get("alocacao_id"))
    if not aloc_school:
        return {"ok": False, "reason": "alocacao_id_missing"}

    ensure_instituicao_b2b_columns()
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            inst_id = _upsert_instituicao(cur, id_clie, payload)
            if not inst_id:
                return {"ok": False, "reason": "instituicao_upsert_failed"}
            periodo_id = _upsert_periodo(cur, inst_id, payload)
            if not periodo_id:
                return {"ok": False, "reason": "periodo_upsert_failed"}
            curso_id = _upsert_curso(cur, periodo_id, payload)
            if not curso_id:
                return {"ok": False, "reason": "curso_upsert_failed"}
            disciplina_id = _upsert_disciplina(cur, inst_id, curso_id, payload)
            if not disciplina_id:
                return {"ok": False, "reason": "disciplina_upsert_failed"}
            turma_id = _upsert_turma(cur, curso_id, payload)

            # Bind Chave Mestra se ainda vazia
            school_inst = _as_uuid(payload.get("instituicao_id"))
            if school_inst:
                cur.execute(
                    """
                    UPDATE public.ctdi_clie
                       SET instituicao_b2b_id = COALESCE(instituicao_b2b_id, %s::uuid),
                           institutional_name = COALESCE(
                             NULLIF(TRIM(institutional_name), ''),
                             %s
                           )
                     WHERE id_clie = %s
                    """,
                    (
                        school_inst,
                        str(payload.get("instituicao_nome") or "").strip() or None,
                        id_clie,
                    ),
                )

            cur.execute(
                """
                INSERT INTO public.inove_alocacoes_escola (
                    id_clie, school_alocacao_id, school_instituicao_id, school_vinculo_id,
                    instituicao_id, periodo_id, curso_id, disciplina_id, turma_id,
                    instituicao_nome, periodo_nome, curso_nome, disciplina_nome,
                    turma_nome, turma_turno, unidade_nome, ativo, meta_json
                )
                VALUES (
                    %s, %s::uuid, %s::uuid, %s::uuid,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, TRUE, %s
                )
                ON CONFLICT (school_alocacao_id) DO UPDATE SET
                    id_clie = EXCLUDED.id_clie,
                    school_instituicao_id = EXCLUDED.school_instituicao_id,
                    school_vinculo_id = COALESCE(
                        EXCLUDED.school_vinculo_id,
                        inove_alocacoes_escola.school_vinculo_id
                    ),
                    instituicao_id = EXCLUDED.instituicao_id,
                    periodo_id = EXCLUDED.periodo_id,
                    curso_id = EXCLUDED.curso_id,
                    disciplina_id = EXCLUDED.disciplina_id,
                    turma_id = EXCLUDED.turma_id,
                    instituicao_nome = EXCLUDED.instituicao_nome,
                    periodo_nome = EXCLUDED.periodo_nome,
                    curso_nome = EXCLUDED.curso_nome,
                    disciplina_nome = EXCLUDED.disciplina_nome,
                    turma_nome = EXCLUDED.turma_nome,
                    turma_turno = EXCLUDED.turma_turno,
                    unidade_nome = EXCLUDED.unidade_nome,
                    ativo = TRUE,
                    meta_json = EXCLUDED.meta_json,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
                """,
                (
                    id_clie,
                    aloc_school,
                    _as_uuid(payload.get("instituicao_id")),
                    _as_uuid(payload.get("vinculo_id")),
                    inst_id,
                    periodo_id,
                    curso_id,
                    disciplina_id,
                    turma_id,
                    str(payload.get("instituicao_nome") or "")[:255] or None,
                    str(payload.get("periodo_nome") or "")[:160] or None,
                    str(payload.get("curso_nome") or "")[:255] or None,
                    str(payload.get("disciplina_nome") or "")[:255] or None,
                    str(payload.get("turma_nome") or "")[:120] or None,
                    str(payload.get("turma_turno") or "")[:40] or None,
                    str(payload.get("unidade_nome") or "")[:160] or None,
                    Json(payload or {}),
                ),
            )
            aloc_row = cur.fetchone()

    return {
        "ok": True,
        "alocacao_id": int(aloc_row["id"]),
        "instituicao_id": inst_id,
        "periodo_id": periodo_id,
        "curso_id": curso_id,
        "disciplina_id": disciplina_id,
        "turma_id": turma_id,
        "school_alocacao_id": aloc_school,
    }


def handle_teacher_invite(payload: dict) -> dict:
    body = payload if isinstance(payload, dict) else {}
    email = str(body.get("professor_email") or body.get("email") or "").strip().lower()
    instituicao_id = _as_uuid(body.get("instituicao_id"))
    vinculo_id = _as_uuid(body.get("vinculo_id"))
    nome = str(body.get("instituicao_nome") or "").strip() or None
    invite_url = str(body.get("invite_url") or "").strip() or None

    if not email or "@" not in email:
        return {"handled": False, "reason": "email_missing", "event": "TEACHER_INVITE"}
    if not instituicao_id:
        return {"handled": False, "reason": "instituicao_id_missing", "event": "TEACHER_INVITE"}

    cliente = find_cliente_by_email(email)
    if not cliente or not cliente.get("id_clie"):
        pending = store_pending(
            email=email,
            event_type="TEACHER_INVITE",
            payload=body,
            school_key=vinculo_id or instituicao_id,
        )
        _log(f"TEACHER_INVITE pending email={email} pending={pending}")
        return {
            "handled": True,
            "event": "TEACHER_INVITE",
            "pending": True,
            "email": email,
            "invite_url": invite_url,
            "pending_id": pending.get("pending_id"),
        }

    id_clie = int(cliente["id_clie"])
    bind = bind_professor_to_institution(
        id_clie=id_clie,
        instituicao_b2b_id=instituicao_id,
        institutional_name=nome,
    )
    accepted = dispatch_invite_accepted(
        id_clie=id_clie,
        email=email,
        instituicao_id=instituicao_id,
        vinculo_id=vinculo_id,
        institutional_name=nome,
    )
    _log(f"TEACHER_INVITE bound id_clie={id_clie} school_ack={accepted.get('ok')}")
    return {
        "handled": True,
        "event": "TEACHER_INVITE",
        "pending": False,
        "id_clie": id_clie,
        "bind": bind,
        "school_ack": accepted,
        "invite_url": invite_url,
    }


def accept_invite_for_cliente(
    *,
    id_clie: int,
    email: str | None = None,
    instituicao_id: str | None = None,
    vinculo_id: str | None = None,
    institutional_name: str | None = None,
) -> dict:
    """Aceite explícito (login /acesso) + replay de pendências."""
    ensure_instituicao_b2b_columns()
    mail = (email or "").strip().lower()
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id_clie, mail_clie, instituicao_b2b_id, institutional_name
                  FROM public.ctdi_clie
                 WHERE id_clie = %s
                 LIMIT 1
                """,
                (int(id_clie),),
            )
            cliente = cur.fetchone()
    if not cliente:
        return {"ok": False, "reason": "cliente_not_found"}

    mail = mail or str(cliente.get("mail_clie") or "").strip().lower()
    inst = _as_uuid(instituicao_id) or (
        str(cliente["instituicao_b2b_id"]) if cliente.get("instituicao_b2b_id") else None
    )
    nome = (institutional_name or cliente.get("institutional_name") or "").strip() or None
    vinculo = _as_uuid(vinculo_id)

    # Busca pending TEACHER_INVITE se faltar instituição
    pending_invites: list[dict] = []
    if mail:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, payload
                      FROM public.inove_school_pending
                     WHERE LOWER(email) = %s
                       AND event_type = 'TEACHER_INVITE'
                       AND processed_at IS NULL
                     ORDER BY created_at ASC
                    """,
                    (mail,),
                )
                pending_invites = list(cur.fetchall() or [])

    if not inst and pending_invites:
        p0 = pending_invites[0].get("payload") or {}
        if isinstance(p0, str):
            import json

            try:
                p0 = json.loads(p0)
            except Exception:
                p0 = {}
        inst = _as_uuid(p0.get("instituicao_id"))
        vinculo = vinculo or _as_uuid(p0.get("vinculo_id"))
        nome = nome or str(p0.get("instituicao_nome") or "").strip() or None

    if not inst:
        return {"ok": False, "reason": "instituicao_id_missing"}

    bind = bind_professor_to_institution(
        id_clie=int(id_clie),
        instituicao_b2b_id=inst,
        institutional_name=nome,
    )
    if not bind.get("ok"):
        return bind

    school_ack = dispatch_invite_accepted(
        id_clie=int(id_clie),
        email=mail,
        instituicao_id=inst,
        vinculo_id=vinculo,
        institutional_name=nome,
    )

    # Marca invites processados
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.inove_school_pending
                   SET processed_at = CURRENT_TIMESTAMP
                 WHERE LOWER(email) = %s
                   AND event_type = 'TEACHER_INVITE'
                   AND processed_at IS NULL
                """,
                (mail,),
            )

    replay = replay_pending_allocations(id_clie=int(id_clie), email=mail)
    return {
        "ok": True,
        "bind": bind,
        "school_ack": school_ack,
        "replay": replay,
        "is_institutional": True,
        "instituicao_b2b_id": inst,
        "institutional_name": nome,
    }


def replay_pending_allocations(*, id_clie: int, email: str) -> dict:
    mail = (email or "").strip().lower()
    if not mail:
        return {"ok": True, "replayed": 0}
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, payload
                  FROM public.inove_school_pending
                 WHERE LOWER(email) = %s
                   AND event_type = 'TEACHER_ALLOCATED'
                   AND processed_at IS NULL
                 ORDER BY created_at ASC
                """,
                (mail,),
            )
            rows = list(cur.fetchall() or [])

    replayed = 0
    errors: list[str] = []
    for row in rows:
        payload = row.get("payload") or {}
        if isinstance(payload, str):
            import json

            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}
        try:
            mat = materialize_allocation(id_clie=id_clie, payload=payload)
            if mat.get("ok"):
                ensure_agenda_for_allocation(id_clie=id_clie, payload=payload)
                replayed += 1
                with get_conn() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            UPDATE public.inove_school_pending
                               SET processed_at = CURRENT_TIMESTAMP
                             WHERE id = %s
                            """,
                            (int(row["id"]),),
                        )
            else:
                errors.append(str(mat.get("reason") or "fail"))
        except Exception as exc:
            errors.append(str(exc))
    return {"ok": True, "replayed": replayed, "errors": errors, "total": len(rows)}


def list_alocacoes_escola(id_clie: int) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT a.*
                  FROM public.inove_alocacoes_escola a
                 WHERE a.id_clie = %s AND a.ativo = TRUE
                 ORDER BY a.instituicao_nome NULLS LAST,
                          a.periodo_nome NULLS LAST,
                          a.disciplina_nome NULLS LAST,
                          a.turma_nome NULLS LAST,
                          a.id ASC
                """,
                (int(id_clie),),
            )
            rows = cur.fetchall() or []
    out = []
    for r in rows:
        d = dict(r)
        for k in (
            "school_alocacao_id",
            "school_instituicao_id",
            "school_vinculo_id",
            "created_at",
            "updated_at",
        ):
            if d.get(k) is not None:
                d[k] = str(d[k])
        out.append(d)
    return out


def handle_teacher_allocated(payload: dict) -> dict:
    body = payload if isinstance(payload, dict) else {}
    email = str(body.get("professor_email") or body.get("email") or "").strip().lower()
    id_clie = None
    cliente = find_cliente_by_email(email) if email and "@" in email else None
    if cliente and cliente.get("id_clie"):
        id_clie = int(cliente["id_clie"])
    else:
        raw = str(body.get("professor_b2c_id") or "").strip()
        if raw.isdigit() and int(raw) > 0:
            id_clie = int(raw)

    if not id_clie:
        aloc_key = _as_uuid(body.get("alocacao_id"))
        pending = store_pending(
            email=email or f"unknown-{aloc_key or 'x'}@pending.local",
            event_type="TEACHER_ALLOCATED",
            payload=body,
            school_key=aloc_key,
        )
        _log(f"TEACHER_ALLOCATED pending email={email} {pending}")
        return {
            "handled": True if email and "@" in email else False,
            "pending": True,
            "reason": "professor_not_found" if not (email and "@" in email) else "queued",
            "event": "TEACHER_ALLOCATED",
            "pending_id": pending.get("pending_id"),
        }

    mat = materialize_allocation(id_clie=id_clie, payload=body)
    agenda = ensure_agenda_for_allocation(id_clie=id_clie, payload=body) if mat.get("ok") else {}
    _log(
        f"TEACHER_ALLOCATED id_clie={id_clie} mirror={mat.get('ok')} "
        f"agenda={agenda.get('id_evento')}"
    )
    return {
        "handled": bool(mat.get("ok")),
        "event": "TEACHER_ALLOCATED",
        "id_clie": id_clie,
        "mirror": mat,
        "id_evento": agenda.get("id_evento"),
        "calendar_event_created": bool(agenda.get("ok") and not agenda.get("idempotent")),
        "idempotent": bool(agenda.get("idempotent")),
        "reason": mat.get("reason"),
    }
