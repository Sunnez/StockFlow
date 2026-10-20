class ApplicationError(Exception):
    """Base exception for expected application-level errors."""


class NotFoundError(ApplicationError):
    """Requested resource does not exist."""


class ConflictError(ApplicationError):
    """Operation conflicts with the current state."""


class ApplicationValidationError(ApplicationError):
    """Application or business rule validation failed."""
