"""Motor do Funil de Vendas — leads órfãos, distribuição e prospecção."""

from __future__ import annotations

import hashlib
import secrets
from typing import Any

STATUS_NOVO_LEAD = "novo_lead"
STATUS_DISTRIBUIDO = "distribuido"
STATUS_EM_NEGOCIACAO = "em_negociacao"
STATUS_CONVITE_ENVIADO = "convite_enviado"
STATUS_GANHO = "ganho"
STATUS_PERDIDO = "perdido"

STATUS_FUNIL_VALIDOS = frozenset({
    STATUS_NOVO_LEAD,
    STATUS_DISTRIBUIDO,
    STATUS_EM_NEGOCIACAO,
    STATUS_CONVITE_ENVIADO,
    STATUS_GANHO,
    STATUS_PERDIDO,
})

ORIGEM_ORGANICO = "organico"
ORIGEM_ADMIN = "admin_distribuicao"
ORIGEM_REATIVO = "consultor_reativo"
ORIGEM_ATIVO = "consultor_ativo"
ORIGEM_CONVITE = "convite"

KANBAN_COLUNAS = (
    STATUS_NOVO_LEAD,
    STATUS_DISTRIBUIDO,
    STATUS_EM_NEGOCIACAO,
    STATUS_CONVITE_ENVIADO,
    STATUS_GANHO,
    STATUS_PERDIDO,
)


class FunilError(ValueError):
    """Erro de negócio do funil."""


def gerar_ref_code() -> str:
    return secrets.token_hex(6)


def gerar_invite_token() -> str:
    return secrets.token_urlsafe(24)


def garantir_ref_code(cur, consultor_id: int) -> str:
    cur.execute(
        "SELECT ref_code FROM public.dx_consultores WHERE id = %s LIMIT 1;",
        (consultor_id,),
    )
    row = cur.fetchone()
    if not row:
        raise FunilError("Consultor não encontrado.")
    code = (row.get("ref_code") if isinstance(row, dict) else row[0]) or ""
    code = str(code).strip()
    if code:
        return code
    for _ in range(5):
        candidate = gerar_ref_code()
        try:
            cur.execute(
                """
                UPDATE public.dx_consultores
                SET ref_code = %s, atualizado_em = NOW()
                WHERE id = %s
                RETURNING ref_code;
                """,
                (candidate, consultor_id),
            )
            updated = cur.fetchone()
            if updated:
                return candidate
        except Exception:
            continue
    # fallback determinístico
    fallback = hashlib.md5(f"consultor-{consultor_id}".encode()).hexdigest()[:12]
    cur.execute(
        """
        UPDATE public.dx_consultores
        SET ref_code = %s, atualizado_em = NOW()
        WHERE id = %s;
        """,
        (fallback, consultor_id),
    )
    return fallback


def serializar_oportunidade(row: dict) -> dict:
    return {
        "id": row.get("id"),
        "id_clie": row.get("id_clie"),
        "id_matu": row.get("id_matu"),
        "id_consultor_origem": row.get("id_consultor_origem"),
        "status_funil": row.get("status_funil") or STATUS_NOVO_LEAD,
        "origem": row.get("origem") or ORIGEM_ORGANICO,
        "nome": row.get("nome") or row.get("nome_clie"),
        "email": row.get("email") or row.get("mail_clie"),
        "telefone": row.get("telefone") or row.get("fone_clie"),
        "empresa": row.get("empresa") or row.get("empresa_clie"),
        "invite_token": row.get("invite_token"),
        "motivo_perda": row.get("motivo_perda"),
        "consultor_nome": row.get("consultor_nome"),
        "consultor_email": row.get("consultor_email"),
        "consultor_ref": row.get("consultor_ref"),
        "status_ia": row.get("status_ia"),
        "criado_em": row["criado_em"].isoformat() if row.get("criado_em") else None,
        "atualizado_em": row["atualizado_em"].isoformat() if row.get("atualizado_em") else None,
    }


def _select_oportunidade_sql(where: str = "TRUE") -> str:
    return f"""
        SELECT o.*,
               c.nome_clie, c.mail_clie, c.fone_clie, c.empresa_clie,
               m.status_ia,
               u.nome AS consultor_nome, u.email AS consultor_email,
               dc.ref_code AS consultor_ref
        FROM public.dx_oportunidades o
        LEFT JOIN public.ctdi_clie c ON c.id_clie = o.id_clie
        LEFT JOIN public.ctdi_matu m ON m.id_matu = o.id_matu
        LEFT JOIN public.dx_consultores dc ON dc.id = o.id_consultor_origem
        LEFT JOIN public.paneldx_usuarios u ON u.id_usuario = dc.user_id
        WHERE {where}
    """


def listar_oportunidades(cur, status_funil: str | None = None) -> list[dict]:
    where = "TRUE"
    params: list[Any] = []
    if status_funil:
        if status_funil not in STATUS_FUNIL_VALIDOS:
            raise FunilError(f"status_funil inválido: {status_funil}")
        where = "o.status_funil = %s"
        params.append(status_funil)
    cur.execute(
        _select_oportunidade_sql(where) + " ORDER BY o.criado_em DESC, o.id DESC;",
        tuple(params),
    )
    return [serializar_oportunidade(dict(r)) for r in cur.fetchall()]


def montar_kanban(cur) -> dict:
    itens = listar_oportunidades(cur)
    colunas = {s: [] for s in KANBAN_COLUNAS}
    for item in itens:
        st = item.get("status_funil") or STATUS_NOVO_LEAD
        if st not in colunas:
            colunas[st] = []
        colunas[st].append(item)
    return {
        "colunas": colunas,
        "totais": {k: len(v) for k, v in colunas.items()},
        "total": len(itens),
    }


def garantir_oportunidade_orfao(
    cur,
    *,
    id_clie: int,
    id_matu: int,
    nome: str | None = None,
    email: str | None = None,
    telefone: str | None = None,
    empresa: str | None = None,
) -> dict | None:
    """
    REGRA AUTOMÁTICA: cliente com id_matu sem consultor → novo_lead.
    Idempotente. Não cria se já existir oportunidade para o id_matu
    ou se já houver contrato com consultor de origem.
    """
    cur.execute(
        "SELECT id FROM public.dx_oportunidades WHERE id_matu = %s LIMIT 1;",
        (id_matu,),
    )
    if cur.fetchone():
        return None

    cur.execute(
        """
        SELECT 1
        FROM public.dx_contratos
        WHERE id_clie = %s
          AND id_consultor_origem IS NOT NULL
          AND status IN ('ativo', 'trial', 'inadimplente')
        LIMIT 1;
        """,
        (id_clie,),
    )
    if cur.fetchone():
        return None

    # Se já há oportunidade aberta do mesmo e-mail com consultor (convite), não órfão
    if email:
        cur.execute(
            """
            SELECT id FROM public.dx_oportunidades
            WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s))
              AND id_consultor_origem IS NOT NULL
              AND status_funil IN ('convite_enviado', 'distribuido', 'em_negociacao')
            LIMIT 1;
            """,
            (email,),
        )
        if cur.fetchone():
            return None

    if not nome or not email:
        cur.execute(
            """
            SELECT nome_clie, mail_clie, fone_clie, empresa_clie
            FROM public.ctdi_clie WHERE id_clie = %s LIMIT 1;
            """,
            (id_clie,),
        )
        clie = cur.fetchone()
        if clie:
            clie = dict(clie)
            nome = nome or clie.get("nome_clie")
            email = email or clie.get("mail_clie")
            telefone = telefone or clie.get("fone_clie")
            empresa = empresa or clie.get("empresa_clie")

    cur.execute(
        """
        INSERT INTO public.dx_oportunidades (
            id_clie, id_matu, id_consultor_origem, status_funil, origem,
            nome, email, telefone, empresa
        ) VALUES (%s, %s, NULL, %s, %s, %s, %s, %s, %s)
        RETURNING *;
        """,
        (
            id_clie,
            id_matu,
            STATUS_NOVO_LEAD,
            ORIGEM_ORGANICO,
            nome,
            email,
            telefone,
            empresa,
        ),
    )
    row = cur.fetchone()
    return serializar_oportunidade(dict(row)) if row else None


def atribuir_lead_admin(cur, oportunidade_id: int, id_consultor: int) -> dict:
    cur.execute(
        "SELECT * FROM public.dx_oportunidades WHERE id = %s LIMIT 1 FOR UPDATE;",
        (oportunidade_id,),
    )
    opp = cur.fetchone()
    if not opp:
        raise FunilError("Oportunidade não encontrada.")
    opp = dict(opp)

    cur.execute(
        "SELECT id FROM public.dx_consultores WHERE id = %s AND ativo = TRUE LIMIT 1;",
        (id_consultor,),
    )
    if not cur.fetchone():
        raise FunilError("Consultor/agência inválido ou inativo.")

    if opp.get("id_consultor_origem") and int(opp["id_consultor_origem"]) != int(id_consultor):
        # Admin pode redistribuir
        pass

    cur.execute(
        """
        UPDATE public.dx_oportunidades
        SET id_consultor_origem = %s,
            status_funil = %s,
            origem = CASE
                WHEN origem = 'organico' THEN %s
                ELSE origem
            END,
            atualizado_em = NOW()
        WHERE id = %s
        RETURNING *;
        """,
        (id_consultor, STATUS_DISTRIBUIDO, ORIGEM_ADMIN, oportunidade_id),
    )
    updated = dict(cur.fetchone())

    # Espelha no contrato aberto, se existir
    if updated.get("id_clie"):
        cur.execute(
            """
            UPDATE public.dx_contratos
            SET id_consultor_origem = COALESCE(id_consultor_origem, %s),
                atualizado_em = NOW()
            WHERE id_clie = %s
              AND status IN ('ativo', 'trial', 'inadimplente')
              AND id_consultor_origem IS NULL;
            """,
            (id_consultor, updated["id_clie"]),
        )

    cur.execute(_select_oportunidade_sql("o.id = %s"), (oportunidade_id,))
    full = cur.fetchone()
    return serializar_oportunidade(dict(full)) if full else serializar_oportunidade(updated)


def vincular_lead_por_matu(cur, *, id_matu: int, id_consultor: int) -> dict:
    cur.execute(
        """
        SELECT m.id_matu, m.id_clie, m.status_ia,
               c.nome_clie, c.mail_clie, c.fone_clie, c.empresa_clie
        FROM public.ctdi_matu m
        INNER JOIN public.ctdi_clie c ON c.id_clie = m.id_clie
        WHERE m.id_matu = %s
        LIMIT 1;
        """,
        (id_matu,),
    )
    matu = cur.fetchone()
    if not matu:
        raise FunilError("ID Matu não encontrado.")
    matu = dict(matu)

    cur.execute(
        "SELECT * FROM public.dx_oportunidades WHERE id_matu = %s LIMIT 1 FOR UPDATE;",
        (id_matu,),
    )
    opp = cur.fetchone()
    if opp:
        opp = dict(opp)
        dono = opp.get("id_consultor_origem")
        if dono and int(dono) != int(id_consultor):
            raise FunilError("Lead já vinculado a outro consultor.")
        cur.execute(
            """
            UPDATE public.dx_oportunidades
            SET id_consultor_origem = %s,
                status_funil = %s,
                origem = %s,
                id_clie = COALESCE(id_clie, %s),
                nome = COALESCE(nome, %s),
                email = COALESCE(email, %s),
                telefone = COALESCE(telefone, %s),
                empresa = COALESCE(empresa, %s),
                atualizado_em = NOW()
            WHERE id = %s
            RETURNING *;
            """,
            (
                id_consultor,
                STATUS_EM_NEGOCIACAO,
                ORIGEM_REATIVO,
                matu["id_clie"],
                matu.get("nome_clie"),
                matu.get("mail_clie"),
                matu.get("fone_clie"),
                matu.get("empresa_clie"),
                opp["id"],
            ),
        )
        updated = dict(cur.fetchone())
    else:
        # Verifica contrato com outro consultor
        cur.execute(
            """
            SELECT id_consultor_origem FROM public.dx_contratos
            WHERE id_clie = %s
              AND id_consultor_origem IS NOT NULL
              AND status IN ('ativo', 'trial', 'inadimplente')
            ORDER BY id DESC LIMIT 1;
            """,
            (matu["id_clie"],),
        )
        ct = cur.fetchone()
        if ct:
            ct = dict(ct)
            if int(ct["id_consultor_origem"]) != int(id_consultor):
                raise FunilError("Lead já vinculado a outro consultor.")

        cur.execute(
            """
            INSERT INTO public.dx_oportunidades (
                id_clie, id_matu, id_consultor_origem, status_funil, origem,
                nome, email, telefone, empresa
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *;
            """,
            (
                matu["id_clie"],
                id_matu,
                id_consultor,
                STATUS_EM_NEGOCIACAO,
                ORIGEM_REATIVO,
                matu.get("nome_clie"),
                matu.get("mail_clie"),
                matu.get("fone_clie"),
                matu.get("empresa_clie"),
            ),
        )
        updated = dict(cur.fetchone())

    cur.execute(
        """
        UPDATE public.dx_contratos
        SET id_consultor_origem = COALESCE(id_consultor_origem, %s),
            atualizado_em = NOW()
        WHERE id_clie = %s
          AND status IN ('ativo', 'trial', 'inadimplente')
          AND id_consultor_origem IS NULL;
        """,
        (id_consultor, matu["id_clie"]),
    )

    cur.execute(_select_oportunidade_sql("o.id = %s"), (updated["id"],))
    full = cur.fetchone()
    return serializar_oportunidade(dict(full)) if full else serializar_oportunidade(updated)


def criar_prospecto(
    cur,
    *,
    id_consultor: int,
    nome: str,
    email: str,
    telefone: str | None = None,
    empresa: str | None = None,
    public_base_url: str = "http://localhost:3000",
) -> dict:
    nome = (nome or "").strip()
    email = (email or "").strip().lower()
    if not nome:
        raise FunilError("Nome é obrigatório.")
    if not email or "@" not in email:
        raise FunilError("E-mail inválido.")

    ref = garantir_ref_code(cur, id_consultor)
    token = gerar_invite_token()

    cur.execute(
        """
        INSERT INTO public.dx_oportunidades (
            id_clie, id_matu, id_consultor_origem, status_funil, origem,
            nome, email, telefone, empresa, invite_token
        ) VALUES (NULL, NULL, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *;
        """,
        (
            id_consultor,
            STATUS_CONVITE_ENVIADO,
            ORIGEM_ATIVO,
            nome,
            email,
            (telefone or "").strip() or None,
            (empresa or "").strip() or None,
            token,
        ),
    )
    row = dict(cur.fetchone())
    base = public_base_url.rstrip("/")
    invite_url = f"{base}/cadastro?ref={ref}&invite={token}"
    payload = serializar_oportunidade(row)
    payload["invite_url"] = invite_url
    payload["ref_code"] = ref
    return payload


def listar_oportunidades_consultor(cur, ids_carteira: list[int]) -> list[dict]:
    if not ids_carteira:
        return []
    placeholders = ", ".join(["%s"] * len(ids_carteira))
    cur.execute(
        _select_oportunidade_sql(f"o.id_consultor_origem IN ({placeholders})")
        + " ORDER BY o.atualizado_em DESC, o.id DESC;",
        tuple(ids_carteira),
    )
    return [serializar_oportunidade(dict(r)) for r in cur.fetchall()]


def resolver_ref_consultor(cur, ref_code: str) -> dict | None:
    code = (ref_code or "").strip()
    if not code:
        return None
    cur.execute(
        """
        SELECT c.id, c.ref_code, c.tipo, u.nome, u.email
        FROM public.dx_consultores c
        INNER JOIN public.paneldx_usuarios u ON u.id_usuario = c.user_id
        WHERE c.ativo = TRUE AND LOWER(TRIM(c.ref_code)) = LOWER(TRIM(%s))
        LIMIT 1;
        """,
        (code,),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def associar_cadastro_com_ref(
    cur,
    *,
    id_clie: int,
    id_matu: int,
    ref_code: str | None,
    invite_token: str | None = None,
    nome: str | None = None,
    email: str | None = None,
    telefone: str | None = None,
    empresa: str | None = None,
) -> dict | None:
    """Associa cadastro novo ao consultor via ?ref= / ?invite= — evita órfão."""
    consultor = resolver_ref_consultor(cur, ref_code) if ref_code else None
    invite = (invite_token or "").strip() or None

    # 1) Convite específico
    if invite:
        cur.execute(
            """
            SELECT * FROM public.dx_oportunidades
            WHERE invite_token = %s
            LIMIT 1 FOR UPDATE;
            """,
            (invite,),
        )
        opp = cur.fetchone()
        if opp:
            opp = dict(opp)
            id_consultor = opp.get("id_consultor_origem")
            if consultor and id_consultor and int(consultor["id"]) != int(id_consultor):
                # ref e invite conflitantes — prioriza invite
                pass
            cur.execute(
                """
                UPDATE public.dx_oportunidades
                SET id_clie = %s,
                    id_matu = %s,
                    status_funil = %s,
                    origem = %s,
                    nome = COALESCE(%s, nome),
                    email = COALESCE(%s, email),
                    telefone = COALESCE(%s, telefone),
                    empresa = COALESCE(%s, empresa),
                    atualizado_em = NOW()
                WHERE id = %s
                RETURNING *;
                """,
                (
                    id_clie,
                    id_matu,
                    STATUS_EM_NEGOCIACAO,
                    ORIGEM_CONVITE,
                    nome,
                    email,
                    telefone,
                    empresa,
                    opp["id"],
                ),
            )
            return serializar_oportunidade(dict(cur.fetchone()))

    # 2) Apenas ref do consultor
    if consultor:
        id_consultor = int(consultor["id"])
        # Match por e-mail de prospecto aberto
        if email:
            cur.execute(
                """
                SELECT * FROM public.dx_oportunidades
                WHERE id_consultor_origem = %s
                  AND LOWER(TRIM(email)) = LOWER(TRIM(%s))
                  AND status_funil IN ('convite_enviado', 'distribuido', 'em_negociacao')
                  AND id_clie IS NULL
                ORDER BY id DESC
                LIMIT 1 FOR UPDATE;
                """,
                (id_consultor, email),
            )
            opp = cur.fetchone()
            if opp:
                opp = dict(opp)
                cur.execute(
                    """
                    UPDATE public.dx_oportunidades
                    SET id_clie = %s,
                        id_matu = %s,
                        status_funil = %s,
                        origem = %s,
                        atualizado_em = NOW()
                    WHERE id = %s
                    RETURNING *;
                    """,
                    (id_clie, id_matu, STATUS_EM_NEGOCIACAO, ORIGEM_CONVITE, opp["id"]),
                )
                return serializar_oportunidade(dict(cur.fetchone()))

        cur.execute(
            """
            INSERT INTO public.dx_oportunidades (
                id_clie, id_matu, id_consultor_origem, status_funil, origem,
                nome, email, telefone, empresa
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *;
            """,
            (
                id_clie,
                id_matu,
                id_consultor,
                STATUS_EM_NEGOCIACAO,
                ORIGEM_CONVITE,
                nome,
                email,
                telefone,
                empresa,
            ),
        )
        return serializar_oportunidade(dict(cur.fetchone()))

    return None
