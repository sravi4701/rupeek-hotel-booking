"""Domain errors. The API layer maps each one to an HTTP status; the domain knows no HTTP."""


class DomainError(Exception):
    """Base class for every business-rule violation."""


class DomainValidationError(DomainError):
    """Input that breaks an invariant of a value object or entity."""


class NotFoundError(DomainError):
    def __init__(self, entity: str, entity_id: str) -> None:
        super().__init__(f"{entity} '{entity_id}' not found")
        self.entity = entity
        self.entity_id = entity_id


class InsufficientInventoryError(DomainError):
    """Not enough free units for the requested dates."""


class InvalidStateTransitionError(DomainError):
    def __init__(self, entity: str, current: str, target: str) -> None:
        super().__init__(f"{entity} cannot move from {current} to {target}")
        self.current = current
        self.target = target


class IdempotencyConflictError(DomainError):
    """An idempotency key was reused for a different request."""
