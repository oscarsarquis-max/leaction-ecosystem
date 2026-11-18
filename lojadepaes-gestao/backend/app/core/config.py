from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuração do Gestão. Tudo vem de variáveis GESTAO_* (nunca de arquivo versionado)."""

    model_config = SettingsConfigDict(env_prefix="GESTAO_", extra="ignore")

    env: str = "development"

    # Banco próprio do Gestão (leitura e escrita).
    database_url: str = "postgresql+psycopg://gestao_app:app_dev_pw@127.0.0.1:55440/gestao"
    # Banco da Loja (somente leitura, papel gestao_reader).
    loja_database_url: str = (
        "postgresql+psycopg://gestao_reader:reader_dev_pw@127.0.0.1:55440/lojadepaes"
    )
    db_connect_timeout_seconds: int = 5

    # Sessão e login (desenho da Loja: argon2, HMAC em tabela, CSRF, 5 falhas em 15 minutos, 8 h).
    session_secret: str = ""
    cookie_secure: bool = True
    session_ttl_hours: int = 8
    login_max_failures: int = 5
    login_window_minutes: int = 15
    # Origens extras aceitas em requisições que gravam (CSV). Vazio = só a própria origem.
    allowed_origins: str = ""

    bakery_timezone: str = "America/Sao_Paulo"
    # Cabeças do Alembic da Loja que o Gestão já conhece (CSV). Só informativo.
    loja_alembic_heads: str = "e7b3c9a41d06"
    horizonte_dias_padrao: int = 14
    horizonte_dias_maximo: int = 60

    spa_dir: str = ""

    @property
    def session_ready(self) -> bool:
        return len(self.session_secret.strip()) >= 32

    @property
    def allowed_origin_list(self) -> list[str]:
        return [item.strip() for item in self.allowed_origins.split(",") if item.strip()]

    @property
    def loja_head_list(self) -> list[str]:
        return [item.strip() for item in self.loja_alembic_heads.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
