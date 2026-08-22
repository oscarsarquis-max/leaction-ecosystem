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


@lru_cache
def get_settings() -> Settings:
    return Settings()
