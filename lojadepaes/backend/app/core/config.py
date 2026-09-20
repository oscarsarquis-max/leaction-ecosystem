from functools import lru_cache
from ipaddress import ip_address

from pydantic_settings import BaseSettings, SettingsConfigDict

_LOOPBACK_NAMES = {"localhost", "ip6-localhost", "ip6-loopback"}


def _is_loopback_bind(host: str) -> bool:
    value = (host or "").strip().lower()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    if "%" in value:
        value = value.split("%", 1)[0]
    if value in _LOOPBACK_NAMES:
        return True
    if value.startswith("::ffff:"):
        value = value[7:]
    try:
        return ip_address(value).is_loopback
    except ValueError:
        return False


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LOJADEPAES_",
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: str = "local"
    http_host: str = "127.0.0.1"
    http_port: int = 5075
    database_url: str = (
        "postgresql+psycopg://lojadepaes:lojadepaes_dev@127.0.0.1:5438/lojadepaes"
    )
    db_connect_timeout_seconds: float = 3
    cors_origins: str = "http://127.0.0.1:5175,http://localhost:5175"
    bakery_timezone: str = "America/Sao_Paulo"
    test_database_url: str = (
        "postgresql+psycopg://lojadepaes:lojadepaes_dev@127.0.0.1:5438/lojadepaes_test"
    )
    admin_username: str = ""
    admin_password_hash: str = ""
    admin_session_secret: str = ""
    admin_local_passwordless: bool = False
    cookie_secure: bool = False
    session_ttl_hours: int = 8
    login_max_failures: int = 5
    login_window_minutes: int = 15
    media_dir: str = "../var/media"
    media_max_bytes: int = 8 * 1024 * 1024

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def password_login_enabled(self) -> bool:
        return bool(
            self.admin_username.strip()
            and self.admin_password_hash.strip()
            and len(self.admin_session_secret.strip()) >= 32
        )

    @property
    def local_passwordless_eligible(self) -> bool:
        env_name = self.env.strip().lower()
        if env_name in {"production", "prod"}:
            return False
        return bool(
            self.admin_local_passwordless
            and env_name in {"local", "development", "dev"}
            and _is_loopback_bind(self.http_host)
            and len(self.admin_session_secret.strip()) >= 32
        )

    @property
    def admin_enabled(self) -> bool:
        return self.password_login_enabled or self.local_passwordless_eligible


@lru_cache
def get_settings() -> Settings:
    return Settings()
