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

    database_url_admin: str = Field(..., description="Migrator/bootstrap DSN (table owner)")
    database_url_app: str = Field(..., description="Runtime DSN as qmind_app")

    auth_mode: Literal["cognito", "dev"] = "dev"
    cognito_region: str = "us-east-2"
    cognito_user_pool_id: str = ""
    cognito_app_client_id: str = ""

    # Object storage (ADR-007)
    storage_backend: Literal["memory", "s3"] = "memory"
    s3_region: str = "us-east-2"
    s3_bucket: str = ""
    s3_endpoint_url: str = ""  # optional LocalStack / MinIO
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    evidence_max_bytes: int = 25_000_000
    evidence_upload_expires_seconds: int = 900
    evidence_download_expires_seconds: int = 300
    evidence_allowed_content_types: str = (
        "application/pdf,image/png,image/jpeg,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    # security_pass without malware worker — forbidden in prod
    allow_simulated_security_pass: bool = True

    @model_validator(mode="after")
    def forbid_unsafe_prod(self) -> Settings:
        if self.environment == "prod" and self.auth_mode == "dev":
            raise ValueError("AUTH_MODE=dev is forbidden when ENVIRONMENT=prod.")
        if self.environment == "prod" and self.allow_simulated_security_pass:
            raise ValueError(
                "ALLOW_SIMULATED_SECURITY_PASS must be false when ENVIRONMENT=prod "
                "(use quarantine worker)."
            )
        if self.environment == "prod" and self.storage_backend != "s3":
            raise ValueError("STORAGE_BACKEND=s3 is required when ENVIRONMENT=prod.")
        return self

    @property
    def allowed_content_types(self) -> set[str]:
        return {p.strip().lower() for p in self.evidence_allowed_content_types.split(",") if p.strip()}

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
