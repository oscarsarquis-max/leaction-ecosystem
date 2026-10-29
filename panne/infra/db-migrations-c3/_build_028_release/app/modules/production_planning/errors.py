class ProductionError(ValueError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class PermissionDeniedError(ProductionError):
    pass


class InvalidStateError(ProductionError):
    pass


class ConcurrencyError(ProductionError):
    pass


class IdempotencyConflictError(ProductionError):
    pass


class ValidationError(ProductionError):
    pass


class CycleError(ProductionError):
    pass


class ImmutableError(ProductionError):
    pass
