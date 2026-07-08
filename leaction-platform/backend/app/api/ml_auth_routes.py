"""Rotas OAuth Mercado Livre — login e callback (plugin Marketplace :4012)."""

from __future__ import annotations

import logging

from flask import Blueprint, jsonify, redirect, request

from app.services.ml_oauth_service import (
    MercadoLivreOAuthError,
    build_authorization_url,
    exchange_authorization_code,
    is_oauth_app_configured,
    oauth_setup_info,
    validate_redirect_uri,
)

logger = logging.getLogger(__name__)

ml_auth_bp = Blueprint("ml_auth", __name__)


@ml_auth_bp.get("/ml/oauth-setup")
def ml_oauth_setup():
    """Instruções e URLs para cadastrar redirect HTTPS no painel ML."""
    info = oauth_setup_info()
    info["ml_oauth_app"] = is_oauth_app_configured()
    return jsonify(info), 200


@ml_auth_bp.get("/ml/login")
def ml_login():
    """Redireciona para autorização oficial do Mercado Livre."""
    if not is_oauth_app_configured():
        return (
            "Configure ML_APP_ID e ML_SECRET_KEY (ou ML_CLIENT_ID / ML_CLIENT_SECRET) "
            "em backend/.env antes de autenticar.",
            503,
        )

    ok, err = validate_redirect_uri()
    if not ok:
        return (
            f"{err}\n\n"
            "Consulte GET /api/marketplace/ml/oauth-setup para a URL exata a cadastrar.",
            503,
        )

    try:
        return redirect(build_authorization_url())
    except MercadoLivreOAuthError as exc:
        logger.error("ML login: %s", exc)
        return str(exc), 503


@ml_auth_bp.get("/ml/callback")
def ml_callback():
    """Recebe authorization_code e persiste tokens OAuth."""
    error = (request.args.get("error") or "").strip()
    if error:
        description = (request.args.get("error_description") or error).strip()
        logger.error("ML callback OAuth error: %s", description)
        return f"Autenticação Mercado Livre falhou: {description}", 400

    code = (request.args.get("code") or "").strip()
    if not code:
        return "Parâmetro 'code' ausente na URL de callback.", 400

    try:
        record = exchange_authorization_code(code)
    except MercadoLivreOAuthError as exc:
        logger.exception("ML callback: falha ao trocar code por tokens")
        return f"Autenticação Mercado Livre falhou: {exc}", 502

    refresh_note = (
        " Refresh token obtido — renovação automática ativa."
        if record.get("refresh_token")
        else (
            " Token ativo por ~6 horas (sem refresh_token). "
            "No painel developers.mercadolivre.com.br habilite acesso offline, "
            "revogue a app em mercadolivre.com.br/privacidade/apps e refaça o login."
        )
    )
    return f"Autenticação Mercado Livre Concluída com Sucesso!{refresh_note}", 200
