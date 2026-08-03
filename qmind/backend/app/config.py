"""Application settings — database `qmind` on cluster `leaction_db`."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "QMind"
    api_prefix: str = "/api/v1"
    environment: Literal["local", "dev", "prod"] = "local"

    # Set via env / .env — never commit real credentials.
    database_url_admin: str = Field(..., description="Migrator/bootstrap DSN (table owner)")
    database_url_app: str = Field(..., description="Runtime DSN as qmind_app (no owner, no BYPASSRLS)")

    auth_mode: Literal["cognito", "dev"] = "dev"
    cognito_region: str = "us-east-2"
    cognito_user_pool_id: str = ""
    cognito_app_client_id: str = ""

    @model_validator(mode="after")
    def forbid_dev_auth_in_prod(self) -> Settings:
        if self.environment == "prod" and self.auth_mode == "dev":
            raise ValueError(
                "AUTH_MODE=dev is forbidden when ENVIRONMENT=prod. Use AUTH_MODE=cognito."
            )
        return self

    @property
    def cognito_issuer(self) -> str:
        return (
            f"https://cognito-idp.{self.cognito_region}.amazonaws.com/"
            f"{self.cognito_user_pool_id}"
        )

    @property
    def cognito_jwks_url(self) -> str:
        return f"{self.cognito_issuer}/.well-known/jwks.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
