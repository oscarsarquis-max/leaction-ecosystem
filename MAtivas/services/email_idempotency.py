"""
Controle de idempotência para envio de e-mail de roteiros.
"""

from __future__ import annotations

import logging
import os

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger("mativas.email_idempotency")

_MANUAL_DEBOUNCE_SECONDS = 60


def _db_config() -> dict:
    return {
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": int(os.environ.get("DB_PORT", 5432)),
        "dbname": os.environ.get("DB_NAME", "MAtivas"),
        "user": os.environ.get("DB_USER") or os.environ.get("DB_USERNAME") or "postgres",
        "password": os.environ.get("DB_PASSWORD") or os.environ.get("DB_PASS") or "",
        "sslmode": os.environ.get("DB_SSLMODE", "disable"),
    }


def _connect():
    return psycopg2.connect(**_db_config())


def reservar_envio_automatico(roteiro_id: int, destinatario: str) -> bool:
    """
    Registra o envio automático antes do SES.
    Retorna True apenas para a primeira tentativa por roteiro.
    """
    conn = None
    try:
        conn = _connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO roteiro_email_envios (roteiro_id, tipo, destinatario)
                SELECT %s, 'automatico', %s
                 WHERE NOT EXISTS (
                       SELECT 1
                         FROM roteiro_email_envios
                        WHERE roteiro_id = %s
                          AND tipo = 'automatico'
                 )
                RETURNING id
                """,
                (roteiro_id, destinatario, roteiro_id),
            )
            reservado = cur.fetchone() is not None
        conn.commit()
        if not reservado:
            logger.info(
                "Envio automático duplicado bloqueado (roteiro_id=%s, to=%s)",
                roteiro_id,
                destinatario,
            )
        return reservado
    except Exception:
        if conn:
            conn.rollback()
        logger.exception(
            "Falha ao reservar envio automático (roteiro_id=%s, to=%s)",
            roteiro_id,
            destinatario,
        )
        return False
    finally:
        if conn:
            conn.close()


def pode_enviar_manual(roteiro_id: int, destinatario: str) -> bool:
    """Evita reenvios manuais repetidos em sequência."""
    conn = None
    try:
        conn = _connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1
                  FROM roteiro_email_envios
                 WHERE roteiro_id = %s
                   AND tipo = 'manual'
                   AND destinatario = %s
                   AND criado_em > CURRENT_TIMESTAMP - (%s || ' seconds')::interval
                 LIMIT 1
                """,
                (roteiro_id, destinatario, _MANUAL_DEBOUNCE_SECONDS),
            )
            return cur.fetchone() is None
    except Exception:
        logger.exception(
            "Falha ao verificar debounce manual (roteiro_id=%s, to=%s)",
            roteiro_id,
            destinatario,
        )
        return True
    finally:
        if conn:
            conn.close()


def registrar_envio_manual(roteiro_id: int, destinatario: str, message_id: str | None = None) -> None:
    conn = None
    try:
        conn = _connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO roteiro_email_envios
                       (roteiro_id, tipo, destinatario, ses_message_id)
                VALUES (%s, 'manual', %s, %s)
                """,
                (roteiro_id, destinatario, message_id),
            )
        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        logger.exception(
            "Falha ao registrar envio manual (roteiro_id=%s, to=%s)",
            roteiro_id,
            destinatario,
        )
    finally:
        if conn:
            conn.close()


def atualizar_message_id_envio_automatico(
    roteiro_id: int, destinatario: str, message_id: str | None
) -> None:
    conn = None
    try:
        conn = _connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE roteiro_email_envios
                   SET ses_message_id = %s
                 WHERE roteiro_id = %s
                   AND tipo = 'automatico'
                   AND destinatario = %s
                """,
                (message_id, roteiro_id, destinatario),
            )
        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        logger.exception(
            "Falha ao atualizar message_id automático (roteiro_id=%s)",
            roteiro_id,
        )
    finally:
        if conn:
            conn.close()
