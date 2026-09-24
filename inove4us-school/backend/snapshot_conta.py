#!/usr/bin/env python3
"""Snapshot diário de estado por conta (School) → Action-Sponge.

Somente leitura no banco do School. Emite `tipo_evento=conta_snapshot` no Hub
pelo mesmo canal S2S do tracking (`POST /api/crm/tracking/receber`, `x-crm-secret`).

Sessão sintética (estável por conta e sistema, o mesmo UUID todos os dias):
    id_sessao = UUID v5 (namespace URL) do nome `snapshot:inove4us-school:{instituicao_id}`
    usuario_origem_ref = sistema:snapshot

Janela pretendida: 03:00 America/Sao_Paulo (crontab no host).
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

SISTEMA = "inove4us-school"
TZ_NAME = "America/Sao_Paulo"
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


def montar_snapshot(cur, instituicao_id: str, data_ref: str) -> dict[str, Any]:
    """SELECTs de contagem. Campo sem fonte não entra no dict."""
    inst = (str(instituicao_id),)
    dados: dict[str, Any] = {"sistema": SISTEMA, "data_ref": data_ref}

    cur.execute(
        """
        SELECT COUNT(*)::int AS cadastrados,
               COUNT(*) FILTER (WHERE ativo IS TRUE)::int AS ativos
          FROM public.school_gestores
         WHERE instituicao_id = %s::uuid
        """,
        inst,
    )
    g = cur.fetchone() or {}
    dados["gestores"] = {
        "cadastrados": int(g.get("cadastrados") or 0),
        "ativos": int(g.get("ativos") or 0),
    }

    cur.execute(
        "SELECT COUNT(*)::int AS n FROM public.school_turmas WHERE instituicao_id = %s::uuid",
        inst,
    )
    dados["turmas"] = int((cur.fetchone() or {}).get("n") or 0)

    cur.execute(
        "SELECT COUNT(*)::int AS n FROM public.school_alunos WHERE instituicao_id = %s::uuid",
        inst,
    )
    dados["alunos"] = int((cur.fetchone() or {}).get("n") or 0)

    cur.execute(
        """
        SELECT COUNT(*) FILTER (WHERE status_vinculo = 'pendente')::int AS pendente,
               COUNT(*) FILTER (WHERE status_vinculo = 'ativo')::int AS ativo
          FROM public.school_professores_vinculo
         WHERE instituicao_id = %s::uuid
        """,
        inst,
    )
    v = cur.fetchone() or {}
    dados["professores_vinculo"] = {
        "pendente": int(v.get("pendente") or 0),
        "ativo": int(v.get("ativo") or 0),
    }
    em_uso = int(v.get("ativo") or 0)

    cur.execute(
        """
        SELECT COUNT(*) FILTER (WHERE ativo IS TRUE)::int AS alocacoes_ativas,
               COUNT(*) FILTER (WHERE ativo IS TRUE AND COALESCE(notificado_b2c, FALSE) IS FALSE)::int AS b2c_pendentes
          FROM public.school_alocacoes_docentes
         WHERE instituicao_id = %s::uuid
        """,
        inst,
    )
    a = cur.fetchone() or {}
    dados["alocacoes_ativas"] = int(a.get("alocacoes_ativas") or 0)
    pend_b2c = int(a.get("b2c_pendentes") or 0)
    dados["ponte_b2c"] = {"notificacoes_pendentes": pend_b2c}
    dados["backfill_pendente"] = pend_b2c

    cur.execute(
        """
        SELECT total_assentos, sku_ultimo, contrato_hub_id
          FROM public.school_licencas
         WHERE instituicao_id = %s::uuid
         LIMIT 1
        """,
        inst,
    )
    lic = cur.fetchone()
    if lic:
        licencas: dict[str, Any] = {
            "total_assentos": int(lic.get("total_assentos") or 0),
            "em_uso": em_uso,
        }
        sku = lic.get("sku_ultimo")
        if sku not in (None, ""):
            licencas["sku_ultimo"] = str(sku)
        contrato = lic.get("contrato_hub_id")
        if contrato not in (None, ""):
            licencas["contrato_hub_id"] = str(contrato)
        dados["licencas"] = licencas

    cur.execute(
        """
        SELECT COUNT(*)::int AS condicoes_ativas,
               MAX(updated_at) AS ultima_atualizacao
          FROM public.school_aee_matrizes
         WHERE instituicao_id = %s::uuid
           AND status::text = 'ativo'
        """,
        inst,
    )
    aee = cur.fetchone() or {}
    aee_out: dict[str, Any] = {"condicoes_ativas": int(aee.get("condicoes_ativas") or 0)}
    ultima = aee.get("ultima_atualizacao")
    if ultima is not None:
        aee_out["ultima_atualizacao"] = (
            ultima.isoformat() if hasattr(ultima, "isoformat") else str(ultima)
        )
    # versao_vigente: omitida — versão é por condição, não há string única da conta.
    dados["aee"] = aee_out

    cur.execute(
        """
        SELECT COUNT(*) FILTER (WHERE status = 'ativo')::int AS ativos,
               COUNT(*) FILTER (
                 WHERE COALESCE(assinado_coordenador, FALSE)
                   AND COALESCE(assinado_psicopedagogo, FALSE)
               )::int AS assinatura_dupla_completa
          FROM public.school_pei_alunos
         WHERE instituicao_id = %s::uuid
        """,
        inst,
    )
    pei = cur.fetchone() or {}
    dados["pei"] = {
        "ativos": int(pei.get("ativos") or 0),
        "assinatura_dupla_completa": int(pei.get("assinatura_dupla_completa") or 0),
    }

    cur.execute(
        """
        SELECT COUNT(*)::int AS n
          FROM public.school_comunicacoes_eventos
         WHERE instituicao_id = %s::uuid
        """,
        inst,
    )
    dados["comunicados_total"] = int((cur.fetchone() or {}).get("n") or 0)

    # ponte_b2c.falhas: omitida — não há contador persistido de falha.
    return _omit_empty(dados)


def emit_hub(instituicao_id: str, dados: dict[str, Any]) -> tuple[bool, str]:
    encoded = json.dumps(dados, ensure_ascii=False, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > MAX_DADOS_BYTES:
        logger.error(
            "snapshot %s excede 4KB (%s bytes) — não enviado",
            instituicao_id,
            len(encoded.encode("utf-8")),
        )
        return False, "dados>4kb"

    secret = (os.environ.get("CRM_TRACKING_SECRET") or "").strip()
    headers = {"Content-Type": "application/json"}
    if secret:
        headers["x-crm-secret"] = secret

    body = {
        "sistema_origem": SISTEMA,
        "id_sessao": snapshot_session_id(SISTEMA, instituicao_id),
        "id_usuario": USUARIO_REF,
        "instituicao_id": instituicao_id,
        "tipo_evento": "conta_snapshot",
        "url_pagina": "/sistema/snapshot",
        "user_agent": "inove4us-school-snapshot/1",
        "tempo_gasto_segundos": 0,
        "dados": dados,
    }
    try:
        resp = requests.post(_hub_receber_url(), json=body, headers=headers, timeout=(4, 12))
        if resp.status_code >= 400:
            logger.error(
                "Hub recusou snapshot %s: HTTP %s %s",
                instituicao_id,
                resp.status_code,
                (resp.text or "")[:240],
            )
            return False, f"hub_{resp.status_code}"
        return True, "ok"
    except requests.RequestException as exc:
        logger.error("Hub indisponível para snapshot %s: %s", instituicao_id, exc)
        return False, "hub_unavailable"


def contas(cur) -> list[str]:
    cur.execute(
        """
        SELECT i.id::text AS id
          FROM public.school_instituicoes i
         WHERE EXISTS (
                 SELECT 1 FROM public.school_licencas l WHERE l.instituicao_id = i.id
               )
            OR EXISTS (
                 SELECT 1 FROM public.school_gestores g WHERE g.instituicao_id = i.id
               )
            OR EXISTS (
                 SELECT 1 FROM public.school_turmas t WHERE t.instituicao_id = i.id
               )
         ORDER BY i.id
        """
    )
    return [str(r["id"]) for r in cur.fetchall()]


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [school-snapshot] %(message)s",
    )
    data_ref = data_ref_hoje()
    enviados = 0
    falhas = 0
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                ids = contas(cur)
                logger.info("contas=%s data_ref=%s", len(ids), data_ref)
                for inst in ids:
                    try:
                        dados = montar_snapshot(cur, inst, data_ref)
                        ok, reason = emit_hub(inst, dados)
                        if ok:
                            enviados += 1
                        else:
                            falhas += 1
                            logger.error("falha conta=%s reason=%s", inst, reason)
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
