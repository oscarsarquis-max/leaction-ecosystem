"""De onde saem o modelo e a região. Os valores ficam no ambiente, nunca no código versionado."""

from __future__ import annotations

import os
from dataclasses import dataclass


class GigioSettingsError(ValueError):
    """Configuração do modelo incompleta."""


@dataclass(frozen=True)
class GigioModelSettings:
    region: str
    model_id: str
    max_tokens: int
    temperature: float


def _env(nome: str, environ: dict[str, str]) -> str:
    return (environ.get(nome) or "").strip()


def load_gigio_model_settings(environ: dict[str, str] | None = None) -> GigioModelSettings:
    env = environ if environ is not None else os.environ
    region = _env("GESTAO_GIGIO_BEDROCK_REGION", env)
    model_id = _env("GESTAO_GIGIO_BEDROCK_MODEL_ID", env)
    if not region:
        raise GigioSettingsError("GESTAO_GIGIO_BEDROCK_REGION não configurada")
    if not model_id:
        raise GigioSettingsError("GESTAO_GIGIO_BEDROCK_MODEL_ID não configurado")
    return GigioModelSettings(region=region, model_id=model_id, max_tokens=2048, temperature=0.3)


def credencial_presente(environ: dict[str, str] | None = None) -> bool:
    env = environ if environ is not None else os.environ
    return bool(_env("GESTAO_GIGIO_AWS_ACCESS_KEY_ID", env) and _env("GESTAO_GIGIO_AWS_SECRET_ACCESS_KEY", env))


def gateway_falso(environ: dict[str, str] | None = None) -> bool:
    env = environ if environ is not None else os.environ
    return _env("GESTAO_GIGIO_GATEWAY", env).lower() == "fake"


def disponivel(environ: dict[str, str] | None = None) -> tuple[bool, str | None]:
    if gateway_falso(environ):
        return True, None
    if credencial_presente(environ):
        try:
            load_gigio_model_settings(environ)
        except GigioSettingsError:
            return False, "O Gigio ainda não está configurado nesta padaria."
        return True, None
    return False, "O Gigio ainda não está configurado nesta padaria."
