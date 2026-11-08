class AuthError(Exception):
    """Credenciais inválidas."""


class RateLimitError(Exception):
    """Falhas demais de login."""


class AuthDisabledError(Exception):
    """Sessão não configurada (segredo ausente ou curto)."""


class ErroDeDominio(Exception):
    """Regra de negócio violada. Vira JSON `{"detail": {"codigo", "mensagem", ...}}` com o status dado."""

    def __init__(self, codigo: str, mensagem: str, status: int = 422, **extra: object) -> None:
        super().__init__(mensagem)
        self.codigo = codigo
        self.mensagem = mensagem
        self.status = status
        self.extra = extra

    def detalhe(self) -> dict[str, object]:
        return {"codigo": self.codigo, "mensagem": self.mensagem, **self.extra}
