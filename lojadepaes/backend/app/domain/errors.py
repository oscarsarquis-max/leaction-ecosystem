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


class UnpaidProductionError(ConflictError):
    def __init__(
        self,
        *,
        public_reference: str,
        total_cents: int | None,
        currency: str,
        financial_bucket: str,
        financial_label: str,
        uncertain: bool,
    ) -> None:
        if uncertain:
            message = "O pagamento deste pedido não pôde ser confirmado."
        else:
            message = "Este pedido ainda não está pago."
        super().__init__(message)
        self.code = "unpaid_production"
        self.public_reference = public_reference
        self.total_cents = total_cents
        self.currency = currency
        self.financial_bucket = financial_bucket
        self.financial_label = financial_label
        self.uncertain = uncertain


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
