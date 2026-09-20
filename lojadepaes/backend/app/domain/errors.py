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


class NotFoundError(DomainError):
    pass


class ProductError(DomainError):
    pass
