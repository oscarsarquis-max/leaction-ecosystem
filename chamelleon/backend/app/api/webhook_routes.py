"""Webhooks de ingestão Gemba — recebe dados operacionais de micro-serviços satélites."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.core.gemba_webhook_auth import require_gemba_webhook_auth
from app.services.andon_triage_service import AndonTriageService
from app.services.gemba_ingestion_service import GembaIngestionService

webhook_bp = Blueprint("webhooks", __name__)


@webhook_bp.post("/gemba/rdo")
@require_gemba_webhook_auth
def ingest_rdo_webhook():
    """
    Recebe RDO finalizado do Diário de Obra (ou outro satélite compatível).

    Autenticação: X-Integration-Key, X-Gemba-Webhook-Key ou Authorization: Bearer <key>.
    Assinatura opcional: X-Gemba-Signature = HMAC-SHA256(corpo, chave compartilhada).

    O corpo JSON completo é persistido em ``GembaEvent.raw_payload``.
    """
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "JSON inválido."}), 400

    try:
        result = GembaIngestionService().ingest_rdo_event(payload)
        event = result.event
        return (
            jsonify(
                {
                    "status": "ok",
                    "event_id": str(event.id),
                    "tenant_id": str(event.tenant_id),
                    "source_app": event.source_app,
                    "event_type": event.event_type,
                    "event_date": event.event_date.isoformat(),
                    "andon_tickets_created": AndonTriageService.tickets_summary(
                        result.tickets
                    ),
                }
            ),
            201,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao persistir evento Gemba."}), 500
