#!/usr/bin/env python3
"""Snapshot diário de estado por conta (Inove4us) → Action-Sponge.

Somente leitura no banco B2C. Emite `tipo_evento=conta_snapshot` no Hub
pelo mesmo canal S2S do tracking (`POST /api/crm/tracking/receber`, `x-crm-secret`).

Sessão sintética (estável por conta e sistema, o mesmo UUID todos os dias):
    id_sessao = UUID v5 (namespace URL) do nome `snapshot:inove4us:{instituicao_b2b_id}`
Evento da conta: usuario_origem_ref = sistema:snapshot
Evento por professor vinculado: id_usuario = id_clie, **mesma** sessão da conta.
  (crm_eventos não tem usuário; o Hub lê `dados.id_clie` / `dados.escopo=professor`.
   A sessão permanece sistema:snapshot porque o evento da conta é emitido primeiro.)

Janela pretendida: 03:00 America/Sao_Paulo (EventBridge cron 06:00 UTC).
Não cria tabela, coluna, migration nem endpoint.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    from zoneinfo import ZoneInfo

    TZ = ZoneInfo("America/Sao_Paulo")
except Exception:
    TZ = timezone(timedelta(hours=-3))

import requests
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
load_dotenv(Path(__file__).resolve().parent / ".env")

from db import get_conn  # noqa: E402

logger = logging.getLogger("snapshot_conta")

SISTEMA = "inove4us"
USUARIO_REF = "sistema:snapshot"
MAX_DADOS_BYTES = 4096
SESSION_NS = uuid.NAMESPACE_URL


def snapshot_session_id(sistema: str, instituicao_id: str) -> str:
    """UUID v5 estável: namespace URL + nome `snapshot:{sistema}:{instituicao_id}`."""
    return str(uuid.uuid5(SESSION_NS, f"snapshot:{sistema}:{instituicao_id}"))


def data_ref_hoje() -> str:
    return datetime.now(TZ).date().isoformat()


def _hub_receber_url() -> str:
    explicit = (os.environ.get("ACTION_HUB_CRM_TRACKING_URL") or "").strip()
    if explicit:
        return explicit
    base = (
        os.environ.get("ACTION_HUB_API_URL")
        or os.environ.get("HUB_API_URL")
        or "http://127.0.0.1:4001"
    ).strip()
    return f"{base.rstrip('/')}/api/crm/tracking/receber"


def _omit_empty(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for key, inner in value.items():
            cleaned = _omit_empty(inner)
            if cleaned is None or cleaned == {} or cleaned == []:
                continue
            out[key] = cleaned
        return out
    return value


def _table_exists(cur, name: str) -> bool:
    cur.execute(
        """
        SELECT 1
          FROM information_schema.tables
         WHERE table_schema = 'public' AND table_name = %s
         LIMIT 1
        """,
        (name,),
    )
    return cur.fetchone() is not None


def montar_snapshot_conta(cur, instituicao_id: str, data_ref: str) -> dict[str, Any]:
    inst = (str(instituicao_id),)
    cur.execute(
        """
        SELECT COUNT(*)::int AS professores_vinculados,
               COALESCE(SUM(creditos_ia), 0)::int AS saldo_total
          FROM public.ctdi_clie
         WHERE instituicao_b2b_id = %s::uuid
        """,
        inst,
    )
    row = cur.fetchone() or {}
    concedidos = 0
    if _table_exists(cur, "inove_credito_ia_concessoes"):
        cur.execute(
            """
            SELECT COALESCE(SUM(credits), 0)::int AS n
              FROM public.inove_credito_ia_concessoes
             WHERE instituicao_id = %s::uuid
            """,
            inst,
        )
        concedidos = int((cur.fetchone() or {}).get("n") or 0)

    aulas = 0
    desafios = 0
    if _table_exists(cur, "inove_aulas_simples"):
        cur.execute(
            """
            SELECT COUNT(*)::int AS n
              FROM public.inove_aulas_simples a
              JOIN public.ctdi_clie c ON c.id_clie = a.id_clie
             WHERE c.instituicao_b2b_id = %s::uuid
            """,
            inst,
        )
        aulas = int((cur.fetchone() or {}).get("n") or 0)
    if _table_exists(cur, "inove_desafios"):
        cur.execute(
            """
            SELECT COUNT(*)::int AS n
              FROM public.inove_desafios d
              JOIN public.ctdi_clie c ON c.id_clie = d.id_clie
             WHERE c.instituicao_b2b_id = %s::uuid
            """,
            inst,
        )
        desafios = int((cur.fetchone() or {}).get("n") or 0)

    return _omit_empty(
        {
            "sistema": SISTEMA,
            "data_ref": data_ref,
            "professores_vinculados": int(row.get("professores_vinculados") or 0),
            "creditos": {
                "saldo_total": int(row.get("saldo_total") or 0),
                "concedidos_institucional_total": concedidos,
            },
            "aulas_total": aulas,
            "desafios_total": desafios,
        }
    )


def montar_snapshot_professor(
    cur, instituicao_id: str, prof: dict[str, Any], data_ref: str, tem_aloc: bool
) -> dict[str, Any]:
    id_clie = int(prof["id_clie"])
    aulas = 0
    desafios = 0
    if _table_exists(cur, "inove_aulas_simples"):
        cur.execute(
            "SELECT COUNT(*)::int AS n FROM public.inove_aulas_simples WHERE id_clie = %s",
            (id_clie,),
        )
        aulas = int((cur.fetchone() or {}).get("n") or 0)
    if _table_exists(cur, "inove_desafios"):
        cur.execute(
            "SELECT COUNT(*)::int AS n FROM public.inove_desafios WHERE id_clie = %s",
            (id_clie,),
        )
        desafios = int((cur.fetchone() or {}).get("n") or 0)

    vinculo_ativo = True
    if tem_aloc:
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1
                  FROM public.inove_alocacoes_escola
                 WHERE id_clie = %s
                   AND school_instituicao_id = %s::uuid
                   AND ativo IS TRUE
            ) AS ok
            """,
            (id_clie, instituicao_id),
        )
        vinculo_ativo = bool((cur.fetchone() or {}).get("ok"))

    plan_tier = prof.get("plan_tier")
    dados: dict[str, Any] = {
        "sistema": SISTEMA,
        "data_ref": data_ref,
        "escopo": "professor",
        "id_clie": id_clie,
        "creditos_saldo": int(prof.get("creditos_ia") or 0),
        "aulas_total": aulas,
        "desafios_total": desafios,
        "vinculo_ativo": vinculo_ativo,
    }
    if plan_tier not in (None, ""):
        dados["plan_tier"] = str(plan_tier)
    return _omit_empty(dados)


def emit_hub(
    instituicao_id: str, dados: dict[str, Any], id_usuario: str
) -> tuple[bool, str]:
    encoded = json.dumps(dados, ensure_ascii=False, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > MAX_DADOS_BYTES:
        logger.error(
            "snapshot %s/%s excede 4KB",
            instituicao_id,
            id_usuario,
        )
        return False, "dados>4kb"

    secret = (os.environ.get("CRM_TRACKING_SECRET") or "").strip()
    headers = {"Content-Type": "application/json"}
    if secret:
        headers["x-crm-secret"] = secret

    body = {
        "sistema_origem": SISTEMA,
        "id_sessao": snapshot_session_id(SISTEMA, instituicao_id),
        "id_usuario": id_usuario,
        "instituicao_id": instituicao_id,
        "tipo_evento": "conta_snapshot",
        "url_pagina": "/sistema/snapshot",
        "user_agent": "inove4us-snapshot/1",
        "tempo_gasto_segundos": 0,
        "dados": dados,
    }
    try:
        resp = requests.post(_hub_receber_url(), json=body, headers=headers, timeout=(4, 12))
        if resp.status_code >= 400:
            logger.error(
                "Hub recusou snapshot %s/%s: HTTP %s %s",
                instituicao_id,
                id_usuario,
                resp.status_code,
                (resp.text or "")[:240],
            )
            return False, f"hub_{resp.status_code}"
        return True, "ok"
    except requests.RequestException as exc:
        logger.error(
            "Hub indisponível para snapshot %s/%s: %s",
            instituicao_id,
            id_usuario,
            exc,
        )
        return False, "hub_unavailable"


def instituicoes(cur) -> list[str]:
    cur.execute(
        """
        SELECT DISTINCT instituicao_b2b_id::text AS id
          FROM public.ctdi_clie
         WHERE instituicao_b2b_id IS NOT NULL
         ORDER BY 1
        """
    )
    return [str(r["id"]) for r in cur.fetchall()]


def professores(cur, instituicao_id: str) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT id_clie, plan_tier, creditos_ia
          FROM public.ctdi_clie
         WHERE instituicao_b2b_id = %s::uuid
         ORDER BY id_clie
        """,
        (instituicao_id,),
    )
    return list(cur.fetchall() or [])


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [inove-snapshot] %(message)s",
    )
    data_ref = data_ref_hoje()
    enviados = 0
    falhas = 0
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                ids = instituicoes(cur)
                tem_aloc = _table_exists(cur, "inove_alocacoes_escola")
                logger.info("contas=%s data_ref=%s", len(ids), data_ref)
                for inst in ids:
                    try:
                        dados_conta = montar_snapshot_conta(cur, inst, data_ref)
                        ok, reason = emit_hub(inst, dados_conta, USUARIO_REF)
                        if ok:
                            enviados += 1
                        else:
                            falhas += 1
                            logger.error("falha conta=%s reason=%s", inst, reason)
                            continue
                        for prof in professores(cur, inst):
                            dados_p = montar_snapshot_professor(
                                cur, inst, prof, data_ref, tem_aloc
                            )
                            ok, reason = emit_hub(inst, dados_p, str(int(prof["id_clie"])))
                            if ok:
                                enviados += 1
                            else:
                                falhas += 1
                                logger.error(
                                    "falha professor=%s conta=%s reason=%s",
                                    prof.get("id_clie"),
                                    inst,
                                    reason,
                                )
                    except Exception:
                        falhas += 1
                        logger.exception("erro ao montar/enviar conta=%s", inst)
    except Exception:
        logger.exception("job abortado (sem escrita no produto)")
        return 1

    logger.info("fim enviados=%s falhas=%s", enviados, falhas)
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())
