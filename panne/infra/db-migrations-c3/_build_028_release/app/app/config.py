from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PANNE_",
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: str = "local"
    http_host: str = "127.0.0.1"
    http_port: int = 5080
    versao: str = "0.1.0"
    database_url: str = "postgresql+asyncpg://<configure-local-user>:<configure-local-password>@127.0.0.1:5434/panne"
    runtime_database_url: str = (
        "postgresql+asyncpg://<configure-runtime-user>:<configure-runtime-password>@127.0.0.1:5434/panne"
    )
    auth_verifier: str = "fake"
    fake_access_token: str = ""
    fake_issuer: str = "https://panne.local/fake"
    fake_subject: str = "local-dev-owner"
    oidc_issuer: str = ""
    oidc_client_id: str = ""
    oidc_audience: str = ""
    oidc_required_scope: str = ""
    jwks_timeout_seconds: float = 3.0
    max_authorization_header_bytes: int = 8192
    # Só efetiva com PANNE_ENV=demo. Fora disso é ignorada (sem efeito em produção).
    # Default alinhado ao seed DEFAULT_ANCHOR quando env=demo e o campo está vazio.
    demo_anchor_date: str = ""
    # Identidade da execução demo (start-demo). Fora de demo permanece vazio.
    demo_instance_id: str = ""
    demo_started_at: str = ""

    # Editorial /entrar via Action Hub (S2S). Sem credenciais no browser.
    action_hub_api_url: str = ""
    login_editorial_timeout_seconds: float = 2.5
    login_editorial_cache_ttl_seconds: int = 30
    # Idade máxima do stale (segundos). Além disso → fallback estático.
    # Cache é em memória por processo — não compartilhado.
    login_editorial_cache_max_stale_seconds: int = 600
    login_editorial_max_bytes: int = 200_000
    # Override explícito (local/test): panne-demo | panne. Em produção é ignorado
    # salvo login_editorial_allow_demo_key_in_prod=True (admin explícito).
    login_editorial_config_key: str = ""
    login_editorial_allow_demo_key_in_prod: bool = False
    # CSV de hosts HTTPS permitidos (mídia / CTA). Vazio = defaults do url_policy.
    login_editorial_media_hosts: str = ""
    login_editorial_cta_hosts: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
