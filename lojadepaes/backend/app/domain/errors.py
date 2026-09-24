class DomainError(Exception):
    """Erro de regra de negócio da Loja de Pães."""


class ConfirmationError(DomainError):
    pass


class CapacityError(ConfirmationError):
    pass


class TransitionError(DomainError):
    pass


class AuthError(DomainError):
    pass


class AuthDisabledError(DomainError):
    pass


class AuthForbiddenError(DomainError):
    pass


class RateLimitError(DomainError):
    pass


class ConflictError(DomainError):
    pass


class PriceChangedError(ConflictError):
    def __init__(self, quoted_cents: int, current_cents: int):
        super().__init__("os preços mudaram desde a revisão")
        self.code = "price_changed"
        self.quoted_cents = quoted_cents
        self.current_cents = current_cents


class NotFoundError(DomainError):
    pass


class ProductError(DomainError):
    pass
