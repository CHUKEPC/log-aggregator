"""Domain exception hierarchy for the Log Aggregator service.

Provides distinct error classes for storage, parsing, authentication,
and rate-limiting scenarios.
"""


class LogAggregatorError(Exception):
    """Base exception for all log aggregator errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ConfigurationError(LogAggregatorError):
    """Raised when configuration values are missing or invalid."""


class StorageError(LogAggregatorError):
    """Raised when a storage backend operation fails."""


class LogParsingError(LogAggregatorError):
    """Raised when parsing a raw log entry fails."""

    def __init__(self, message: str, raw_line: str | None = None) -> None:
        super().__init__(message)
        self.raw_line = raw_line


class AuthenticationError(LogAggregatorError):
    """Raised when client authentication fails."""


class PermissionDeniedError(LogAggregatorError):
    """Raised when client lacks authorization for an action."""


class RateLimitExceededError(LogAggregatorError):
    """Raised when request frequency exceeds allowed limits."""

    def __init__(self, message: str, retry_after: int = 60) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class NotFoundError(LogAggregatorError):
    """Raised when a requested resource is not found."""


class ValidationError(LogAggregatorError):
    """Raised when domain validation rules are violated."""
